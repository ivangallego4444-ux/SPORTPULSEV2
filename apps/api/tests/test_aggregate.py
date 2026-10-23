from __future__ import annotations

from datetime import datetime, timezone

from sp_core.models import HighlightMatch, Match, MatchPrediction, MatchStatus
from sp_predict import pick_featured, pick_top_btts, pick_top_by_favorite, pick_top_over_2_5
from sp_predict.aggregate import team_aggregate_stats


def _match(
    match_id: str,
    home: str,
    away: str,
    home_score: int | None,
    away_score: int | None,
    day: int,
    status: MatchStatus = MatchStatus.FINISHED,
) -> Match:
    return Match(
        id=match_id,
        sport="futbol",
        competition_slug="test-league",
        competition_name="Test League",
        status=status,
        kickoff=datetime(2026, 1, day, tzinfo=timezone.utc),
        home=home,
        away=away,
        home_score=home_score,
        away_score=away_score,
        summary=None,
        venue=None,
        source="test",
    )


def _prediction(home_win: float, draw: float, away_win: float, over_2_5: float, btts: float) -> MatchPrediction:
    return MatchPrediction(
        method="test",
        confidence="real_history",
        home_matches_used=5,
        away_matches_used=5,
        h2h_matches_considered=0,
        h2h_adjustment_pct=0.0,
        home_attack_rating=1.0,
        home_defense_rating=1.0,
        away_attack_rating=1.0,
        away_defense_rating=1.0,
        expected_goals_home=1.5,
        expected_goals_away=1.0,
        home_win_pct=home_win,
        draw_pct=draw,
        away_win_pct=away_win,
        double_chance_1x_pct=home_win + draw,
        double_chance_x2_pct=draw + away_win,
        double_chance_12_pct=home_win + away_win,
        btts_yes_pct=btts,
        btts_no_pct=100 - btts,
        over_1_5_pct=over_2_5 + 10,
        over_2_5_pct=over_2_5,
        over_3_5_pct=max(over_2_5 - 20, 0),
        top_scorelines=[],
        scoreline_grid=[],
        asian_handicap=[],
        margin_distribution=[],
        recommended_pick_label="test",
        recommended_pick_pct=home_win,
        expected_corners_home=5.0,
        expected_corners_away=4.0,
        expected_corners_total=9.0,
        corners_over_8_5_pct=50.0,
        corners_over_9_5_pct=40.0,
        corners_favoured_side="home",
        note="test",
    )


class TestTeamAggregateStats:
    def test_returns_none_with_zero_matches_in_window(self):
        assert team_aggregate_stats([], "Alpha") is None

    def test_computes_real_averages_and_percentages(self):
        matches = [
            _match("1", "Alpha", "Beta", 3, 1, 1),  # over1.5, over2.5, over3.5, btts
            _match("2", "Gamma", "Alpha", 0, 2, 2),  # away win for Alpha, over1.5 only
        ]
        stats = team_aggregate_stats(matches, "Alpha")
        assert stats is not None
        assert stats.matches_played == 2
        assert stats.wins == 2
        assert stats.goals_for_avg == 2.5  # (3 + 2) / 2
        assert stats.over_2_5_pct == 50.0  # only match 1 has 4 total goals

    def test_venue_filter_only_counts_that_venue(self):
        matches = [
            _match("1", "Alpha", "Beta", 3, 1, 1),
            _match("2", "Gamma", "Alpha", 0, 2, 2),
        ]
        home_only = team_aggregate_stats(matches, "Alpha", venue="home")
        assert home_only is not None
        assert home_only.matches_played == 1

    def test_limit_caps_the_window_to_most_recent(self):
        matches = [_match(str(d), "Alpha", "Beta", 1, 0, d) for d in range(1, 6)]
        capped = team_aggregate_stats(matches, "Alpha", limit=2)
        assert capped is not None
        assert capped.matches_played == 2

    def test_ignores_unfinished_matches(self):
        matches = [_match("1", "Alpha", "Beta", None, None, 1, status=MatchStatus.SCHEDULED)]
        assert team_aggregate_stats(matches, "Alpha") is None


class TestPickFunctions:
    def _highlight(self, match_id, home_win, draw, away_win, over_2_5, btts, day=10) -> HighlightMatch:
        match = _match(match_id, "Home", "Away", None, None, day, status=MatchStatus.SCHEDULED)
        return HighlightMatch(
            match=match, prediction=_prediction(home_win, draw, away_win, over_2_5, btts)
        )

    def test_top_by_favorite_sorts_by_most_one_sided(self):
        a = self._highlight("a", 50, 30, 20, 40, 40)
        b = self._highlight("b", 90, 5, 5, 40, 40)
        result = pick_top_by_favorite([a, b], limit=2)
        assert [h.match.id for h in result] == ["b", "a"]

    def test_top_over_2_5_sorts_by_that_field(self):
        a = self._highlight("a", 50, 30, 20, 30, 40)
        b = self._highlight("b", 50, 30, 20, 80, 40)
        result = pick_top_over_2_5([a, b], limit=2)
        assert [h.match.id for h in result] == ["b", "a"]

    def test_top_btts_excludes_matches_without_a_prediction(self):
        a = self._highlight("a", 50, 30, 20, 30, 70)
        no_pred = HighlightMatch(
            match=_match("c", "X", "Y", None, None, 10, status=MatchStatus.SCHEDULED), prediction=None
        )
        result = pick_top_btts([a, no_pred], limit=4)
        assert [h.match.id for h in result] == ["a"]

    def test_featured_prefers_soonest_one_sided_upcoming_match(self):
        soon_close = self._highlight("soon_close", 55, 25, 20, 40, 40, day=5)
        soon_lopsided = self._highlight("soon_lopsided", 88, 7, 5, 40, 40, day=6)
        later = self._highlight("later", 95, 3, 2, 40, 40, day=20)
        result = pick_featured([soon_close, soon_lopsided, later])
        assert result is not None
        assert result.match.id == "soon_lopsided"

    def test_featured_falls_back_to_soonest_when_none_have_a_prediction(self):
        no_pred_soon = HighlightMatch(
            match=_match("x", "X", "Y", None, None, 3, status=MatchStatus.SCHEDULED), prediction=None
        )
        no_pred_later = HighlightMatch(
            match=_match("y", "X", "Y", None, None, 9, status=MatchStatus.SCHEDULED), prediction=None
        )
        result = pick_featured([no_pred_later, no_pred_soon])
        assert result is not None
        assert result.match.id == "x"

    def test_featured_is_none_with_no_upcoming_matches(self):
        finished_only = HighlightMatch(match=_match("z", "X", "Y", 1, 0, 1), prediction=None)
        assert pick_featured([finished_only]) is None
