"""Recent-form and head-to-head, derived from real fetched matches only.

Both functions only ever read `Match` objects a provider already fetched
from a verified source — they never call out to the network and never
invent a result. An empty list means the data genuinely isn't in what was
fetched (e.g. these two teams haven't played each other this season), not
an error.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sp_core.models import FormResult, Match, MatchStatus


def _sort_key(match: Match) -> float:
    if match.kickoff is None:
        return 0.0
    kickoff = match.kickoff if match.kickoff.tzinfo else match.kickoff.replace(tzinfo=timezone.utc)
    return kickoff.timestamp()


def _to_form_result(match: Match, perspective_team: str) -> FormResult:
    is_home = match.home == perspective_team
    goals_for = match.home_score if is_home else match.away_score
    goals_against = match.away_score if is_home else match.home_score
    opponent = match.away if is_home else match.home
    outcome = "W" if goals_for > goals_against else ("D" if goals_for == goals_against else "L")
    return FormResult(
        match_id=match.id,
        date=match.kickoff,
        opponent=opponent or "?",
        venue="home" if is_home else "away",
        goals_for=goals_for,
        goals_against=goals_against,
        outcome=outcome,
    )


def _is_finished_with_score(match: Match) -> bool:
    return (
        match.status == MatchStatus.FINISHED
        and match.home_score is not None
        and match.away_score is not None
        and bool(match.home)
        and bool(match.away)
    )


def recent_form(matches: list[Match], team_name: str, limit: int = 5) -> list[FormResult]:
    played = [
        m for m in matches if _is_finished_with_score(m) and (m.home == team_name or m.away == team_name)
    ]
    played.sort(key=_sort_key, reverse=True)
    return [_to_form_result(m, team_name) for m in played[:limit]]


def head_to_head(matches: list[Match], team_a: str, team_b: str, limit: int = 10) -> list[FormResult]:
    """Results from `team_a`'s point of view."""
    played = [m for m in matches if _is_finished_with_score(m) and {m.home, m.away} == {team_a, team_b}]
    played.sort(key=_sort_key, reverse=True)
    return [_to_form_result(m, team_a) for m in played[:limit]]
