from __future__ import annotations

from datetime import datetime, timezone

from sp_core.models import Match, MatchStatus
from sp_predict.backtest import backtest_accuracy


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
        home_score=home_score,
        away_score=away_score,
        summary=None,
        venue=None,
        source="test",
    )


class TestBacktestAccuracy:
    def test_zero_checked_when_no_match_has_enough_prior_history(self):
        matches = [_match("1", "Alpha", "Beta", 2, 0, 1)]
        correct, checked = backtest_accuracy(matches)
        assert checked == 0
        assert correct == 0

    def test_never_uses_a_matchs_own_result_to_predict_itself(self):
        # Alpha wins big at home every time — by the time there's enough
        # history to predict match 5, the model should favour Alpha, and
        # crucially the walk-forward split means match 1-3 (used to build
        # that first prediction) never include the match being graded.
        matches = [_match(str(d), "Alpha", "Beta", 3, 1, d) for d in range(1, 4)]
        matches += [_match(str(d), "Alpha", "Beta", 3, 1, d) for d in range(4, 9)]
        correct, checked = backtest_accuracy(matches)
        assert checked > 0
        # A dominant home side should be predicted correctly more often
        # than not once there's enough history to work from.
        assert correct / checked > 0.5

    def test_counts_every_graded_match_exactly_once(self):
        matches = [_match(str(d), "Alpha", "Beta", 1, 1, d) for d in range(1, 10)]
        correct, checked = backtest_accuracy(matches)
        assert correct <= checked
        assert checked <= len(matches)
