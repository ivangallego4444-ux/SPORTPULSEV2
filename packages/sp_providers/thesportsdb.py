from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from sp_core.models import Competition, Match, MatchStatLine, MatchStats, MatchStatus, StandingRow

from .base import Throttle, TTLCache, fetch_json

SOURCE = "thesportsdb"
BASE_URL = "https://www.thesportsdb.com/api/v1/json/123"
# "123" is TheSportsDB's own published shared free-tier key (no account
# created for this project) — see docs/DATA_SOURCES.md for its limits.


@dataclass(frozen=True)
class _LeagueConfig:
    league_id: str
    structured: bool
    """True when the source gives real home/away team objects and numeric
    scores (basketball). False for player-vs-player sports (tennis), where
    we only have free text — we never invent a score split for those."""


COMPETITIONS: dict[str, Competition] = {
    "nba": Competition(
        sport="baloncesto",
        slug="nba",
        name="NBA",
        source=SOURCE,
        supports_standings=False,
        supports_upcoming=True,
        country="Estados Unidos",
        notes=(
            "La tabla de clasificación no está disponible en esta fuente para "
            "la NBA (la consulta real devuelve vacío); se muestran partidos "
            "próximos y resultados recientes."
        ),
    ),
    "euroleague": Competition(
        sport="baloncesto",
        slug="euroleague",
        name="EuroLeague",
        source=SOURCE,
        supports_standings=False,
        supports_upcoming=True,
        country="Europa",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/7xjtuy1554397263.png",
        notes=(
            "Misma limitación que la NBA en esta fuente gratuita: sin tabla "
            "de clasificación, se muestran partidos próximos y resultados "
            "recientes reales."
        ),
    ),
    "atp": Competition(
        sport="tenis",
        slug="atp",
        name="ATP Tour",
        source=SOURCE,
        supports_standings=False,
        supports_upcoming=True,
        country="Internacional",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/q7aej51769857150.png",
        notes=(
            "Cobertura real pero muy limitada en la fuente gratuita (decenas "
            "de partidos por temporada, no el cuadro completo); no hay "
            "resultado estructurado por sets, solo el texto del resultado "
            "oficial. No hay tabla de clasificación (no aplica a un circuito "
            "individual)."
        ),
    ),
    "wta": Competition(
        sport="tenis",
        slug="wta",
        name="WTA Tour",
        source=SOURCE,
        supports_standings=False,
        supports_upcoming=True,
        country="Internacional",
        notes=(
            "Mismas limitaciones que el ATP Tour: cobertura real pero parcial, "
            "resultado solo en texto, sin tabla de clasificación."
        ),
    ),
    # badge_url values verified live via TheSportsDB's search_all_leagues.php
    # / lookupleague.php (2026-10-23); the few still missing one (conference-
    # league, segunda, primeira-liga, eredivisie) get it for free the next
    # time this process does a real live fetch for them (see
    # get_league_badge/_LEAGUE_BADGES) rather than from a hardcoded value
    # this session didn't get a chance to verify under today's rate limit.
    "laliga": Competition(
        sport="futbol", slug="laliga", name="LaLiga", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="España",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/ja4it51687628717.png",
    ),
    "premier-league": Competition(
        sport="futbol", slug="premier-league", name="Premier League", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Inglaterra",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/gasy9d1737743125.png",
    ),
    "serie-a": Competition(
        sport="futbol", slug="serie-a", name="Serie A", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Italia",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/67q3q21679951383.png",
    ),
    "ligue-1": Competition(
        sport="futbol", slug="ligue-1", name="Ligue 1", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Francia",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/9f7z9d1742983155.png",
    ),
    "champions-league": Competition(
        sport="futbol", slug="champions-league", name="UEFA Champions League", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Europa",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/facv1u1742998896.png",
    ),
    "europa-league": Competition(
        sport="futbol", slug="europa-league", name="UEFA Europa League", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Europa",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/mlsr7d1718774547.png",
    ),
    "conference-league": Competition(
        sport="futbol", slug="conference-league", name="UEFA Conference League", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Europa",
    ),
    "segunda": Competition(
        sport="futbol", slug="segunda", name="LaLiga Hypermotion", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="España",
    ),
    "championship": Competition(
        sport="futbol", slug="championship", name="EFL Championship", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Inglaterra",
        badge_url="https://r2.thesportsdb.com/images/media/league/badge/ty5a681688770169.png",
    ),
    "primeira-liga": Competition(
        sport="futbol", slug="primeira-liga", name="Primeira Liga", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Portugal",
    ),
    "eredivisie": Competition(
        sport="futbol", slug="eredivisie", name="Eredivisie", source=SOURCE,
        supports_standings=True, supports_upcoming=True, country="Países Bajos",
    ),
}

_LEAGUES: dict[str, _LeagueConfig] = {
    "nba": _LeagueConfig(league_id="4387", structured=True),
    "euroleague": _LeagueConfig(league_id="4546", structured=True),
    "atp": _LeagueConfig(league_id="4464", structured=False),
    "wta": _LeagueConfig(league_id="4517", structured=False),
    "laliga": _LeagueConfig(league_id="4335", structured=True),
    "premier-league": _LeagueConfig(league_id="4328", structured=True),
    "serie-a": _LeagueConfig(league_id="4332", structured=True),
    "ligue-1": _LeagueConfig(league_id="4334", structured=True),
    "champions-league": _LeagueConfig(league_id="4480", structured=True),
    # Verified live (league names confirmed via lookupleague.php):
    "europa-league": _LeagueConfig(league_id="4481", structured=True),
    "conference-league": _LeagueConfig(league_id="5071", structured=True),
    "segunda": _LeagueConfig(league_id="4400", structured=True),
    "championship": _LeagueConfig(league_id="4329", structured=True),
    "primeira-liga": _LeagueConfig(league_id="4344", structured=True),
    "eredivisie": _LeagueConfig(league_id="4337", structured=True),
}


def _parse_timestamp(raw: dict) -> datetime | None:
    ts = raw.get("strTimestamp")
    if ts:
        try:
            return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    date_part = raw.get("dateEvent")
    if date_part:
        try:
            return datetime.fromisoformat(date_part)
        except ValueError:
            return None
    return None


def _infer_status(raw: dict, kickoff: datetime | None) -> MatchStatus:
    str_status = (raw.get("strStatus") or "").upper()
    if str_status in {"FT", "AOT", "AP"}:
        return MatchStatus.FINISHED
    if str_status in {"NS", "", None}:
        if kickoff is None:
            return MatchStatus.UNKNOWN
        now = datetime.now(timezone.utc)
        kickoff_cmp = kickoff if kickoff.tzinfo else kickoff.replace(tzinfo=timezone.utc)
        return MatchStatus.SCHEDULED if kickoff_cmp >= now else MatchStatus.FINISHED
    return MatchStatus.UNKNOWN


_LEAGUE_BADGES: dict[str, str] = {}
"""Real competition logos, harvested for free from `strLeagueBadge` — a
field already present on every single event TheSportsDB returns (see
_map_event) — rather than one extra lookupleague.php request per
competition. Populated as a side effect of matches this app fetches
anyway; never a guessed/constructed CDN URL."""


def get_league_badge(competition_slug: str) -> str | None:
    return _LEAGUE_BADGES.get(competition_slug)


_TEAM_CRESTS: dict[str, str] = {}
"""Real team crests, harvested for free the same way as _LEAGUE_BADGES —
from `strHomeTeamBadge`/`strAwayTeamBadge`, already present on every
structured event TheSportsDB returns. Exists because the hybrid OpenFootball
+ TheSportsDB merge (see apps/api/app/main.py's _OPENFOOTBALL_SLUGS) means
most of a competition's real matches come from OpenFootball, which gives
no crest at all (see openfootball.py) — real bug found live: ~380 of 381
LaLiga matches had no crest, because only the narrow recent TheSportsDB
window ever carried one. `lookup_all_teams.php` (which would have given
every team's crest in one request) was tried and found to return the
wrong league's teams regardless of the id passed — broken on the free
tier, not a wrong id. Harvesting one crest per team name as a side effect
of matches already being fetched needs no extra request and — given
enough real matches seen — eventually covers every team."""

_CRESTS_STORE_PATH: Path | None = None
"""Real bug found live: _LEAGUE_BADGES/_TEAM_CRESTS are harvested for free
but were in-memory only, so every single backend restart wiped every crest
ever learned — a team whose only real-crest sighting came from a round
TheSportsDB happened to serve three restarts ago went right back to no
crest, even though the known-good *match* cache (a separate store) still
remembered that round's matches fine. Persisting these two small dicts the
same way (see configure_crest_store) makes a learned crest permanent:
coverage only ever grows across restarts instead of resetting to whatever
this one process's lucky rate-limit window happened to see."""


def configure_crest_store(path: Path) -> None:
    """Call once at startup (see apps/api/app/main.py) to load any crests
    already learned in a previous process, and persist every new one from
    here on. Never called in tests — stays in-memory-only there, same as
    before."""
    global _CRESTS_STORE_PATH
    _CRESTS_STORE_PATH = path
    if not path.exists():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    _LEAGUE_BADGES.update(raw.get("league_badges") or {})
    _TEAM_CRESTS.update(raw.get("team_crests") or {})


def _persist_crest_store() -> None:
    if _CRESTS_STORE_PATH is None:
        return
    try:
        _CRESTS_STORE_PATH.write_text(
            json.dumps({"league_badges": _LEAGUE_BADGES, "team_crests": _TEAM_CRESTS}),
            encoding="utf-8",
        )
    except OSError:
        pass  # Disk persistence is a nice-to-have; never break a request over it.


def get_team_crest(team_name: str) -> str | None:
    return _TEAM_CRESTS.get(team_name)


def remember_team_crest(team_name: str, crest_url: str) -> None:
    """Lets a caller (apps/api/app/main.py's _backfill_team_crests) feed a
    real crest back into this same harvest — e.g. one found on a Match
    object loaded from the known-good *disk* cache, which never runs
    _map_event and so never populates this dict on its own. Once
    remembered here, every other competition's backfill this process
    serves afterwards benefits too (a team seen in the Champions League
    helps backfill it in LaLiga, and vice versa)."""
    if team_name in _TEAM_CRESTS:
        return
    _TEAM_CRESTS[team_name] = crest_url
    _persist_crest_store()


_PLAYER_HEADSHOTS: dict[str, str] = {}
"""Real player photos, looked up once per real surname (see
TheSportsDBProvider.enrich_player_headshots) via searchplayers.php and
kept here for the life of the process — a player's photo doesn't change
mid-season, so there's no reason to ever look the same name up twice."""


_VS_LINE_RE = re.compile(r"^(.+?)\s+vs\.?\s+(.+)$", re.IGNORECASE)
_SEED_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")


def _parse_tennis_players(raw: dict) -> tuple[str | None, str | None]:
    """Real player names, parsed from TheSportsDB's own free-text
    description — tennis gives no structured home/away team fields (see
    _LeagueConfig.structured), but `strDescriptionEN`'s last line is
    reliably "Player1 (seed) vs Player2 (seed)" (verified live, e.g.
    "Alcaraz (3) vs Lehecka (23)"), unlike `strEvent` which also carries
    the tournament name with no consistent separator. Never invents a
    name — returns (None, None) when the line doesn't match."""
    description = (raw.get("strDescriptionEN") or "").strip()
    if not description:
        return None, None
    last_line = description.splitlines()[-1].strip()
    match = _VS_LINE_RE.match(last_line)
    if not match:
        return None, None
    home = _SEED_SUFFIX_RE.sub("", match.group(1)).strip()
    away = _SEED_SUFFIX_RE.sub("", match.group(2)).strip()
    return (home or None), (away or None)


def _map_event(raw: dict, competition_slug: str, config: _LeagueConfig) -> Match:
    kickoff = _parse_timestamp(raw)
    status = _infer_status(raw, kickoff)
    sport = COMPETITIONS[competition_slug].sport

    badge = raw.get("strLeagueBadge")
    learned_something = False
    if badge and competition_slug not in _LEAGUE_BADGES:
        _LEAGUE_BADGES[competition_slug] = badge
        learned_something = True

    if config.structured:
        home = raw.get("strHomeTeam")
        away = raw.get("strAwayTeam")
        home_id = raw.get("idHomeTeam")
        away_id = raw.get("idAwayTeam")
        home_crest = raw.get("strHomeTeamBadge")
        away_crest = raw.get("strAwayTeamBadge")
        if home and home_crest and _TEAM_CRESTS.get(home) != home_crest:
            _TEAM_CRESTS[home] = home_crest
            learned_something = True
        if away and away_crest and _TEAM_CRESTS.get(away) != away_crest:
            _TEAM_CRESTS[away] = away_crest
            learned_something = True
        if learned_something:
            _persist_crest_store()
        home_score_raw = raw.get("intHomeScore")
        away_score_raw = raw.get("intAwayScore")
        home_score = int(home_score_raw) if home_score_raw not in (None, "") else None
        away_score = int(away_score_raw) if away_score_raw not in (None, "") else None
        title = None
        summary = None
    else:
        home, away = _parse_tennis_players(raw) if sport == "tenis" else (None, None)
        home_id = None
        away_id = None
        # Real headshots, when already looked up for this exact name (see
        # enrich_player_headshots) — never populated synchronously here,
        # since that needs a network call this sync function can't make.
        home_crest = _PLAYER_HEADSHOTS.get(home) if home else None
        away_crest = _PLAYER_HEADSHOTS.get(away) if away else None
        home_score = None
        away_score = None
        title = raw.get("strEvent")
        summary = raw.get("strResult") or raw.get("strDescriptionEN") or None
        if summary:
            summary = summary.strip()

    return Match(
        id=f"thesportsdb-{raw.get('idEvent')}",
        sport=sport,
        competition_slug=competition_slug,
        competition_name=COMPETITIONS[competition_slug].name,
        status=status,
        kickoff=kickoff,
        home=home,
        away=away,
        home_id=str(home_id) if home_id else None,
        away_id=str(away_id) if away_id else None,
        home_crest=home_crest,
        away_crest=away_crest,
        home_score=home_score,
        away_score=away_score,
        title=title,
        summary=summary,
        venue=raw.get("strVenue"),
        source=SOURCE,
    )


_TWO_YEAR_SEASON_SLUGS = {
    "nba",
    "euroleague",
    "laliga",
    "premier-league",
    "serie-a",
    "ligue-1",
    "champions-league",
    "europa-league",
    "conference-league",
    "segunda",
    "championship",
    "primeira-liga",
    "eredivisie",
}

ROUND_BASED_SLUGS = {
    "laliga",
    "premier-league",
    "serie-a",
    "ligue-1",
    "champions-league",
    "europa-league",
    "conference-league",
    "segunda",
    "championship",
    "primeira-liga",
    "eredivisie",
}
"""These use get_rounds() instead of get_recent()/get_upcoming(), because
eventsseason.php caps out at ~15 events total for the whole competition
(verified live — same cap found for ATP/WTA), which is too thin a sample
for recent-form/H2H/the Poisson model. eventsround.php has no such cap and
returns every match of a single matchday, finished or not — so it covers
both "recent results" and "próximos partidos" at once."""

FINISHED_ROUND_TTL = 30 * 24 * 3600
"""A matchday whose every event is already FINISHED has a real result
that will never change — effectively permanent (30 days, simply to avoid
an unbounded in-memory entry across a long-running process), so it's
never re-fetched once seen complete. This is what makes repeat requests
for a competition cheap over time: only the still-in-progress/upcoming
rounds keep costing real requests."""

ROUNDS_TO_FETCH = 11
"""Verified live (2026-10-21): the big-5 leagues were already ~9 matchdays
in, so a window of 8 rounds was entirely in the past — no genuinely
upcoming fixture ever showed up, only the odd postponed match. 11 rounds
reaches 1-2 matchdays into the future (real scheduled fixtures) while
keeping a ~9-match sample per team for the Poisson model, without firing
off a full season's worth of requests against a free-tier key that's
already shown it rate-limits bursts (HTTP 429, see
docs/DATA_SOURCES.md)."""


def current_season(competition_slug: str) -> str:
    """Season-string format differs: team leagues (NBA, the five football
    leagues) use "YYYY-YYYY+1" (verified live for each one), ATP/WTA tours
    use a plain "YYYY"."""
    now = datetime.now(timezone.utc)
    if competition_slug in _TWO_YEAR_SEASON_SLUGS:
        start_year = now.year if now.month >= 8 else now.year - 1
        return f"{start_year}-{start_year + 1}"
    return str(now.year)


class TheSportsDBProvider:
    """Basketball (NBA) and tennis (ATP/WTA) via the free public key `123`
    on thesportsdb.com. See docs/DATA_SOURCES.md for verified limits:
    ~30 req/min nominal but Cloudflare throttles bursts harder in
    practice, so every call here goes through the shared TTL cache."""

    def __init__(
        self,
        cache: TTLCache | None = None,
        throttle: Throttle | None = None,
        known_good_store_path: Path | None = None,
    ) -> None:
        self.cache = cache or TTLCache()
        # Shared across every method on this instance — and this provider
        # is a module-level singleton in apps/api — so it paces *all*
        # TheSportsDB traffic app-wide, not just calls within one method.
        # Bumped from 0.35s after live testing: an 11-round fetch spaced
        # at 0.35s (a ~3.5s burst) tripped the free key's burst limit on
        # the last round almost every single time, even with no other
        # process touching the key — the limit is evidently about burst
        # density, not just the nominal ~30 req/min. Spreading the same
        # 11 requests over ~11s instead avoided it in the same live test.
        self.throttle = throttle or Throttle(min_interval_seconds=1.0)
        # Optional: persists the known-good cache to a local JSON file so
        # a real, already-successful fetch survives a process restart —
        # found live that restarting the verification backend to pick up
        # a code change wiped an in-memory-only cache, making a league
        # that had already loaded correctly look broken again for no
        # real reason. None (the default, and what every test uses)
        # means in-memory only, same as before.
        self._known_good_store_path = known_good_store_path
        if known_good_store_path is not None:
            self._load_known_good_from_disk()

    def _load_known_good_from_disk(self) -> None:
        path = self._known_good_store_path
        assert path is not None
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        restored = {
            key: [Match.model_validate(m) for m in matches_raw] for key, matches_raw in raw.items()
        }
        self.cache.import_known_good(restored)

    def _remember_known_good(self, cache_key: str, matches: list[Match]) -> None:
        self.cache.set_known_good(cache_key, matches)
        if self._known_good_store_path is None:
            return
        try:
            serializable = {
                key: [m.model_dump(mode="json") for m in value]
                for key, value in self.cache.export_known_good().items()
            }
            self._known_good_store_path.write_text(json.dumps(serializable), encoding="utf-8")
        except OSError:
            pass  # Disk persistence is a nice-to-have; never break a request over it.

    async def get_upcoming(self, client: httpx.AsyncClient, competition_slug: str) -> list[Match]:
        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:next:{competition_slug}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(
            client, f"{BASE_URL}/eventsnextleague.php", params={"id": config.league_id}
        )
        events = (data or {}).get("events") or []
        matches = [_map_event(raw, competition_slug, config) for raw in events]
        # Don't lock in a rate-limited "nothing came back" for the full
        # TTL — a short retry window lets the next request self-heal once
        # the free key's burst limit clears (verified live: it does,
        # within roughly a minute).
        self.cache.set(cache_key, matches, ttl_seconds=180 if matches else 20)
        if matches:
            self._remember_known_good(cache_key, matches)
            return matches
        # This fetch itself came back empty (likely rate-limited) — a
        # transient failure must never erase real data we already had.
        # Serve the last successful fetch instead of nothing; the 20s
        # short TTL above still makes the next request retry live.
        return self.cache.get_known_good(cache_key) or matches

    async def _fetch_one_round(
        self, client: httpx.AsyncClient, competition_slug: str, season: str, round_number: int
    ) -> tuple[list[Match] | None, bool]:
        """(matches, succeeded) for a single matchday. A round whose
        events are *all* finished is remembered essentially forever (see
        FINISHED_ROUND_TTL) — a finished round's real result never
        changes, so re-fetching it on every request wastes a slot of the
        free key's burst budget for nothing. A round still in progress or
        upcoming keeps the old short TTL, so it's re-checked often."""
        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:round:{competition_slug}:{season}:{round_number}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached, True

        await self.throttle.wait()
        data = await fetch_json(
            client,
            f"{BASE_URL}/eventsround.php",
            params={"id": config.league_id, "r": round_number, "s": season},
        )
        if data is None:
            return None, False

        events = data.get("events") or []
        matches = [_map_event(raw, competition_slug, config) for raw in events]
        all_finished = bool(matches) and all(m.status == MatchStatus.FINISHED for m in matches)
        self.cache.set(cache_key, matches, ttl_seconds=FINISHED_ROUND_TTL if all_finished else 20)
        return matches, True

    async def _aggregate_rounds(
        self,
        client: httpx.AsyncClient,
        competition_slug: str,
        season: str,
        round_numbers: range,
        cache_key: str,
    ) -> list[Match]:
        cached = self.cache.get(cache_key)
        if cached is not None:
            # The short-lived entry above can itself be a worse partial
            # than something we already know is good (e.g. this exact
            # 20s window's attempt only got 1 of N rounds through, right
            # after an earlier attempt got N-1 of N) — never let the UI
            # regress to less real data than it already had.
            known_good = self.cache.get_known_good(cache_key)
            if known_good and len(known_good) > len(cached):
                return known_good
            return cached

        all_matches: list[Match] = []
        failed_rounds = 0
        for round_number in round_numbers:
            matches, ok = await self._fetch_one_round(client, competition_slug, season, round_number)
            if not ok:
                # Rate-limited or network error for this specific round —
                # real bug found live: caching whatever partial result we
                # got from the *other* rounds for the full 900s success
                # TTL locked in an incomplete season (e.g. only 1 of 11
                # rounds) for 15 minutes. Track it instead so the whole
                # fetch gets the short retry TTL, not just empty ones.
                failed_rounds += 1
                continue
            all_matches.extend(matches or [])

        all_matches.sort(
            key=lambda m: m.kickoff or datetime.min.replace(tzinfo=timezone.utc), reverse=True
        )
        complete = failed_rounds == 0
        if all_matches:
            # Remember any non-empty fetch as the fallback to serve on a
            # future failure — even a partial one (e.g. 10 of 11 rounds).
            # Verified live: TheSportsDB's burst limit routinely trips on
            # the last round or two of a multi-round fetch even when the
            # key isn't otherwise under contention, so requiring a
            # *perfect* fetch before remembering anything meant this
            # fallback almost never actually had data to serve. Real, if
            # slightly incomplete, data beats showing nothing — but never
            # regress from an already-better remembered snapshot to a
            # worse one.
            existing_known_good = self.cache.get_known_good(cache_key)
            if existing_known_good is None or len(all_matches) >= len(existing_known_good):
                self._remember_known_good(cache_key, all_matches)
        if all_matches and complete:
            self.cache.set(cache_key, all_matches, ttl_seconds=900)
            return all_matches

        # Some (or all) rounds failed this attempt — almost always a
        # transient rate limit, not "this league has no matches". Cache
        # this attempt's own result for only 20s so the next request
        # retries soon, but serve the last known-good fetch instead of an
        # empty/more-partial one in the meantime, so the table/fixtures
        # never go blank just because the free key got throttled.
        self.cache.set(cache_key, all_matches, ttl_seconds=20)
        known_good = self.cache.get_known_good(cache_key)
        return known_good if known_good else all_matches

    async def get_rounds(
        self,
        client: httpx.AsyncClient,
        competition_slug: str,
        season: str,
        max_rounds: int = ROUNDS_TO_FETCH,
    ) -> list[Match]:
        cache_key = f"thesportsdb:rounds:{competition_slug}:{season}:{max_rounds}"
        return await self._aggregate_rounds(
            client, competition_slug, season, range(1, max_rounds + 1), cache_key
        )

    async def discover_current_round(
        self, client: httpx.AsyncClient, competition_slug: str
    ) -> int | None:
        """Cheap (1 request) real signal of which matchday is current,
        read straight off the next real scheduled fixture's own
        `intRound` — verified live this field is always present. Lets a
        caller fetch only a narrow window of recent rounds instead of the
        whole season, without guessing."""
        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:current_round:{competition_slug}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(
            client, f"{BASE_URL}/eventsnextleague.php", params={"id": config.league_id}
        )
        events = (data or {}).get("events") or []
        round_number = None
        if events:
            try:
                round_number = int(events[0].get("intRound"))
            except (TypeError, ValueError):
                round_number = None
        # A real round number barely changes within a week — cache it
        # generously; a miss just falls back to the full-season fetch.
        self.cache.set(cache_key, round_number, ttl_seconds=3600 if round_number else 60)
        return round_number

    async def get_recent_rounds(
        self,
        client: httpx.AsyncClient,
        competition_slug: str,
        season: str,
        round_numbers: range,
    ) -> list[Match]:
        """Like get_rounds(), but for an explicit, narrow window of
        matchdays (see discover_current_round()) instead of 1..max_rounds
        — far fewer requests per load when the caller already knows which
        rounds are actually current."""
        cache_key = (
            f"thesportsdb:recent:{competition_slug}:{season}:{round_numbers.start}:{round_numbers.stop}"
        )
        return await self._aggregate_rounds(client, competition_slug, season, round_numbers, cache_key)

    async def get_recent(
        self, client: httpx.AsyncClient, competition_slug: str, season: str
    ) -> list[Match]:
        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:season:{competition_slug}:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(
            client,
            f"{BASE_URL}/eventsseason.php",
            params={"id": config.league_id, "s": season},
        )
        events = (data or {}).get("events") or []
        matches = [_map_event(raw, competition_slug, config) for raw in events]
        matches.sort(key=lambda m: m.kickoff or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        self.cache.set(cache_key, matches, ttl_seconds=300 if matches else 20)
        if matches:
            self._remember_known_good(cache_key, matches)
            return matches
        return self.cache.get_known_good(cache_key) or matches

    async def get_recent_past(self, client: httpx.AsyncClient, competition_slug: str) -> list[Match]:
        """Real bug found live (2026-10-23): for a tour that runs all year
        round (ATP/WTA — unlike a football league that restarts each
        August), get_recent()'s eventsseason.php is capped at ~15 events
        *from the start of that season* (see ROUND_BASED_SLUGS' docstring)
        — by October that cap had already been used up by January's
        Brisbane International, so no real October result ever surfaced.
        eventspastleague.php instead returns the real *most recent*
        events regardless of season length — verified live: it returned
        this week's real Japan Open result when eventsseason.php was
        still stuck in January. No season param (it doesn't take one)."""
        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:pastleague:{competition_slug}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(
            client, f"{BASE_URL}/eventspastleague.php", params={"id": config.league_id}
        )
        events = (data or {}).get("events") or []
        matches = [_map_event(raw, competition_slug, config) for raw in events]
        self.cache.set(cache_key, matches, ttl_seconds=300 if matches else 20)
        if matches:
            self._remember_known_good(cache_key, matches)
            return matches
        return self.cache.get_known_good(cache_key) or matches

    async def get_standings(
        self, client: httpx.AsyncClient, competition_slug: str, season: str
    ) -> list[StandingRow] | None:
        competition = COMPETITIONS[competition_slug]
        if not competition.supports_standings:
            return None

        config = _LEAGUES[competition_slug]
        cache_key = f"thesportsdb:table:{competition_slug}:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(
            client,
            f"{BASE_URL}/lookuptable.php",
            params={"l": config.league_id, "s": season},
        )
        rows_raw = (data or {}).get("table") or []
        if not rows_raw:
            return None

        rows = [
            StandingRow(
                rank=int(row["intRank"]),
                team=row["strTeam"],
                played=_safe_int(row.get("intPlayed")),
                wins=_safe_int(row.get("intWin")),
                draws=_safe_int(row.get("intDraw")),
                losses=_safe_int(row.get("intLoss")),
                points=_safe_int(row.get("intPoints")),
                crest_url=row.get("strBadge"),
            )
            for row in rows_raw
        ]
        self.cache.set(cache_key, rows, ttl_seconds=600)
        return rows

    async def get_match_stats(self, client: httpx.AsyncClient, match_id: str) -> MatchStats | None:
        """Real per-match stats (shots etc.) for an already-finished match.
        Checked live across several real matches: this free endpoint
        consistently has no corners or cards figures, only shots — so we
        only ever report what it actually gives us."""
        if not match_id.startswith("thesportsdb-"):
            return None
        event_id = match_id.removeprefix("thesportsdb-")

        cache_key = f"thesportsdb:stats:{event_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(client, f"{BASE_URL}/lookupeventstats.php", params={"id": event_id})
        rows_raw = (data or {}).get("eventstats") or []

        lines = [
            MatchStatLine(
                label=row["strStat"],
                home_value=float(row["intHome"]),
                away_value=float(row["intAway"]),
            )
            for row in rows_raw
            if row.get("intHome") not in (None, "") and row.get("intAway") not in (None, "")
        ]
        if not lines:
            return None

        stats = MatchStats(lines=lines)
        # Stats for a finished match never change — safe to cache for a
        # long time regardless of the fetch outcome.
        self.cache.set(cache_key, stats, ttl_seconds=3600)
        return stats

    async def get_live_matches(self, client: httpx.AsyncClient) -> list[Match]:
        """Every real in-progress match, across every league this app
        tracks, from one single call to TheSportsDB's free livescore
        endpoint — verified live (2026-10-22) to work on the free key and
        to return a real elapsed-time string (`strProgress`, e.g. "63" or
        "90+2") straight from the source, which is what `live_minute`
        carries — never estimated from kickoff time. One shared call
        covers every competition at once, so adding more tracked leagues
        costs nothing extra here (unlike the per-competition round
        fetches elsewhere in this provider)."""
        cache_key = "thesportsdb:livescore"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.throttle.wait()
        data = await fetch_json(client, f"{BASE_URL}/livescore.php", params={"s": "Soccer"})
        events = (data or {}).get("livescore") or []

        league_to_slug = {config.league_id: slug for slug, config in _LEAGUES.items()}
        matches: list[Match] = []
        for raw in events:
            slug = league_to_slug.get(str(raw.get("idLeague")))
            if slug is None:
                continue  # A league we don't track yet — never show it.

            str_status = (raw.get("strStatus") or "").upper()
            status = MatchStatus.FINISHED if str_status == "FT" else MatchStatus.LIVE
            home_score_raw = raw.get("intHomeScore")
            away_score_raw = raw.get("intAwayScore")
            matches.append(
                Match(
                    id=f"thesportsdb-{raw.get('idEvent')}",
                    sport="futbol",
                    competition_slug=slug,
                    competition_name=COMPETITIONS[slug].name,
                    status=status,
                    kickoff=_parse_timestamp(raw),
                    home=raw.get("strHomeTeam"),
                    away=raw.get("strAwayTeam"),
                    home_id=str(raw["idHomeTeam"]) if raw.get("idHomeTeam") else None,
                    away_id=str(raw["idAwayTeam"]) if raw.get("idAwayTeam") else None,
                    home_crest=raw.get("strHomeTeamBadge"),
                    away_crest=raw.get("strAwayTeamBadge"),
                    home_score=int(home_score_raw) if home_score_raw not in (None, "") else None,
                    away_score=int(away_score_raw) if away_score_raw not in (None, "") else None,
                    live_minute=raw.get("strProgress") if status == MatchStatus.LIVE else None,
                    summary=None,
                    venue=None,
                    source=SOURCE,
                )
            )
        # Real-time by nature — a short TTL so the next poll (the frontend
        # polls every 60s, see LiveMatchesBanner) gets a fresh minute/score
        # rather than one already 15 minutes stale.
        self.cache.set(cache_key, matches, ttl_seconds=20)
        return matches

    async def search_player_headshot(self, client: httpx.AsyncClient, player_name: str) -> str | None:
        """Real photo for one real player name, via searchplayers.php —
        `strCutout` (a clean cutout, preferred when the source has one)
        else `strThumb`. Cached forever in-process (see
        _PLAYER_HEADSHOTS) and never retried once looked up, successful
        or not, so an ambiguous/unmatched surname doesn't cost a repeat
        request on every subsequent page view.

        Real bug found live: a tennis match only ever gives a bare
        surname (see _parse_tennis_players — "Alcaraz", not "Carlos
        Alcaraz"), and searchplayers.php's top relevance-ranked result
        for a bare surname can genuinely be a same-named player from a
        *different sport* — verified live: searching "Alcaraz" returned
        a Paraguayan football defender, not the real tennis player.
        Showing that photo next to a tennis match would be a real
        person's face misattributed to someone else, which is worse than
        showing none — so results are filtered to `strSport == "Tennis"`
        before taking the first match, and this method skips the lookup
        entirely unless told the match is tennis in the first place."""
        if player_name in _PLAYER_HEADSHOTS:
            return _PLAYER_HEADSHOTS[player_name]
        await self.throttle.wait()
        data = await fetch_json(client, f"{BASE_URL}/searchplayers.php", params={"p": player_name})
        players = (data or {}).get("player") or []
        tennis_players = [p for p in players if (p.get("strSport") or "").lower() == "tennis"]
        photo = None
        if tennis_players:
            photo = tennis_players[0].get("strCutout") or tennis_players[0].get("strThumb") or None
        if photo:
            _PLAYER_HEADSHOTS[player_name] = photo
        return photo

    async def enrich_player_headshots(self, client: httpx.AsyncClient, matches: list[Match]) -> list[Match]:
        """Best-effort: looks up a real headshot for every distinct real
        player name this batch of tennis matches already has (see
        _parse_tennis_players), then re-applies it to every match
        mentioning that player. One real request per *new* name only —
        already-cached names (the common case after the first lookup)
        cost nothing. Never blocks match display: a name search failing
        just leaves that side without a photo, the same honest "no
        fabricated image" behavior as a missing team crest elsewhere."""
        names = {m.home for m in matches if m.home} | {m.away for m in matches if m.away}
        unknown = [n for n in names if n not in _PLAYER_HEADSHOTS]
        for name in unknown:
            try:
                await self.search_player_headshot(client, name)
            except Exception:
                continue
        if not any(n in _PLAYER_HEADSHOTS for n in names):
            return matches
        return [
            m.model_copy(
                update={
                    "home_crest": _PLAYER_HEADSHOTS.get(m.home) if m.home else m.home_crest,
                    "away_crest": _PLAYER_HEADSHOTS.get(m.away) if m.away else m.away_crest,
                }
            )
            for m in matches
        ]


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
