"""Pure aggregation helpers over already-fetched real matches/predictions.
No network calls here — orchestration (which competitions to fetch) lives
in apps/api; this module only ever transforms data it's handed.
"""

from __future__ import annotations

from typing import Literal

from sp_core.models import HighlightMatch, Match, MatchStatus, TeamAggregateStats

from .history import _is_finished_with_score, _sort_key


def team_aggregate_stats(
    matches: list[Match],
    team_name: str,
    venue: Literal["all", "home", "away"] = "all",
    limit: int | None = None,
) -> TeamAggregateStats | None:
    """Real averages/percentages for one team over its matches in the
    given list, most recent first, optionally capped at `limit` games and
    filtered to home-only or away-only. Returns None when the filtered
    window has zero matches — there's nothing to average."""
    played = [m for m in matches if _is_finished_with_score(m) and (m.home == team_name or m.away == team_name)]
    if venue == "home":
        played = [m for m in played if m.home == team_name]
    elif venue == "away":
        played = [m for m in played if m.away == team_name]

    played.sort(key=_sort_key, reverse=True)
    if limit is not None:
        played = played[:limit]

    if not played:
        return None

    wins = draws = losses = 0
    goals_for_total = goals_against_total = 0
    over_1_5 = over_2_5 = over_3_5 = btts = 0

    for m in played:
        is_home = m.home == team_name
        goals_for = m.home_score if is_home else m.away_score
        goals_against = m.away_score if is_home else m.home_score
        total_goals = m.home_score + m.away_score

        if goals_for > goals_against:
            wins += 1
        elif goals_for == goals_against:
            draws += 1
        else:
            losses += 1

        goals_for_total += goals_for
        goals_against_total += goals_against
        if total_goals > 1.5:
            over_1_5 += 1
        if total_goals > 2.5:
            over_2_5 += 1
        if total_goals > 3.5:
            over_3_5 += 1
        if m.home_score >= 1 and m.away_score >= 1:
            btts += 1

    n = len(played)
    return TeamAggregateStats(
        matches_played=n,
        wins=wins,
        draws=draws,
        losses=losses,
        goals_for_avg=round(goals_for_total / n, 2),
        goals_against_avg=round(goals_against_total / n, 2),
        over_1_5_pct=round(100 * over_1_5 / n, 1),
        over_2_5_pct=round(100 * over_2_5 / n, 1),
        over_3_5_pct=round(100 * over_3_5 / n, 1),
        btts_pct=round(100 * btts / n, 1),
    )


def pick_top_by_favorite(highlights: list[HighlightMatch], limit: int = 4) -> list[HighlightMatch]:
    """Most one-sided predicted matches (highest of home/away win %)."""
    with_prediction = [h for h in highlights if h.prediction is not None]
    with_prediction.sort(
        key=lambda h: max(h.prediction.home_win_pct, h.prediction.away_win_pct), reverse=True
    )
    return with_prediction[:limit]


def pick_top_over_2_5(highlights: list[HighlightMatch], limit: int = 4) -> list[HighlightMatch]:
    with_prediction = [h for h in highlights if h.prediction is not None]
    with_prediction.sort(key=lambda h: h.prediction.over_2_5_pct, reverse=True)
    return with_prediction[:limit]


def pick_top_btts(highlights: list[HighlightMatch], limit: int = 4) -> list[HighlightMatch]:
    with_prediction = [h for h in highlights if h.prediction is not None]
    with_prediction.sort(key=lambda h: h.prediction.btts_yes_pct, reverse=True)
    return with_prediction[:limit]


def pick_featured(highlights: list[HighlightMatch], window_days: int = 7) -> HighlightMatch | None:
    """"Partido del día": among the matches kicking off soon (within
    `window_days` of the very next one — not "soon" by wall-clock, since
    this also runs in tests with synthetic dates), the most one-sided
    predicted one — more interesting to lead with than a coin-flip.
    Falls back to just the single soonest upcoming match if none in that
    window has a prediction, and to None if nothing is upcoming at all in
    what was fetched."""
    upcoming = [
        h for h in highlights if h.match.status == MatchStatus.SCHEDULED and h.match.kickoff is not None
    ]
    if not upcoming:
        return None

    upcoming.sort(key=lambda h: _sort_key(h.match))
    earliest = _sort_key(upcoming[0].match)
    window_seconds = window_days * 86400
    candidates = [h for h in upcoming if _sort_key(h.match) - earliest <= window_seconds]

    with_prediction = [h for h in candidates if h.prediction is not None]
    if with_prediction:
        return max(
            with_prediction, key=lambda h: max(h.prediction.home_win_pct, h.prediction.away_win_pct)
        )
    return candidates[0]
