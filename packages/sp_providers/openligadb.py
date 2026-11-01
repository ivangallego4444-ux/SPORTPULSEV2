from __future__ import annotations

from datetime import UTC, datetime

import httpx

from sp_core.models import Competition, Match, MatchStatus, StandingRow

from .base import TTLCache, fetch_json

SOURCE = "openligadb"
BASE_URL = "https://api.openligadb.de"

# OpenLigaDB's own shortcodes. Verified live on 2026-10-21: all three
# return real current-season data with no API key.
_SHORTCUTS = {
    "bundesliga": "bl1",
    "2-bundesliga": "bl2",
}

COMPETITIONS: dict[str, Competition] = {
    # badge_url values verified live via TheSportsDB's
    # search_all_leagues.php?c=Germany&s=Soccer (2026-10-23) — OpenLigaDB
    # itself has no league-level logo field, only team crests, so these
    # are the one real exception to "harvested for free from fetched
    # match data" (see thesportsdb.get_league_badge): a dedicated,
    # one-off verified lookup since this app's actual match/standings
    # data for these three still comes from OpenLigaDB, never TheSportsDB.
    "bundesliga": Competition(
        sport="futbol",
        slug="bundesliga",
        name="1. Bundesliga",
        source=SOURCE,
        supports_standings=True,
        supports_upcoming=True,
        country="Alemania",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/teqh1b1679952008.png",
    ),
    "2-bundesliga": Competition(
        sport="futbol",
        slug="2-bundesliga",
        name="2. Bundesliga",
        source=SOURCE,
        supports_standings=True,
        supports_upcoming=True,
        country="Alemania",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/hl40981534764789.png",
    ),
}


def _current_season_year(today: datetime | None = None) -> int:
    """German football seasons run roughly August-May; OpenLigaDB indexes
    tables by the year the season started."""
    today = today or datetime.now(UTC)
    return today.year if today.month >= 7 else today.year - 1


def _map_match(raw: dict, competition_slug: str) -> Match:
    team1 = raw.get("team1") or {}
    team2 = raw.get("team2") or {}
    results = raw.get("matchResults") or []
    final = next(
        (r for r in results if r.get("resultTypeKind") == "After90Minutes"),
        results[-1] if results else None,
    )
    home_score = final.get("pointsTeam1") if final else None
    away_score = final.get("pointsTeam2") if final else None

    kickoff: datetime | None
    try:
        kickoff = datetime.fromisoformat(raw["matchDateTime"])
    except (KeyError, ValueError):
        kickoff = None

    status = MatchStatus.FINISHED if raw.get("matchIsFinished") else MatchStatus.SCHEDULED

    return Match(
        id=f"openligadb-{raw.get('matchID')}",
        sport="futbol",
        competition_slug=competition_slug,
        competition_name=COMPETITIONS[competition_slug].name,
        status=status,
        kickoff=kickoff,
        home=team1.get("teamName"),
        away=team2.get("teamName"),
        home_id=str(team1["teamId"]) if team1.get("teamId") is not None else None,
        away_id=str(team2["teamId"]) if team2.get("teamId") is not None else None,
        home_crest=team1.get("teamIconUrl"),
        away_crest=team2.get("teamIconUrl"),
        home_score=home_score,
        away_score=away_score,
        summary=None,
        venue=None,
        source=SOURCE,
    )


class OpenLigaDBProvider:
    """Football (Germany) via api.openligadb.de — no API key, ODbL license."""

    def __init__(self, cache: TTLCache | None = None) -> None:
        self.cache = cache or TTLCache()

    async def get_matches(self, client: httpx.AsyncClient, competition_slug: str) -> list[Match]:
        # Full season (not just the current matchday): this is what makes
        # real upcoming fixtures show up at all — the single-matchday
        # endpoint can land on an all-finished matchday with nothing
        # upcoming — and gives enough real history per team for the
        # Poisson model and recent-form/H2H lookups in sp_predict.
        shortcut = _SHORTCUTS[competition_slug]
        season = _current_season_year()
        cache_key = f"openligadb:matches:{shortcut}:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await fetch_json(client, f"{BASE_URL}/getmatchdata/{shortcut}/{season}")
        if not data:
            return []

        matches = [_map_match(raw, competition_slug) for raw in data]
        self.cache.set(cache_key, matches, ttl_seconds=120)
        return matches

    async def get_standings(
        self, client: httpx.AsyncClient, competition_slug: str
    ) -> list[StandingRow] | None:
        competition = COMPETITIONS[competition_slug]
        if not competition.supports_standings:
            return None

        shortcut = _SHORTCUTS[competition_slug]
        season = _current_season_year()
        cache_key = f"openligadb:table:{shortcut}:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await fetch_json(client, f"{BASE_URL}/getbltable/{shortcut}/{season}")
        if not data:
            return None

        rows = [
            StandingRow(
                rank=i,
                team=row["teamName"],
                played=row.get("matches"),
                wins=row.get("won"),
                draws=row.get("draw"),
                losses=row.get("lost"),
                points=row.get("points"),
                crest_url=row.get("teamIconUrl"),
            )
            for i, row in enumerate(data, start=1)
        ]
        self.cache.set(cache_key, rows, ttl_seconds=300)
        return rows
