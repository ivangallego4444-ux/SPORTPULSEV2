"""Computes a league table from real match results — for competitions
(like the UEFA Champions League's current league-phase format) where the
source gives no ready-made table endpoint, and for the five round-based
domestic leagues, whose source table endpoint (`lookuptable.php`) is
capped at exactly 5 rows on the free tier (verified live). Every number
here is a real sum over real finished matches — never invented.

Tiebreak cascades are the two real criteria orders actually used:

- "uefa": the UEFA league-phase order (points, goal difference, goals
  scored, away goals scored, wins, away wins). Omits the final fair-play
  / club-coefficient steps, since that isn't data we have — ties that
  reach that point fall back to team name, same as the rest of this
  module.
- "h2h": the head-to-head-before-goal-difference cascade most domestic
  leagues in this project use (points, then a head-to-head mini-table
  among the exact set of teams tied on points, then overall goal
  difference, goals scored, name). This is the standard method, not a
  byte-for-byte copy of each federation's full regulation text (which
  also covers disciplinary points, play-offs, etc. — not data we have).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sp_core.models import Match, StandingRow

from .history import _is_finished_with_score


@dataclass
class _Row:
    played: int = 0
    won: int = 0
    draw: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    away_goals_for: int = 0
    away_won: int = 0
    crest_url: str | None = field(default=None)


def _build_rows(finished: list[Match]) -> dict[str, _Row]:
    rows: dict[str, _Row] = {}

    def row_for(team: str, crest: str | None) -> _Row:
        row = rows.setdefault(team, _Row())
        if crest and not row.crest_url:
            row.crest_url = crest
        return row

    for m in finished:
        home = row_for(m.home, m.home_crest)
        away = row_for(m.away, m.away_crest)

        home.played += 1
        away.played += 1
        home.goals_for += m.home_score
        home.goals_against += m.away_score
        away.goals_for += m.away_score
        away.goals_against += m.home_score
        away.away_goals_for += m.away_score

        if m.home_score > m.away_score:
            home.won += 1
            home.points += 3
            away.lost += 1
        elif m.home_score < m.away_score:
            away.won += 1
            away.points += 3
            away.away_won += 1
            home.lost += 1
        else:
            home.draw += 1
            away.draw += 1
            home.points += 1
            away.points += 1

    return rows


def _gd(row: _Row) -> int:
    return row.goals_for - row.goals_against


def _uefa_order(rows: dict[str, _Row]) -> list[str]:
    return sorted(
        rows.keys(),
        key=lambda team: (
            -rows[team].points,
            -_gd(rows[team]),
            -rows[team].goals_for,
            -rows[team].away_goals_for,
            -rows[team].won,
            -rows[team].away_won,
            team,
        ),
    )


def _h2h_mini_table(team_names: list[str], finished: list[Match]) -> dict[str, tuple[int, int]]:
    """(points, goal_difference) for each team, counting only matches
    played against the other teams in `team_names` — the real
    head-to-head record among exactly this tied group."""
    mini: dict[str, tuple[int, int]] = {t: (0, 0) for t in team_names}
    group = set(team_names)
    for m in finished:
        if m.home not in group or m.away not in group:
            continue
        hp, hg = mini[m.home]
        ap, ag = mini[m.away]
        hg += m.home_score - m.away_score
        ag += m.away_score - m.home_score
        if m.home_score > m.away_score:
            hp += 3
        elif m.home_score < m.away_score:
            ap += 3
        else:
            hp += 1
            ap += 1
        mini[m.home] = (hp, hg)
        mini[m.away] = (ap, ag)
    return mini


def _h2h_order(rows: dict[str, _Row], finished: list[Match]) -> list[str]:
    provisional = sorted(
        rows.keys(),
        key=lambda team: (-rows[team].points, team),
    )

    result: list[str] = []
    i = 0
    while i < len(provisional):
        j = i
        while j + 1 < len(provisional) and rows[provisional[j + 1]].points == rows[provisional[i]].points:
            j += 1
        cluster = provisional[i : j + 1]
        if len(cluster) == 1:
            result.extend(cluster)
        else:
            mini = _h2h_mini_table(cluster, finished)
            cluster_sorted = sorted(
                cluster,
                key=lambda team: (
                    -mini[team][0],
                    -mini[team][1],
                    -_gd(rows[team]),
                    -rows[team].goals_for,
                    team,
                ),
            )
            result.extend(cluster_sorted)
        i = j + 1
    return result


def compute_table(
    matches: list[Match], tiebreak: Literal["uefa", "h2h"] = "h2h"
) -> list[StandingRow] | None:
    finished = [m for m in matches if _is_finished_with_score(m)]
    if not finished:
        return None

    rows = _build_rows(finished)
    order = _uefa_order(rows) if tiebreak == "uefa" else _h2h_order(rows, finished)

    return [
        StandingRow(
            rank=i + 1,
            team=team,
            played=rows[team].played,
            wins=rows[team].won,
            draws=rows[team].draw,
            losses=rows[team].lost,
            points=rows[team].points,
            crest_url=rows[team].crest_url,
        )
        for i, team in enumerate(order)
    ]
