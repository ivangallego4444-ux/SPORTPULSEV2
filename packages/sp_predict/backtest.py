"""Real accuracy measurement for the Poisson model — walk-forward, so a
match's own result never leaks into the prediction used to "grade" it.

For "algorithm accuracy" telemetry on the PRO dashboard: rather than
inventing a confident-sounding percentage, this replays every finished
match in chronological order, predicts each one using only the matches
that happened strictly before it, and checks whether the model's most-
likely outcome (home/draw/away) matched the real result. The resulting
percentage is real, reproducible, and only as good as the sample size it
reports alongside it.
"""

from __future__ import annotations

from sp_core.models import Match

from .history import _is_finished_with_score, _sort_key
from .poisson import predict_match


def backtest_accuracy(matches: list[Match]) -> tuple[int, int]:
    """Returns (correct, checked). `checked` is 0 when no finished match in
    this competition ever had enough real prior matches to predict from —
    callers must treat that as "no data" (not "100%" or "0%")."""
    finished = sorted(
        (m for m in matches if _is_finished_with_score(m)),
        key=_sort_key,
    )

    correct = 0
    checked = 0
    history: list[Match] = []

    for match in finished:
        prediction = predict_match(history, match.home, match.away)
        if prediction is not None:
            if match.home_score > match.away_score:
                actual = "home"
            elif match.home_score == match.away_score:
                actual = "draw"
            else:
                actual = "away"

            predicted = max(
                (
                    ("home", prediction.home_win_pct),
                    ("draw", prediction.draw_pct),
                    ("away", prediction.away_win_pct),
                ),
                key=lambda pair: pair[1],
            )[0]

            checked += 1
            if predicted == actual:
                correct += 1

        history.append(match)

    return correct, checked
