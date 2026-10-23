"""Regression test for a real bug found live: round-based fetching for
the Champions League pulled in July/August qualifying-round matches
(tiny clubs) mixed with the actual 36-team league phase (September
onward), which would badly skew both the computed table and the Poisson
model's "league average" if left unfiltered."""

from __future__ import annotations

from datetime import datetime, timezone

from app.main import _filter_uefa_league_phase
from sp_core.models import Match, MatchStatus


def _match(match_id: str, home: str, kickoff: datetime) -> Match:
    return Match(
        id=match_id,
        sport="futbol",
        competition_slug="champions-league",
        competition_name="UEFA Champions League",
        status=MatchStatus.FINISHED,
        kickoff=kickoff,
        home=home,
        away="Opponent",
        home_score=1,
        away_score=0,
        summary=None,
        venue=None,
        source="thesportsdb",
    )


def test_drops_qualifying_round_matches_before_september():
    qualifying = _match("1", "Sabah Baku", datetime(2026, 7, 15, tzinfo=timezone.utc))
    league_phase = _match("2", "Liverpool", datetime(2026, 9, 20, tzinfo=timezone.utc))
    result = _filter_uefa_league_phase([qualifying, league_phase], "champions-league")
    assert [m.id for m in result] == ["2"]


def test_keeps_matches_with_no_kickoff_excluded_not_crashed():
    no_kickoff = Match(
        id="3",
        sport="futbol",
        competition_slug="champions-league",
        competition_name="UEFA Champions League",
        status=MatchStatus.SCHEDULED,
        kickoff=None,
        home="Team",
        away="Other",
        home_score=None,
        away_score=None,
        summary=None,
        venue=None,
        source="thesportsdb",
    )
    assert _filter_uefa_league_phase([no_kickoff], "champions-league") == []
