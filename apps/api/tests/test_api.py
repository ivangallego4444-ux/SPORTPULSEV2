"""FastAPI endpoint tests. External calls are mocked with respx using the
same real fixtures as test_providers.py, so these check routing, status
codes and response shape without depending on network availability."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import _snapshot, app, openfootball_provider, thesportsdb_provider

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@pytest.fixture(autouse=True)
def _reset_shared_provider_caches():
    """`app.main` keeps one module-level provider instance for the whole
    process (by design — it's what makes the known-good cache survive
    across real requests). That means its cache is also shared across
    every test in this file, so one test's mocked failure/success can
    otherwise leak into the next one's expectations. Reset it before
    each test for isolation.

    Real bug found live: that same module-level instance also points at
    the *real* apps/api/.cache_store.json (so known-good data survives an
    actual server restart) — without this guard, every test run was
    silently overwriting the real production cache with fake fixture
    data (team names like "A"/"B"), which a future real server start
    could then have served as if it were genuine. Swap the disk path out
    for the duration of each test instead of touching the real file."""
    real_path = thesportsdb_provider._known_good_store_path
    thesportsdb_provider._known_good_store_path = None
    thesportsdb_provider.cache._store.clear()
    thesportsdb_provider.cache._known_good.clear()
    openfootball_provider.cache._store.clear()
    # Same leakage risk as the provider caches above, for the newer
    # in-memory `_snapshot` (see main.py): SPORTPULSE_DISABLE_BACKGROUND_REFRESH
    # keeps the background loops from ever running during tests, but the
    # request-time lazy-fetch fallback (_snapshot_matches/_snapshot_standings)
    # still *writes* into `_snapshot` on first use — without resetting it,
    # one test's mocked fixture data would otherwise still be sitting in
    # the snapshot for the next test to read instead of its own mocks.
    _snapshot.matches_by_slug.clear()
    _snapshot.standings_by_slug.clear()
    _snapshot.live_matches = []
    _snapshot.pool_by_sport.clear()
    _snapshot.season_ratings_by_sport.clear()
    _snapshot.sos_by_sport.clear()
    yield
    thesportsdb_provider._known_good_store_path = real_path


def test_list_sports_only_includes_verified_ones():
    with TestClient(app) as client:
        resp = client.get("/api/sports")
    assert resp.status_code == 200
    slugs = {s["slug"] for s in resp.json()}
    assert slugs == {"futbol", "baloncesto", "tenis"}


def test_futbol_competitions_include_all_fourteen():
    with TestClient(app) as client:
        resp = client.get("/api/sports/futbol/competitions")
    assert resp.status_code == 200
    slugs = {c["slug"] for c in resp.json()}
    assert slugs == {
        "bundesliga",
        "2-bundesliga",
        "dfb-pokal",
        "laliga",
        "premier-league",
        "serie-a",
        "ligue-1",
        "champions-league",
        "europa-league",
        "conference-league",
        "segunda",
        "championship",
        "primeira-liga",
        "eredivisie",
    }


def test_unsupported_sport_is_404_not_empty_list():
    with TestClient(app) as client:
        resp = client.get("/api/sports/motorsport/competitions")
    assert resp.status_code == 404


def test_unknown_competition_is_404():
    with TestClient(app) as client:
        resp = client.get("/api/competitions/does-not-exist/matches")
    assert resp.status_code == 404


def test_bundesliga_matches_endpoint_returns_real_shape():
    data = load("openligadb_bl1_matchday.json")
    with respx.mock:
        respx.get(url__regex=r".*getmatchdata/bl1/\d+$").mock(
            return_value=httpx.Response(200, json=data)
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/bundesliga/matches")

    assert resp.status_code == 200
    body = resp.json()
    assert body["competition"]["slug"] == "bundesliga"
    assert len(body["matches"]) == len(data)


def test_bundesliga_standings_endpoint_returns_real_shape():
    data = load("openligadb_bl1_table.json")
    with respx.mock:
        respx.get(url__regex=r".*getbltable/bl1/.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/bundesliga/standings")

    assert resp.status_code == 200
    body = resp.json()
    assert body["standings"][0]["team"] == data[0]["teamName"]


def test_nba_standings_endpoint_reports_unavailable_not_error():
    # Verified live: this source has no NBA standings data. The API must
    # say so explicitly (null) rather than 500 or a fabricated table.
    with TestClient(app) as client:
        resp = client.get("/api/competitions/nba/standings")
    assert resp.status_code == 200
    assert resp.json()["standings"] is None


def test_dfb_pokal_standings_endpoint_reports_unavailable_not_error():
    with TestClient(app) as client:
        resp = client.get("/api/competitions/dfb-pokal/standings")
    assert resp.status_code == 200
    assert resp.json()["standings"] is None


def test_analysis_unknown_competition_is_404():
    with TestClient(app) as client:
        resp = client.get("/api/competitions/does-not-exist/matches/1/analysis")
    assert resp.status_code == 404


def test_analysis_unknown_match_id_is_404():
    data = load("openligadb_bl1_matchday.json")
    with respx.mock:
        respx.get(url__regex=r".*getmatchdata/bl1/\d+$").mock(
            return_value=httpx.Response(200, json=data)
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/bundesliga/matches/openligadb-999999/analysis")
    assert resp.status_code == 404


def test_analysis_on_a_finished_match_has_no_prediction_but_real_form():
    data = load("openligadb_bl1_matchday.json")
    with respx.mock:
        respx.get(url__regex=r".*getmatchdata/bl1/\d+$").mock(
            return_value=httpx.Response(200, json=data)
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/bundesliga/matches/openligadb-83208/analysis")

    assert resp.status_code == 200
    body = resp.json()
    # Already played: we never predict the past, and we say so explicitly.
    assert body["prediction"] is None
    assert "solo se calcula" in body["note"]
    # Real result for FC Schalke 04 (home, lost 0-1) shows up in its form.
    assert body["home_form"][0]["opponent"] == "1. FSV Mainz 05"
    assert body["home_form"][0]["outcome"] == "L"


def test_matches_endpoint_falls_back_to_openfootball_when_thesportsdb_is_entirely_down():
    # Round discovery itself fails too (every request to TheSportsDB is
    # rate-limited) — this must never show an empty LaLiga, OpenFootball's
    # real (if less current) full season schedule should be served.
    openfootball_data = load("openfootball_es1_sample.json")
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        respx.get(url__regex=r".*es\.1\.json$").mock(
            return_value=httpx.Response(200, json=openfootball_data)
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/matches")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["matches"]) == 4
    assert all(m["source"] == "openfootball" for m in body["matches"])


def test_matches_endpoint_merges_thesportsdbs_recent_window_into_the_full_season():
    # The real architecture this is meant to fix: OpenFootball has the
    # *fixtures* (it knows these 10 real matchups are scheduled) but is
    # stale on the *results* (no score yet). TheSportsDB's narrow window
    # overwrites exactly those 10 real fixtures with their real result,
    # by (home, away) identity — not by discarding a whole date range —
    # and leaves everything else (5 unrelated future fixtures) untouched.
    discovery_data = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "3"}]}
    round1 = load("thesportsdb_laliga_round1.json")  # 10 real finished matches
    real_pairings = [
        ("Sevilla", "Rayo Vallecano"),
        ("Deportivo Alavés", "Getafe"),
        ("Espanyol", "Levante"),
        ("Racing de Santander", "Villarreal"),
        ("Deportivo de A Coruña", "Elche"),
        ("Atlético Madrid", "Málaga"),
        ("Valencia", "Real Betis"),
        ("Real Madrid", "Real Sociedad"),
        ("Barcelona", "Athletic Bilbao"),
        ("Celta Vigo", "Osasuna"),
    ]
    full_season = {
        "matches": (
            [{"date": "2026-08-10", "team1": h, "team2": a} for h, a in real_pairings]  # no score yet
            + [{"date": "2026-11-01", "team1": f"Future{i}", "team2": f"Team{i}"} for i in range(5)]
        )
    }
    requested_rounds: list[str] = []

    def respond(request):
        requested_rounds.append(request.url.params["r"])
        return httpx.Response(200, json=round1)

    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=discovery_data)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=full_season))
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/matches")

    # current_round=3, back=3, forward=1 -> rounds [1,2,3,4].
    assert requested_rounds == ["1", "2", "3", "4"]
    assert resp.status_code == 200
    body = resp.json()
    # 10 real fixtures overwritten with TheSportsDB's real result
    # (deduplicated even though 4 requested rounds all mock to the same
    # 10 fixtures here) + 5 untouched future OpenFootball fixtures.
    assert len(body["matches"]) == 15
    by_pair = {(m["home"], m["away"]): m for m in body["matches"]}
    overwritten = by_pair[("Sevilla", "Rayo Vallecano")]
    assert overwritten["source"] == "thesportsdb"
    assert overwritten["status"] == "finished"
    assert overwritten["home_score"] == 2
    untouched = by_pair[("Future0", "Team0")]
    assert untouched["source"] == "openfootball"


def test_matches_endpoint_never_shows_a_past_dated_match_as_still_scheduled():
    # Real bug found live: a LaLiga fixture from 10 October stayed marked
    # "scheduled" in OpenFootball (TheSportsDB's window never happened to
    # reach that exact date), so it kept showing up in "Próximos
    # partidos" days after it should have been played. Any match whose
    # kickoff has already passed must never be reported as still
    # scheduled — demoted to "unknown" (never a fabricated score)
    # instead.
    discovery_data = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "1"}]}
    full_season = {
        "matches": [
            {"date": "2020-01-01", "team1": "A", "team2": "B"},  # long past, still "scheduled"
            {"date": "2026-11-01", "team1": "C", "team2": "D"},  # genuinely future
        ]
    }
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=discovery_data)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json={"events": None})
        )
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=full_season))
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/matches")

    body = resp.json()
    by_pair = {(m["home"], m["away"]): m for m in body["matches"]}
    assert by_pair[("A", "B")]["status"] == "unknown"
    assert by_pair[("C", "D")]["status"] == "scheduled"


def test_matches_endpoint_prefers_the_more_advanced_of_the_two_round_discovery_signals():
    # Real bug found live: TheSportsDB's live discovery can itself return
    # a stale round (e.g. served from an old cached answer during a rate
    # limit), which silently narrowed the fetch window and left a gap
    # right up to today uncovered. OpenFootball's own schedule dates are
    # a reliable, zero-network second signal — whichever round is more
    # advanced should win.
    stale_discovery = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "2"}]}
    # OpenFootball's own schedule says round 6 is the one nearest today —
    # more advanced than TheSportsDB's stale "round 2" answer.
    full_season = {
        "matches": [
            {"date": "2026-08-15", "round": "Matchday 1", "team1": "A", "team2": "B"},
            {"date": today_iso(), "round": "Matchday 6", "team1": "C", "team2": "D"},
        ]
    }
    requested_rounds: list[str] = []

    def respond(request):
        requested_rounds.append(request.url.params["r"])
        return httpx.Response(200, json={"events": None})

    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=stale_discovery)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=full_season))
        with TestClient(app) as client:
            client.get("/api/competitions/laliga/matches")

    # If round 2 (TheSportsDB's stale answer) had won, the window would
    # be [1,2,3]. Round 6 (OpenFootball's schedule-based estimate) wins
    # instead, giving window [3,4,5,6,7].
    assert requested_rounds == ["3", "4", "5", "6", "7"]


def test_matches_endpoint_never_overwrites_a_real_result_with_a_still_scheduled_one():
    # A TheSportsDB entry for a fixture that already has a real
    # OpenFootball result must never downgrade it back to "scheduled"
    # just because TheSportsDB's own copy of that match hasn't been
    # played yet in its data (e.g. a postponed-and-rescheduled fixture).
    discovery_data = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "1"}]}
    thesportsdb_data = {
        "events": [
            {
                "idEvent": "99",
                "strEvent": "Sevilla vs Rayo Vallecano",
                "strHomeTeam": "Sevilla",
                "strAwayTeam": "Rayo Vallecano",
                "intHomeScore": None,
                "intAwayScore": None,
                "strStatus": "NS",
                "dateEvent": "2026-12-01",
                "strTimestamp": "2026-12-01T20:00:00",
            }
        ]
    }
    full_season = {
        "matches": [
            {
                "date": "2026-08-10",
                "team1": "Sevilla",
                "team2": "Rayo Vallecano",
                "score": {"ft": [2, 1]},
            }
        ]
    }
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=discovery_data)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=thesportsdb_data)
        )
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=full_season))
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/matches")

    body = resp.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["status"] == "finished"
    assert body["matches"][0]["home_score"] == 2
    assert body["matches"][0]["source"] == "openfootball"


def test_matches_endpoint_prefers_thesportsdbs_real_kickoff_time_for_a_still_scheduled_fixture():
    # Real bug found live: OpenFootball's "scheduled" fixtures only carry
    # a placeholder date (midnight UTC, no real kick-off time), which
    # rendered as an implausible "02:00" local slot. TheSportsDB's
    # scheduled entry in the current round window has the real,
    # TV-confirmed day/time — it should win even though neither side has
    # a score yet.
    discovery_data = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "1"}]}
    thesportsdb_data = {
        "events": [
            {
                "idEvent": "99",
                "strEvent": "Barcelona vs Real Madrid",
                "strHomeTeam": "Barcelona",
                "strAwayTeam": "Real Madrid",
                "intHomeScore": None,
                "intAwayScore": None,
                "strStatus": "NS",
                "dateEvent": "2026-10-25",
                "strTimestamp": "2026-10-25T20:00:00",
            }
        ]
    }
    full_season = {
        "matches": [
            {"date": "2026-10-25", "team1": "Barcelona", "team2": "Real Madrid"}  # no time, no score
        ]
    }
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=discovery_data)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=thesportsdb_data)
        )
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=full_season))
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/matches")

    body = resp.json()
    assert len(body["matches"]) == 1
    assert body["matches"][0]["status"] == "scheduled"
    assert body["matches"][0]["source"] == "thesportsdb"
    assert body["matches"][0]["kickoff"] == "2026-10-25T20:00:00Z"


def test_standings_endpoint_serves_the_computed_table_not_the_5_row_capped_one():
    # Regression test: TheSportsDB's lookuptable.php is capped at exactly
    # 5 rows on the free tier (verified live — even a fixture captured
    # earlier for this project only ever had 5). /standings for a
    # round-based league must use our own computed table instead, which
    # covers every team in the matches already fetched.
    round1 = load("thesportsdb_laliga_round1.json")
    with respx.mock:
        # Round discovery itself fails here, so this falls back to the
        # old full 1..11 request pattern — keeps this test focused on
        # TheSportsDB's own round-1 result rather than the merge path.
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json={"events": None})
        )
        respx.get(url__regex=r".*eventsround\.php.*r=1&").mock(
            return_value=httpx.Response(200, json=round1)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json={"events": None})
        )
        respx.get(url__regex=r".*es\.1\.json$").mock(
            return_value=httpx.Response(200, json={"matches": []})
        )
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/standings")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["standings"]) == 20  # every team from round 1, not capped at 5


def test_audit_endpoint_reports_real_counts_against_the_real_expectation():
    discovery_data = {"events": [{"idEvent": "1", "strEvent": "X vs Y", "intRound": "1"}]}
    round1 = load("thesportsdb_laliga_round1.json")  # 10 real matches, 20 teams
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=discovery_data)
        )
        respx.get(url__regex=r".*eventsround\.php.*").mock(return_value=httpx.Response(200, json=round1))
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json={"matches": []}))
        with TestClient(app) as client:
            resp = client.get("/api/competitions/laliga/audit")

    assert resp.status_code == 200
    body = resp.json()
    assert body["competition_slug"] == "laliga"
    assert body["matches_found"] == 10
    assert body["matches_expected"] == 380
    assert body["teams_found"] == 20
    assert body["teams_expected"] == 20
    assert body["matches_complete"] is False  # honest: 10 of 380 real matches
    assert body["teams_complete"] is True  # all 20 real teams already appear
    assert body["is_complete"] is False
