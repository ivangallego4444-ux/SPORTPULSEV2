"""OpenFootball (github.com/openfootball/football.json) — static JSON
files served from GitHub's raw CDN, dedicated to the public domain (see
the project's own README: "dedicated to the public domain. Use as you
please with no restrictions whatsoever."). No API key, no rate limit for
our traffic volume.

Used only as a gap-filler, never as the primary source: verified live
that this community-maintained dataset lags real results by roughly a
month (its most recent real score was about 4 matchdays behind
TheSportsDB on the day this was built). It also has no Champions League
file at all — only the five domestic leagues below. Every match this
provider returns is tagged `source="openfootball"` so the rest of the
app can tell it apart from TheSportsDB's fresher data, and callers are
expected to only reach for it when TheSportsDB itself came back thin or
empty — never to silently prefer a staler dataset over a fresher real
one.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from sp_core.models import Match, MatchStatus

from .base import TTLCache, fetch_json

SOURCE = "openfootball"
BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"

# openfootball's own file codes, verified live to exist with full real
# season schedules (380/380/380/306/306 matches respectively — correct
# for 20-team vs 18-team double round-robins).
_FILES = {
    "laliga": "es.1",
    "premier-league": "en.1",
    "serie-a": "it.1",
    "ligue-1": "fr.1",
    "bundesliga": "de.1",
    "championship": "en.2",
    "primeira-liga": "pt.1",
    "eredivisie": "nl.1",
    # "segunda" deliberately excluded: verified live that OpenFootball's
    # community file for the 2026-27 season (es.2.json) 404s — last
    # published season was 2025-26. Segunda is TheSportsDB-only until that
    # changes (see main.py's routing, same pattern as champions-league).
}

COMPETITION_NAMES = {
    "laliga": "LaLiga",
    "premier-league": "Premier League",
    "serie-a": "Serie A",
    "ligue-1": "Ligue 1",
    "bundesliga": "1. Bundesliga",
    "championship": "EFL Championship",
    "primeira-liga": "Primeira Liga",
    "eredivisie": "Eredivisie",
}

# Real bug found live: merging this source with TheSportsDB's recent
# window (see apps/api/app/main.py) produced duplicate rows in the
# standings table — e.g. LaLiga showed 37 "teams" instead of 20, because
# OpenFootball spells club names differently ("FC Internazionale Milano"
# vs TheSportsDB's "Inter Milan"). Verified by directly comparing both
# sources' real current team lists for the 2026-27 season (not guessed) —
# every entry below is a confirmed same-club pairing. A season-specific,
# hand-verified map is the only safe fix: a generic fuzzy/substring
# matcher risks silently merging two *different* real clubs that happen
# to share a city name (e.g. "Real Madrid" and "Atlético Madrid" both
# contain "Madrid").
_TEAM_NAME_ALIASES: dict[str, dict[str, str]] = {
    "laliga": {
        "FC Barcelona": "Barcelona",
        "Club Atlético de Madrid": "Atlético Madrid",
        "Real Betis Balompié": "Real Betis",
        "Real Madrid CF": "Real Madrid",
        "Sevilla FC": "Sevilla",
        "RC Deportivo La Coruña": "Deportivo de A Coruña",
        "Real Sociedad de Fútbol": "Real Sociedad",
        "CA Osasuna": "Osasuna",
        "Rayo Vallecano de Madrid": "Rayo Vallecano",
        "Villarreal CF": "Villarreal",
        "Athletic Club": "Athletic Bilbao",
        "Getafe CF": "Getafe",
        "RC Celta de Vigo": "Celta Vigo",
        "RCD Espanyol de Barcelona": "Espanyol",
        "Real Racing Club de Santander": "Racing de Santander",
        "Levante UD": "Levante",
        "Elche CF": "Elche",
        "Valencia CF": "Valencia",
        "Málaga CF": "Málaga",
    },
    "premier-league": {
        "Manchester City FC": "Manchester City",
        "Arsenal FC": "Arsenal",
        "Brighton & Hove Albion FC": "Brighton and Hove Albion",
        "Brentford FC": "Brentford",
        "Leeds United FC": "Leeds United",
        "Liverpool FC": "Liverpool",
        "Everton FC": "Everton",
        "Newcastle United FC": "Newcastle United",
        "Hull City AFC": "Hull City",
        "Chelsea FC": "Chelsea",
        "Ipswich Town FC": "Ipswich Town",
        "Manchester United FC": "Manchester United",
        "Nottingham Forest FC": "Nottingham Forest",
        "Tottenham Hotspur FC": "Tottenham Hotspur",
        "Aston Villa FC": "Aston Villa",
        "Sunderland AFC": "Sunderland",
        "Crystal Palace FC": "Crystal Palace",
        "Coventry City FC": "Coventry City",
        "AFC Bournemouth": "Bournemouth",
        "Fulham FC": "Fulham",
    },
    "serie-a": {
        "AS Roma": "Roma",
        "FC Internazionale Milano": "Inter Milan",
        "SS Lazio": "Lazio",
        "Cagliari Calcio": "Cagliari",
        "Frosinone Calcio": "Frosinone",
        "Juventus FC": "Juventus",
        "Como 1907": "Como",
        "SSC Napoli": "Napoli",
        "US Sassuolo Calcio": "Sassuolo",
        "Atalanta BC": "Atalanta",
        "US Lecce": "Lecce",
        "Udinese Calcio": "Udinese",
        "Torino FC": "Torino",
        "Parma Calcio 1913": "Parma",
        "AC Monza": "Monza",
        "ACF Fiorentina": "Fiorentina",
        "Bologna FC 1909": "Bologna",
        "Genoa CFC": "Genoa",
        "Venezia FC": "Venezia",
    },
    "ligue-1": {
        "AS Monaco FC": "Monaco",
        "Olympique Lyonnais": "Lyon",
        "Lille OSC": "Lille",
        "Stade Rennais FC 1901": "Rennes",
        "Paris Saint-Germain FC": "Paris Saint-Germain",
        "Angers SCO": "Angers",
        "RC Strasbourg Alsace": "Strasbourg",
        "Olympique de Marseille": "Marseille",
        "Racing Club de Lens": "Lens",
        "FC Lorient": "Lorient",
        "Le Mans FC": "Le Mans",
        "AJ Auxerre": "Auxerre",
        "Toulouse FC": "Toulouse",
        "Stade Brestois 29": "Brest",
        "OGC Nice": "Nice",
        "ES Troyes AC": "Troyes",
        "Le Havre AC": "Le Havre",
    },
    "championship": {
        "Birmingham City FC": "Birmingham City",
        "Blackburn Rovers FC": "Blackburn Rovers",
        "Bolton Wanderers FC": "Bolton Wanderers",
        "Bristol City FC": "Bristol City",
        "Burnley FC": "Burnley",
        "Cardiff City FC": "Cardiff City",
        "Charlton Athletic FC": "Charlton Athletic",
        "Derby County FC": "Derby County",
        "Lincoln City FC": "Lincoln City",
        "Middlesbrough FC": "Middlesbrough",
        "Millwall FC": "Millwall",
        "Norwich City FC": "Norwich City",
        "Portsmouth FC": "Portsmouth",
        "Preston North End FC": "Preston North End",
        "Queens Park Rangers FC": "Queens Park Rangers",
        "Sheffield United FC": "Sheffield United",
        "Southampton FC": "Southampton",
        "Stoke City FC": "Stoke City",
        "Swansea City AFC": "Swansea City",
        "Watford FC": "Watford",
        "West Bromwich Albion FC": "West Bromwich Albion",
        "West Ham United FC": "West Ham United",
        "Wolverhampton Wanderers FC": "Wolverhampton Wanderers",
        "Wrexham AFC": "Wrexham",
    },
    "primeira-liga": {
        "Académico de Viseu FC": "Académico de Viseu",
        "CD Nacional": "Nacional de Madeira",
        "CD Santa Clara": "Santa Clara",
        "CF Estrela da Amadora": "Estrela Amadora",
        "CS Marítimo": "Marítimo",
        "Casa Pia AC": "Casa Pia",
        "FC Alverca": "Alverca",
        "FC Arouca": "Arouca",
        "FC Famalicão": "Famalicao",
        "FC Porto": "Porto",
        "GD Estoril Praia": "Estoril Praia",
        "Gil Vicente FC": "Gil Vicente",
        "Moreirense FC": "Moreirense",
        "Rio Ave FC": "Rio Ave",
        "Sport Lisboa e Benfica": "Benfica",
        "Sporting Clube de Braga": "Braga",
        "Sporting Clube de Portugal": "Sporting CP",
        "Vitória Guimarães": "Vitória de Guimarães",
    },
    "eredivisie": {
        "AFC Ajax": "Ajax",
        "AZ": "AZ Alkmaar",
        "FC Groningen": "Groningen",
        "FC Twente '65": "Twente",
        "FC Utrecht": "Utrecht",
        "Feyenoord Rotterdam": "Feyenoord",
        "NEC": "NEC Nijmegen",
        "PSV": "PSV Eindhoven",
        "SBV Excelsior": "Excelsior",
        "SC Cambuur-Leeuwarden": "Cambuur",
        "SC Heerenveen": "Heerenveen",
        "Telstar 1963": "Telstar",
        "Willem II Tilburg": "Willem II",
    },
}


def _canonical_name(competition_slug: str, team_name: str) -> str:
    return _TEAM_NAME_ALIASES.get(competition_slug, {}).get(team_name, team_name)


def _to_openfootball_season(season: str) -> str:
    """Our internal "2026-2027" -> openfootball's "2026-27"."""
    start, end = season.split("-")
    return f"{start}-{end[-2:]}"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _stable_id(competition_slug: str, date: str, team1: str, team2: str) -> str:
    """openfootball gives no event id, so build a deterministic one from
    the fields that uniquely identify a fixture — stable across repeated
    fetches of the same file."""
    raw = f"{competition_slug}-{date}-{team1}-{team2}".lower()
    return f"openfootball-{_SLUG_RE.sub('-', raw).strip('-')}"


def _map_match(raw: dict, competition_slug: str) -> Match | None:
    date = raw.get("date")
    team1 = raw.get("team1")
    team2 = raw.get("team2")
    if not date or not team1 or not team2:
        return None
    team1 = _canonical_name(competition_slug, team1)
    team2 = _canonical_name(competition_slug, team2)

    time_part = raw.get("time") or "00:00"
    try:
        kickoff = datetime.fromisoformat(f"{date}T{time_part}").replace(tzinfo=timezone.utc)
    except ValueError:
        kickoff = None

    score = raw.get("score") or {}
    # Verified live: most matches give {"ht": [..], "ft": [home, away]},
    # but some (rescheduled fixtures, at least in the Premier League file)
    # give a bare [home, away] list directly as "score" instead — handle
    # both shapes rather than assuming the dict form everywhere.
    full_time = score.get("ft") if isinstance(score, dict) else score
    if full_time and len(full_time) == 2:
        home_score, away_score = full_time
        status = MatchStatus.FINISHED
    else:
        home_score = away_score = None
        status = MatchStatus.SCHEDULED

    return Match(
        id=_stable_id(competition_slug, date, team1, team2),
        sport="futbol",
        competition_slug=competition_slug,
        competition_name=COMPETITION_NAMES[competition_slug],
        status=status,
        kickoff=kickoff,
        home=team1,
        away=team2,
        # openfootball gives no team ids or crest artwork — never invent
        # them, leave honestly empty like any other source that lacks a
        # field (see Match's own docstring).
        home_id=None,
        away_id=None,
        home_crest=None,
        away_crest=None,
        home_score=home_score,
        away_score=away_score,
        summary=None,
        venue=None,
        source=SOURCE,
    )


_ROUND_NUMBER_RE = re.compile(r"(\d+)")


def _extract_round_number(raw_round: object) -> int | None:
    if not isinstance(raw_round, str):
        return None
    m = _ROUND_NUMBER_RE.search(raw_round)
    return int(m.group(1)) if m else None


def _estimate_current_round(raw_matches: list[dict], today: object) -> int | None:
    """Zero-network fallback for "which matchday is current": OpenFootball's
    own *schedule* (the `date` field) is reliable months in advance even
    though its *results* can be weeks stale — a competition's fixture
    list is published before the season and rarely changes. Picks the
    round number of whichever real match is dated closest to `today`."""
    best_round: int | None = None
    best_distance: int | None = None
    for raw in raw_matches:
        date_str = raw.get("date")
        round_number = _extract_round_number(raw.get("round"))
        if not date_str or round_number is None:
            continue
        try:
            match_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            continue
        distance = abs((match_date - today).days)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_round = round_number
    return best_round


class OpenFootballProvider:
    """Fallback-only source for the five domestic leagues it covers. See
    module docstring for why this is never treated as authoritative."""

    def __init__(self, cache: TTLCache | None = None) -> None:
        self.cache = cache or TTLCache()

    async def _fetch_raw(
        self, client: httpx.AsyncClient, competition_slug: str, season: str
    ) -> list[dict]:
        file_code = _FILES[competition_slug]
        of_season = _to_openfootball_season(season)
        cache_key = f"openfootball:raw:{competition_slug}:{of_season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        data = await fetch_json(client, f"{BASE_URL}/{of_season}/{file_code}.json")
        raw_matches = (data or {}).get("matches") or []
        # Static file on GitHub's CDN — updates at most every few days, so
        # an hour-long cache costs us nothing real and avoids needless
        # repeat fetches of a multi-hundred-KB file on every page view.
        self.cache.set(cache_key, raw_matches, ttl_seconds=3600 if raw_matches else 60)
        return raw_matches

    async def get_season(
        self, client: httpx.AsyncClient, competition_slug: str, season: str
    ) -> list[Match]:
        if competition_slug not in _FILES:
            return []

        raw_matches = await self._fetch_raw(client, competition_slug, season)
        return [m for raw in raw_matches if (m := _map_match(raw, competition_slug)) is not None]

    async def estimate_current_round(
        self, client: httpx.AsyncClient, competition_slug: str, season: str, today: object = None
    ) -> int | None:
        """See _estimate_current_round — reuses the same cached raw fetch
        as get_season(), so calling both costs at most one real request."""
        if competition_slug not in _FILES:
            return None
        today = today or datetime.now(timezone.utc).date()
        raw_matches = await self._fetch_raw(client, competition_slug, season)
        return _estimate_current_round(raw_matches, today)
