from __future__ import annotations

from datetime import datetime, timezone

from sp_core.models import Match, MatchStatus
from sp_predict.standings import compute_table


def _match(match_id: str, home: str, away: str, home_score: int, away_score: int, day: int) -> Match:
    return Match(
        id=match_id,
        sport="futbol",
        competition_slug="test-league",
        competition_name="Test League",
        status=MatchStatus.FINISHED,
        kickoff=datetime(2026, 1, day, tzinfo=timezone.utc),
        home=home,
        away=away,
        home_crest="home.png" if home == "Alpha" else None,
        home_score=home_score,
        away_score=away_score,
        summary=None,
        venue=None,
        source="test",
    )


class TestComputeTable:
    def test_returns_none_with_no_finished_matches(self):
        assert compute_table([]) is None

    def test_computes_real_points_from_real_results(self):
        matches = [
            _match("1", "Alpha", "Beta", 3, 0, 1),  # Alpha win
            _match("2", "Beta", "Gamma", 1, 1, 2),  # draw
            _match("3", "Gamma", "Alpha", 0, 2, 3),  # Alpha win
        ]
        table = compute_table(matches)
        assert table is not None
        alpha = next(r for r in table if r.team == "Alpha")
        assert alpha.points == 6
        assert alpha.wins == 2
        assert alpha.played == 2

    def test_ranks_by_points_then_goal_difference(self):
        matches = [
            _match("1", "Alpha", "Beta", 5, 0, 1),  # Alpha +5
            _match("2", "Gamma", "Delta", 1, 0, 2),  # Gamma +1
        ]
        table = compute_table(matches)
        assert table is not None
        assert table[0].team == "Alpha"  # both have 3 points, Alpha has better GD
        assert table[0].rank == 1

    def test_keeps_a_real_crest_when_one_is_available(self):
        matches = [_match("1", "Alpha", "Beta", 1, 0, 1)]
        table = compute_table(matches)
        assert table is not None
        alpha = next(r for r in table if r.team == "Alpha")
        assert alpha.crest_url == "home.png"

    def test_h2h_tiebreak_resolves_a_real_points_tie_via_direct_results(self):
        # Alpha and Beta both finish on 3 points with identical overall
        # goal difference (0) — only their one real meeting (Alpha beat
        # Beta there) should decide who ranks above whom under the "h2h"
        # cascade, which is the real, requested fix for the old
        # points-then-GD-only table.
        matches = [
            _match("ab", "Alpha", "Beta", 2, 1, 1),  # Alpha wins the h2h
            _match("ac", "Alpha", "Gamma", 0, 3, 2),  # Alpha's offsetting loss
            _match("bc", "Beta", "Delta", 1, 0, 3),  # Beta's extra win elsewhere
        ]
        # Alpha: 1W1L, GF2 GA4 -> GD -2, 3 pts. Beta: 1L1W, GF2 GA3 -> GD -1, 3pts.
        # Overall GD actually favours Beta (-1 vs -2), but the real h2h
        # meeting was an Alpha win — h2h must be checked before overall GD.
        table = compute_table(matches, tiebreak="h2h")
        assert table is not None
        alpha_rank = next(r.rank for r in table if r.team == "Alpha")
        beta_rank = next(r.rank for r in table if r.team == "Beta")
        assert alpha_rank < beta_rank

    def test_uefa_tiebreak_uses_away_goals_before_wins(self):
        # Two teams tied on points (4), goal difference (+2) and goals
        # scored (3): the UEFA cascade must then prefer whoever scored
        # more as an away side (real data only — no fair-play/coefficient
        # data here, so the cascade stops at away goals/wins).
        matches = [
            _match("1", "Alpha", "X1", 2, 0, 1),  # Alpha home win
            _match("2", "X2", "Alpha", 1, 1, 2),  # Alpha away draw, 1 away goal
            _match("3", "Beta", "X3", 3, 1, 1),  # Beta home win
            _match("4", "X4", "Beta", 0, 0, 2),  # Beta away draw, 0 away goals
        ]
        table = compute_table(matches, tiebreak="uefa")
        assert table is not None
        alpha_rank = next(r.rank for r in table if r.team == "Alpha")
        beta_rank = next(r.rank for r in table if r.team == "Beta")
        assert alpha_rank < beta_rank

    def test_ignores_scheduled_matches(self):
        finished = _match("1", "Alpha", "Beta", 1, 0, 1)
        scheduled = Match(
            id="2",
            sport="futbol",
            competition_slug="test-league",
            competition_name="Test League",
            status=MatchStatus.SCHEDULED,
            kickoff=datetime(2026, 1, 5, tzinfo=timezone.utc),
            home="Gamma",
            away="Delta",
            home_score=None,
            away_score=None,
            summary=None,
            venue=None,
            source="test",
        )
        table = compute_table([finished, scheduled])
        assert table is not None
        teams = {r.team for r in table}
        assert "Gamma" not in teams and "Delta" not in teams
