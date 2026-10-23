"""OpenFootball provider tests. Fixture is a real, trimmed sample captured
live from raw.githubusercontent.com/openfootball/football.json on
2026-10-21 (2 finished + 2 scheduled fixtures from the real 2026-27
LaLiga file) — not invented data."""

from __future__ import annotations

import json
import pathlib
from datetime import date

import httpx
import respx

from sp_core.models import MatchStatus
from sp_providers.openfootball import (
    OpenFootballProvider,
    _estimate_current_round,
    _to_openfootball_season,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_season_string_conversion_matches_openfootballs_own_format():
    assert _to_openfootball_season("2026-2027") == "2026-27"


async def test_maps_real_fixture_honestly():
    data = load("openfootball_es1_sample.json")
    with respx.mock:
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(200, json=data))
        async with httpx.AsyncClient() as client:
            matches = await OpenFootballProvider().get_season(client, "laliga", "2026-2027")

    assert len(matches) == 4
    finished = [m for m in matches if m.status == MatchStatus.FINISHED]
    scheduled = [m for m in matches if m.status == MatchStatus.SCHEDULED]
    assert len(finished) == 2
    assert len(scheduled) == 2

    first = finished[0]
    assert first.home == "Deportivo Alavés"
    assert first.away == "Getafe"  # canonicalized from the raw "Getafe CF"
    assert first.home_score == 3
    assert first.away_score == 0
    assert first.source == "openfootball"
    # Never fabricates what the source doesn't give.
    assert first.home_id is None
    assert first.home_crest is None

    unplayed = scheduled[0]
    assert unplayed.home_score is None
    assert unplayed.away_score is None


async def test_unsupported_competition_returns_empty_not_an_error():
    async with httpx.AsyncClient() as client:
        matches = await OpenFootballProvider().get_season(client, "champions-league", "2026-2027")
    assert matches == []


async def test_handles_a_bare_list_score_not_just_the_dict_form():
    # Real bug found live: most matches give {"ht": [..], "ft": [h, a]},
    # but some rescheduled Premier League fixtures give a bare [h, a]
    # list directly as "score" — this used to raise AttributeError.
    data = {
        "name": "Test League 2026/27",
        "matches": [
            {
                "round": "Matchday 3",
                "date": "2026-09-05",
                "time": "15:00",
                "team1": "Nottingham Forest FC",
                "team2": "Tottenham Hotspur FC",
                "score": [0, 0],
            }
        ],
    }
    with respx.mock:
        respx.get(url__regex=r".*en\.1\.json$").mock(return_value=httpx.Response(200, json=data))
        async with httpx.AsyncClient() as client:
            matches = await OpenFootballProvider().get_season(client, "premier-league", "2026-2027")

    assert len(matches) == 1
    assert matches[0].status == MatchStatus.FINISHED
    assert matches[0].home_score == 0
    assert matches[0].away_score == 0


async def test_a_genuinely_missing_file_returns_empty():
    with respx.mock:
        respx.get(url__regex=r".*es\.1\.json$").mock(return_value=httpx.Response(404))
        async with httpx.AsyncClient() as client:
            matches = await OpenFootballProvider().get_season(client, "laliga", "2026-2027")
    assert matches == []


async def test_team_names_are_canonicalized_to_match_thesportsdbs_spelling():
    # Real bug found live: merging this source with TheSportsDB's recent
    # window produced duplicate standings rows for the same real club
    # (e.g. LaLiga showed 37 "teams" instead of 20) because the two
    # sources spell names differently. Every alias here was verified
    # against both sources' real current team lists, not guessed.
    data = {
        "matches": [
            {
                "date": "2026-08-15",
                "team1": "FC Internazionale Milano",
                "team2": "AS Roma",
                "score": {"ft": [2, 1]},
            }
        ]
    }
    with respx.mock:
        respx.get(url__regex=r".*it\.1\.json$").mock(return_value=httpx.Response(200, json=data))
        async with httpx.AsyncClient() as client:
            matches = await OpenFootballProvider().get_season(client, "serie-a", "2026-2027")

    assert matches[0].home == "Inter Milan"
    assert matches[0].away == "Roma"


class TestEstimateCurrentRound:
    def test_picks_the_round_of_the_match_closest_to_today(self):
        raw_matches = [
            {"date": "2026-09-20", "round": "Matchday 7"},
            {"date": "2026-10-04", "round": "Matchday 8"},
            {"date": "2026-10-18", "round": "Matchday 9"},
            {"date": "2026-11-01", "round": "Matchday 10"},
        ]
        assert _estimate_current_round(raw_matches, date(2026, 10, 22)) == 9

    def test_ignores_entries_missing_a_date_or_round(self):
        raw_matches = [
            {"date": "2026-10-20", "round": None},
            {"date": None, "round": "Matchday 9"},
            {"date": "2026-10-18", "round": "Matchday 9"},
        ]
        assert _estimate_current_round(raw_matches, date(2026, 10, 22)) == 9

    def test_returns_none_when_nothing_usable_is_available(self):
        assert _estimate_current_round([], date(2026, 10, 22)) is None


async def test_estimate_current_round_reuses_the_same_cached_raw_fetch_as_get_season():
    data = {
        "matches": [
            {"date": "2026-10-18", "round": "Matchday 9", "team1": "A", "team2": "B"},
        ]
    }
    call_count = 0

    def respond(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=data)

    provider = OpenFootballProvider()
    with respx.mock:
        respx.get(url__regex=r".*es\.1\.json$").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            await provider.get_season(client, "laliga", "2026-2027")
            round_number = await provider.estimate_current_round(
                client, "laliga", "2026-2027", today=date(2026, 10, 22)
            )

    assert call_count == 1  # the second call reused the cached raw fetch
    assert round_number == 9
