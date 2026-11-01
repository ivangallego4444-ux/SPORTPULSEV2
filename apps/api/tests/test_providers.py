"""Provider mapping tests.

Fixtures under tests/fixtures/*.json are real responses captured from the
live APIs on 2026-10-21 while building this (see docs/DATA_SOURCES.md) —
not invented payloads. These tests only check that our mapping logic
handles that real shape correctly, including the honest "no data" cases
(empty standings, null next-events for tennis).
"""

from __future__ import annotations

import json
import pathlib

import httpx
import pytest
import respx

from sp_core.models import MatchStatus
from sp_providers.openligadb import OpenLigaDBProvider
from sp_providers.thesportsdb import TheSportsDBProvider

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_openligadb_matches_map_real_fixture():
    data = load("openligadb_bl1_matchday.json")
    with respx.mock:
        respx.get(url__regex=r".*getmatchdata/bl1/\d+$").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            matches = await OpenLigaDBProvider().get_matches(client, "bundesliga")

    assert len(matches) == len(data)
    first, raw_first = matches[0], data[0]
    assert first.sport == "futbol"
    assert first.home == raw_first["team1"]["teamName"]
    assert first.away == raw_first["team2"]["teamName"]
    if raw_first["matchIsFinished"]:
        assert first.status == MatchStatus.FINISHED
        assert first.home_score is not None
        assert first.away_score is not None


@pytest.mark.asyncio
async def test_openligadb_standings_map_real_fixture():
    data = load("openligadb_bl1_table.json")
    with respx.mock:
        respx.get(url__regex=r".*getbltable/bl1/.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            standings = await OpenLigaDBProvider().get_standings(client, "bundesliga")

    assert standings is not None
    assert standings[0].rank == 1
    assert standings[0].team == data[0]["teamName"]
    assert standings[0].points == data[0]["points"]


@pytest.mark.asyncio
async def test_thesportsdb_nba_structured_matches_map_real_fixture():
    data = load("thesportsdb_nba_season.json")
    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_recent(client, "nba", "2024-2025")

    assert len(matches) == len(data["events"])
    raw_first = data["events"][0]
    match = next(m for m in matches if m.id == f"thesportsdb-{raw_first['idEvent']}")
    assert match.home == raw_first["strHomeTeam"]
    assert match.away == raw_first["strAwayTeam"]
    assert match.home_score == int(raw_first["intHomeScore"])
    assert match.away_score == int(raw_first["intAwayScore"])


@pytest.mark.asyncio
async def test_thesportsdb_tennis_drops_events_with_no_identifiable_players():
    # Real bug found live: this exact captured fixture — eventsseason.php
    # for ATP — has no `strDescriptionEN` on any of its 15 events (only
    # `strEvent`, which mixes the tournament name into the player names
    # with no reliable separator), so none of them can be honestly
    # parsed into real player names. Mapping them anyway produced 15
    # "finished" matches with no team names and no score at all — blank
    # cards. A match with nothing identifiable on either side is dropped
    # entirely rather than surfaced as a Match full of nulls.
    data = load("thesportsdb_atp_season.json")
    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_recent(client, "atp", "2026")

    assert matches == []


@pytest.mark.asyncio
async def test_thesportsdb_tennis_never_fabricates_a_score_split():
    # A real, parseable tennis event (strDescriptionEN's last line is
    # "Player1 vs Player2") still never gets a guessed numeric score —
    # tennis has no structured score fields on this source, only free
    # text (strResult), which is kept as-is for display.
    raw_event = {
        "idEvent": "1",
        "strEvent": "Lyon Open Fritz vs Musetti",
        "strDescriptionEN": "Lyon Open - Lyon - The Final\r\nFritz (14) vs Musetti (26)",
        "strResult": "Musetti beat Fritz 2-0\r\nMusetti : 6 6\r\nFritz : 3 4",
        "strStatus": "",
        "dateEvent": "2026-10-25",
        "strTimestamp": "2026-10-25T00:00:00",
    }
    data = {"events": [raw_event]}
    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_recent(client, "atp", "2026")

    assert len(matches) == 1
    match = matches[0]
    assert match.home == "Fritz"
    assert match.away == "Musetti"
    assert match.home_score is None
    assert match.away_score is None
    assert match.status == MatchStatus.FINISHED  # real strResult text is evidence enough
    assert match.title  # raw event title kept for display


@pytest.mark.asyncio
async def test_thesportsdb_atp_upcoming_is_genuinely_empty():
    # Real captured response for this endpoint was literally {"events": null}.
    data = load("thesportsdb_atp_next.json")
    assert data == {"events": None}
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_upcoming(client, "atp")
    assert matches == []


@pytest.mark.asyncio
async def test_thesportsdb_laliga_rounds_map_real_fixture():
    # eventsseason.php caps at ~15 events for the whole competition
    # (verified live), so football leagues fetch per-round instead.
    data = load("thesportsdb_laliga_round1.json")
    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            # max_rounds=1 keeps this test fast (no point exercising the
            # real pacing delay between rounds here — that's a live-call
            # concern, not a mapping-logic one).
            matches = await TheSportsDBProvider().get_rounds(
                client, "laliga", "2026-2027", max_rounds=1
            )

    assert len(matches) == len(data["events"])
    raw_first = data["events"][0]
    match = next(m for m in matches if m.id == f"thesportsdb-{raw_first['idEvent']}")
    assert match.home == raw_first["strHomeTeam"]
    assert match.home_id == raw_first["idHomeTeam"]
    assert match.home_score == int(raw_first["intHomeScore"])


@pytest.mark.asyncio
async def test_thesportsdb_rate_limited_response_gets_a_short_lived_cache_entry():
    # Regression test: a 429 used to get cached as "[]" for 15 minutes,
    # so the UI stayed stuck on "no data" long after the free key's burst
    # limit had actually cleared. Checks the stored expiry directly
    # (rather than sleeping past the real TTL, which would make this test
    # slow/flaky) to prove a failed fetch gets a short retry window, not
    # the long success TTL.
    import time

    provider = TheSportsDBProvider()

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            result = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)
    assert result == []

    cache_key = "thesportsdb:rounds:laliga:2026-2027:1"
    expires_at, cached_value = provider.cache._store[cache_key]
    assert cached_value == []
    assert expires_at - time.monotonic() < 30  # short retry window, not the 900s success TTL


@pytest.mark.asyncio
async def test_thesportsdb_partial_round_failure_also_gets_a_short_lived_cache_entry():
    # Regression test for a real bug found live: LaLiga's matches list
    # dropped from ~80+ to exactly 10 (one round's worth) after some
    # rounds got rate-limited mid-fetch — but because *some* matches came
    # back, the old code treated the whole fetch as a success and cached
    # that incomplete season for the full 900s, locking in missing data
    # for 15 minutes. A fetch where even one round failed must get the
    # short retry TTL too, not just a fully-empty one.
    import time

    provider = TheSportsDBProvider()
    round_1_data = load("thesportsdb_laliga_round1.json")

    call_count = 0

    def respond(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=round_1_data)
        return httpx.Response(429, text="error code: 1015")

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            result = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=3)

    assert len(result) == len(round_1_data["events"])  # round 1's real matches came through

    cache_key = "thesportsdb:rounds:laliga:2026-2027:3"
    expires_at, cached_value = provider.cache._store[cache_key]
    assert len(cached_value) == len(round_1_data["events"])
    assert expires_at - time.monotonic() < 30  # short retry window despite having *some* data


@pytest.mark.asyncio
async def test_thesportsdb_standings_map_real_fixture():
    data = load("thesportsdb_premierleague_table.json")
    with respx.mock:
        respx.get(url__regex=r".*lookuptable\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            standings = await TheSportsDBProvider().get_standings(
                client, "premier-league", "2024-2025"
            )

    assert standings is not None
    assert standings[0].team == data["table"][0]["strTeam"]
    assert standings[0].points == int(data["table"][0]["intPoints"])


@pytest.mark.asyncio
async def test_thesportsdb_lookuptable_is_empty_for_champions_league():
    # TheSportsDB's own table endpoint genuinely has nothing for the
    # Champions League's league-phase format (verified live). The app
    # still shows a real table for it — computed locally from match
    # results via sp_predict.compute_table, wired in apps/api/app/main.py
    # — but this provider method on its own correctly reports "no data"
    # rather than fabricating one.
    with respx.mock:
        respx.get(url__regex=r".*lookuptable\.php.*").mock(
            return_value=httpx.Response(200, json={"table": []})
        )
        async with httpx.AsyncClient() as client:
            standings = await TheSportsDBProvider().get_standings(
                client, "champions-league", "2026-2027"
            )
    assert standings is None


@pytest.mark.asyncio
async def test_thesportsdb_serves_last_known_good_rounds_when_a_retry_is_rate_limited():
    # Real-world fix: two processes (or just bursty load) sharing
    # TheSportsDB's free demo key can rate-limit a *retry* even after an
    # earlier fetch genuinely succeeded. That must never erase the real
    # data already loaded — the UI should keep showing it (fixtures,
    # standings) while a short-TTL retry keeps trying in the background,
    # not go blank.
    provider = TheSportsDBProvider()
    round_1_data = load("thesportsdb_laliga_round1.json")
    cache_key = "thesportsdb:rounds:laliga:2026-2027:1"

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=round_1_data)
        )
        async with httpx.AsyncClient() as client:
            first = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)
    assert len(first) == len(round_1_data["events"])

    # Force the short "fresh" cache entry to actually expire (without a
    # real sleep) so the next call hits the network again.
    provider.cache._store.pop(cache_key, None)

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            second = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)

    assert len(second) == len(round_1_data["events"])  # served from known-good, not []


@pytest.mark.asyncio
async def test_thesportsdb_remembers_a_partial_success_as_known_good():
    # Real bug found live: the known-good fallback used to require a
    # *perfect* fetch (zero failed rounds) before remembering anything —
    # but TheSportsDB's burst limit very often trips on just the last
    # round of an 11-round fetch even on an otherwise-healthy key, so the
    # fallback almost never actually had data to serve. A partial success
    # (here: round 1 of 2 succeeds, round 2 is rate-limited) must still
    # be remembered and served on a later total failure.
    provider = TheSportsDBProvider()
    round_1_data = load("thesportsdb_laliga_round1.json")
    cache_key = "thesportsdb:rounds:laliga:2026-2027:2"

    call_count = 0

    def respond(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=round_1_data)
        return httpx.Response(429, text="error code: 1015")

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            first = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=2)
    assert len(first) == len(round_1_data["events"])

    provider.cache._store.pop(cache_key, None)  # expire the short-TTL entry

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            second = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=2)

    assert len(second) == len(round_1_data["events"])  # served from the partial known-good, not []


@pytest.mark.asyncio
async def test_thesportsdb_known_good_survives_a_process_restart_via_disk(tmp_path):
    # Real problem found live: restarting the backend to pick up a code
    # change wiped the in-memory known-good cache, making a league that
    # had already loaded correctly look broken again for no real reason.
    # A new provider instance pointed at the same store file must pick
    # up where the old one left off.
    store_path = tmp_path / "cache_store.json"
    round_1_data = load("thesportsdb_laliga_round1.json")

    first_provider = TheSportsDBProvider(known_good_store_path=store_path)
    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=round_1_data)
        )
        async with httpx.AsyncClient() as client:
            first = await first_provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)
    assert len(first) == len(round_1_data["events"])
    assert store_path.exists()

    # Simulate a restart: a brand-new provider instance, same store file,
    # and this time the API is fully rate-limited from the very first call.
    second_provider = TheSportsDBProvider(known_good_store_path=store_path)
    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            second = await second_provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)

    assert len(second) == len(round_1_data["events"])  # restored from disk, not []


@pytest.mark.asyncio
async def test_thesportsdb_fresh_cache_never_regresses_below_known_good():
    # Real bug found live: a *fresh* (within its 20s TTL) but worse
    # partial result — e.g. only 1 of 11 rounds came through this time —
    # was being served as-is even though an earlier attempt had already
    # produced a much more complete known-good snapshot. The UI must
    # never visibly regress to less real data than it already had.
    provider = TheSportsDBProvider()
    round_1_data = load("thesportsdb_laliga_round1.json")
    cache_key = "thesportsdb:rounds:laliga:2026-2027:1"

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(
            return_value=httpx.Response(200, json=round_1_data)
        )
        async with httpx.AsyncClient() as client:
            first = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)
    assert len(first) == len(round_1_data["events"])

    # Manually plant a worse but still "fresh" partial result, as if a
    # later attempt within the same 20s window had only managed a single
    # match before getting rate-limited.
    provider.cache.set(cache_key, first[:1], ttl_seconds=20)

    async with httpx.AsyncClient() as client:
        second = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)

    assert len(second) == len(round_1_data["events"])  # served known-good, not the worse fresh entry


@pytest.mark.asyncio
async def test_thesportsdb_a_fully_finished_round_is_never_refetched():
    # Point 2 of the user's request: a finished matchday's real result
    # never changes, so re-fetching it on every request just burns a slot
    # of the free key's burst budget for nothing.
    provider = TheSportsDBProvider()
    round_1_data = load("thesportsdb_laliga_round1.json")  # all FT (finished)

    call_count = 0

    def respond(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=round_1_data)

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)
    assert call_count == 1

    # Force the aggregate-level short cache entry to expire so a second
    # call actually re-enters the per-round fetch path — the finished
    # round itself must still be served from its own permanent entry.
    provider.cache._store.pop("thesportsdb:rounds:laliga:2026-2027:1", None)

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            result = await provider.get_rounds(client, "laliga", "2026-2027", max_rounds=1)

    assert call_count == 1  # no new network call for the already-finished round
    assert len(result) == len(round_1_data["events"])


@pytest.mark.asyncio
async def test_thesportsdb_discover_current_round_reads_the_real_intRound_field():
    data = {
        "events": [
            {
                "idEvent": "1",
                "strEvent": "A vs B",
                "intRound": "8",
                "strHomeTeam": "A",
                "strAwayTeam": "B",
            }
        ]
    }
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            round_number = await TheSportsDBProvider().discover_current_round(client, "serie-a")
    assert round_number == 8


@pytest.mark.asyncio
async def test_thesportsdb_discover_current_round_is_none_when_genuinely_unavailable():
    with respx.mock:
        respx.get(url__regex=r".*eventsnextleague\.php.*").mock(
            return_value=httpx.Response(200, json={"events": None})
        )
        async with httpx.AsyncClient() as client:
            round_number = await TheSportsDBProvider().discover_current_round(client, "serie-a")
    assert round_number is None


@pytest.mark.asyncio
async def test_thesportsdb_get_recent_rounds_only_fetches_the_given_window():
    round_1_data = load("thesportsdb_laliga_round1.json")
    requested_rounds: list[str] = []

    def respond(request):
        requested_rounds.append(request.url.params["r"])
        return httpx.Response(200, json=round_1_data)

    with respx.mock:
        respx.get(url__regex=r".*eventsround\.php.*").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_recent_rounds(
                client, "laliga", "2026-2027", range(6, 9)
            )

    assert requested_rounds == ["6", "7", "8"]  # exactly the narrow window, not 1..11
    assert len(matches) == 3 * len(round_1_data["events"])


@pytest.mark.asyncio
async def test_thesportsdb_serves_last_known_good_recent_matches_on_rate_limit():
    provider = TheSportsDBProvider()
    data = load("thesportsdb_nba_season.json")
    cache_key = "thesportsdb:season:nba:2024-2025"

    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(200, json=data)
        )
        async with httpx.AsyncClient() as client:
            first = await provider.get_recent(client, "nba", "2024-2025")
    assert len(first) == len(data["events"])

    provider.cache._store.pop(cache_key, None)

    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            second = await provider.get_recent(client, "nba", "2024-2025")

    assert len(second) == len(data["events"])


@pytest.mark.asyncio
async def test_provider_returns_empty_on_rate_limit_instead_of_crashing():
    # Confirmed live: TheSportsDB's free key starts returning HTTP 429
    # under bursty load. The provider must degrade to "no data" rather
    # than raising, so the API/UI can show an honest empty state.
    with respx.mock:
        respx.get(url__regex=r".*eventsseason\.php.*").mock(
            return_value=httpx.Response(429, text="error code: 1015")
        )
        async with httpx.AsyncClient() as client:
            matches = await TheSportsDBProvider().get_recent(client, "nba", "2024-2025")
    assert matches == []
