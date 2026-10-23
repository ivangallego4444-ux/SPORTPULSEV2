"""Team search and history, built purely from matches a competition's
provider already fetched — a team "exists" here only because it showed up
in real data, never from a separate team-directory fetch."""

from __future__ import annotations

from typing import Literal

import httpx

from sp_core.models import Match, TeamHistory, TeamSummary
from sp_predict import recent_form
from sp_predict.aggregate import team_aggregate_stats
from sp_providers.registry import ALL_COMPETITIONS

from .highlights import FOOTBALL_COMPETITION_SLUGS


def _teams_in(matches: list[Match], competition_slug: str) -> list[TeamSummary]:
    competition = ALL_COMPETITIONS[competition_slug]
    seen: dict[str, TeamSummary] = {}
    for match in matches:
        for name, team_id, crest in (
            (match.home, match.home_id, match.home_crest),
            (match.away, match.away_id, match.away_crest),
        ):
            if not name or not team_id or team_id in seen:
                continue
            seen[team_id] = TeamSummary(
                team_id=team_id,
                team_name=name,
                crest_url=crest,
                competition_slug=competition_slug,
                competition_name=competition.name,
                sport=competition.sport,
            )
    return list(seen.values())


async def search_teams(client: httpx.AsyncClient, fetch_matches, query: str, limit: int = 15) -> list[TeamSummary]:
    query_lower = query.strip().lower()
    if len(query_lower) < 2:
        return []

    results: list[TeamSummary] = []
    for slug in FOOTBALL_COMPETITION_SLUGS:
        try:
            matches = await fetch_matches(client, slug)
        except Exception:  # noqa: BLE001 - one competition failing shouldn't break search
            continue
        for team in _teams_in(matches, slug):
            if query_lower in team.team_name.lower():
                results.append(team)
                if len(results) >= limit:
                    return results
    return results


async def get_team_history(
    client: httpx.AsyncClient,
    fetch_matches,
    competition_slug: str,
    team_id: str,
    venue: Literal["all", "home", "away"],
    limit: int | None,
) -> TeamHistory | None:
    if competition_slug not in ALL_COMPETITIONS:
        return None

    matches = await fetch_matches(client, competition_slug)
    teams_by_id = {t.team_id: t for t in _teams_in(matches, competition_slug)}
    team = teams_by_id.get(team_id)
    if team is None:
        return None

    history = recent_form(matches, team.team_name, limit=100_000)
    if venue != "all":
        history = [h for h in history if h.venue == venue]
    if limit is not None:
        history = history[:limit]

    aggregate = team_aggregate_stats(matches, team.team_name, venue=venue, limit=limit)

    return TeamHistory(team=team, venue_filter=venue, matches=history, aggregate=aggregate)
