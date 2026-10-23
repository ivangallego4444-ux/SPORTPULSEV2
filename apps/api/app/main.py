from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sp_core.models import (
    HomeHighlights,
    Match,
    MatchAnalysis,
    MatchStatus,
    StandingRow,
    TeamHistory,
    TeamSummary,
)
from sp_predict import audit_completeness, compute_table, head_to_head, predict_match, recent_form
from sp_predict.poisson import _collect_stats, _dynamic_season_ratings, _sos_corrections
from sp_providers.openfootball import OpenFootballProvider
from sp_providers.openligadb import OpenLigaDBProvider
from sp_providers.registry import ALL_COMPETITIONS, SPORTS, competitions_for_sport
from sp_providers.thesportsdb import ROUND_BASED_SLUGS, TheSportsDBProvider, current_season, get_league_badge

from . import teams as teams_module
from .highlights import build_home_highlights

SPORT_NAMES = {"futbol": "Fútbol", "baloncesto": "Baloncesto", "tenis": "Tenis"}

# Survives a backend restart: a league that already loaded successfully
# once should never look broken again just because the process restarted
# while TheSportsDB's shared free key happened to be rate-limited.
_KNOWN_GOOD_STORE_PATH = Path(__file__).resolve().parent.parent / ".cache_store.json"

openligadb_provider = OpenLigaDBProvider()
thesportsdb_provider = TheSportsDBProvider(known_good_store_path=_KNOWN_GOOD_STORE_PATH)
openfootball_provider = OpenFootballProvider()

_BACKGROUND_REFRESH_ENABLED = os.environ.get("SPORTPULSE_DISABLE_BACKGROUND_REFRESH") != "1"
FULL_REFRESH_INTERVAL_SECONDS = 15 * 60
"""Every competition's matches/standings, plus the cross-competition pool
and its SoS/Dynamic Season Rating indices, rebuilt and swapped into
`_snapshot` on this cadence — in the background, never inside a request.
15 minutes keeps the data fresh enough for anything that isn't literally
live (that's LIVE_REFRESH_INTERVAL_SECONDS below) without hammering the
free key every few seconds for twelve-plus competitions at once."""

LIVE_REFRESH_INTERVAL_SECONDS = 25
"""The livescore endpoint is one cheap shared call covering every
competition at once (see TheSportsDBProvider.get_live_matches) — frequent
enough that the 🔴 EN DIRECTO banner's minute/score never look stale,
without ever blocking a request on it."""


@dataclass
class _Snapshot:
    """In-memory, pre-merged view the real app serves every request from
    — see FULL_REFRESH_INTERVAL_SECONDS/LIVE_REFRESH_INTERVAL_SECONDS.
    Never mutated field-by-field from a request handler; only the two
    background loops (_refresh_all/_refresh_live) write to it. A field
    missing for a given slug/sport just means no background refresh has
    completed yet (e.g. the first moments after a fresh process start, or
    a test — see SPORTPULSE_DISABLE_BACKGROUND_REFRESH) — callers fall
    back to a real (slower) fetch in that case, never to fabricated data."""

    matches_by_slug: dict[str, list[Match]] = field(default_factory=dict)
    standings_by_slug: dict[str, list[StandingRow] | None] = field(default_factory=dict)
    live_matches: list[Match] = field(default_factory=list)
    pool_by_sport: dict[str, list[Match]] = field(default_factory=dict)
    season_ratings_by_sport: dict[str, dict[str, tuple[float, int]]] = field(default_factory=dict)
    sos_by_sport: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)
    full_refresh_count: int = 0
    live_refresh_count: int = 0
    last_full_refresh: float | None = None
    last_live_refresh: float | None = None


_snapshot = _Snapshot()


async def _refresh_all(client: httpx.AsyncClient) -> None:
    """One full pass over every competition — the slow background loop.
    Each competition is independent: one failing (rate-limited, etc.)
    never blocks or discards the others, and simply leaves that slug's
    previous snapshot entry in place until a later pass succeeds.

    Real bug found live: matches and standings used to be fetched inside
    one try/except, so a transient standings-only failure (e.g. a single
    bad response) discarded that pass's already-successfully-fetched
    matches too, not just the standings — a competition with perfectly
    real match data could still show empty until the next full refresh
    cycle happened to succeed at both. They're now independent: a matches
    success is kept even if standings fails right after, and vice versa."""
    for slug, competition in ALL_COMPETITIONS.items():
        try:
            matches = await _fetch_matches(client, slug)
            _snapshot.matches_by_slug[slug] = matches
        except Exception:
            matches = _snapshot.matches_by_slug.get(slug)
            if matches is None:
                continue
        try:
            _snapshot.standings_by_slug[slug] = await _compute_standings(
                client, slug, competition, matches=matches
            )
        except Exception:
            pass

    for sport in SPORTS:
        pool: list[Match] = []
        for competition in competitions_for_sport(sport):
            pool.extend(_snapshot.matches_by_slug.get(competition.slug, []))
        _snapshot.pool_by_sport[sport] = pool
        if sport == "futbol" and pool:
            # Precomputed here (see poisson.py's predict_match optional
            # season_ratings/sos_corrections params) so a real user's
            # /analysis click never re-walks the whole cross-competition
            # pool itself — only the one match's own Poisson grid runs at
            # request time.
            pool_records, _, _, _ = _collect_stats(pool)
            _snapshot.season_ratings_by_sport[sport] = _dynamic_season_ratings(pool)
            _snapshot.sos_by_sport[sport] = _sos_corrections(pool_records, pool)

    _snapshot.full_refresh_count += 1
    _snapshot.last_full_refresh = time.monotonic()


async def _refresh_live(client: httpx.AsyncClient) -> None:
    """The fast background loop: just the one cheap livescore call,
    overlaid into whatever matches the slow loop already has cached for
    each affected competition (same identity-merge idea as
    _overlay_live_matches, applied here instead of per-request)."""
    try:
        live = await thesportsdb_provider.get_live_matches(client)
    except Exception:
        return

    by_slug: dict[str, list[Match]] = {}
    for m in live:
        by_slug.setdefault(m.competition_slug, []).append(m)
    for slug, live_for_slug in by_slug.items():
        existing = _snapshot.matches_by_slug.get(slug)
        if existing is None:
            continue
        by_id = {m.id: m for m in existing}
        for m in live_for_slug:
            by_id[m.id] = m
        _snapshot.matches_by_slug[slug] = list(by_id.values())

    _snapshot.live_matches = [m for m in live if m.status == MatchStatus.LIVE]
    _snapshot.live_refresh_count += 1
    _snapshot.last_live_refresh = time.monotonic()


async def _background_full_refresh_loop(client: httpx.AsyncClient) -> None:
    while True:
        await asyncio.sleep(FULL_REFRESH_INTERVAL_SECONDS)
        await _refresh_all(client)


async def _background_live_refresh_loop(client: httpx.AsyncClient) -> None:
    while True:
        await asyncio.sleep(LIVE_REFRESH_INTERVAL_SECONDS)
        await _refresh_live(client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        tasks: list[asyncio.Task] = []
        if _BACKGROUND_REFRESH_ENABLED:
            # One synchronous warm-up before the app starts accepting
            # traffic — a bounded, one-time startup cost (same as any
            # real app's cache warm), never a per-request one. Every
            # request from here on reads the snapshot these loops keep
            # fresh; see _snapshot_matches/_snapshot_standings.
            await _refresh_all(client)
            await _refresh_live(client)
            tasks = [
                asyncio.create_task(_background_full_refresh_loop(client)),
                asyncio.create_task(_background_live_refresh_loop(client)),
            ]
        yield
        for task in tasks:
            task.cancel()


async def _snapshot_matches(client: httpx.AsyncClient, slug: str) -> list[Match]:
    """Zero-blocking read path for a request handler: the background
    loops keep `_snapshot` warm, so this is a dict lookup in the common
    case. Falls back to a real (slower) fetch only when nothing has been
    cached for this slug yet — right after a fresh process start before
    the first background pass completes, or when the background loops
    are disabled entirely (tests — see SPORTPULSE_DISABLE_BACKGROUND_REFRESH)."""
    cached = _snapshot.matches_by_slug.get(slug)
    if cached is not None:
        return cached
    matches = await _fetch_matches(client, slug)
    _snapshot.matches_by_slug[slug] = matches
    return matches


async def _snapshot_standings(client: httpx.AsyncClient, slug: str, competition):
    if slug in _snapshot.standings_by_slug:
        return _snapshot.standings_by_slug[slug]
    standings = await _compute_standings(client, slug, competition, matches=None)
    _snapshot.standings_by_slug[slug] = standings
    return standings


async def _snapshot_pool(client: httpx.AsyncClient, sport: str, current_slug: str) -> list[Match]:
    pool = _snapshot.pool_by_sport.get(sport)
    if pool is not None:
        return pool
    # Cold start / background loops disabled: same real-data pooling as
    # before the snapshot existed, just computed on demand this once.
    matches = await _snapshot_matches(client, current_slug)
    sibling_pool = await _cross_competition_pool(client, current_slug)
    return matches + sibling_pool


app = FastAPI(title="SportPulse API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3120",
        "http://127.0.0.1:3120",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _filter_uefa_league_phase(matches: list[Match], slug: str) -> list[Match]:
    """TheSportsDB numbers rounds sequentially across the whole
    competition, qualifying included — verified live: round-based
    fetching for champions-league pulled in 80 distinct teams across
    July-August (tiny qualifying-round clubs like "Vardar", "Sabah Baku")
    mixed with the real 36-team league phase. Mixing those into one
    "league average" would badly skew both the table and the Poisson
    model. The real league-phase matches land cleanly from September
    onward — confirmed against the actual counts (18 matches × 8
    matchdays = 144 for champions-league/europa-league, 18 × 6 = 108 for
    conference-league, exactly what filtering to September+ returns).
    Same qualifying-rounds pollution exists for all 3 UEFA club
    competitions, so this one filter now covers all of them."""
    season = current_season(slug)
    start_year = int(season.split("-")[0])
    phase_start = datetime(start_year, 9, 1, tzinfo=timezone.utc)

    return [m for m in matches if (k := _kickoff_utc(m)) is not None and k >= phase_start]


def _kickoff_utc(m: Match) -> datetime | None:
    if m.kickoff is None:
        return None
    return m.kickoff if m.kickoff.tzinfo else m.kickoff.replace(tzinfo=timezone.utc)


UEFA_LEAGUE_ROUNDS = {
    "champions-league": 8,
    "europa-league": 8,
    "conference-league": 6,
}
"""Each UEFA club competition's league phase has a fixed number of
matchdays — verified live per competition (champions-league/europa-league:
144 matches = 36 teams × 8 ÷ 2; conference-league: 108 matches = 36 teams ×
6 ÷ 2, confirmed by round 6 having exactly 18 real events on a single real
date). _filter_uefa_league_phase's date cutoff, not this round count, is
what actually isolates the real league-phase matches from any qualifying
rounds mixed into the same numbering — verified live (2026-10-23) that
round 1 here returns ~50 events spanning several July dates (qualifying,
correctly excluded by the date filter) alongside round 6's one real
September+ matchday. Keep this number STABLE: TheSportsDB round fetches
are cached per (slug, season, this exact number) — see
_fetch_one_round — so changing it orphans whatever's already been
painstakingly accumulated under the old key instead of building on it."""

UEFA_LEAGUE_PHASE_MATCHES = {
    "champions-league": 144,  # 36 teams × 8 matchdays ÷ 2
    "europa-league": 144,
    "conference-league": 108,  # 36 teams × 6 matchdays ÷ 2
}
"""Real expected match count once _filter_uefa_league_phase has isolated
the real league phase — independent of UEFA_LEAGUE_ROUNDS' round count
(which, for conference-league, intentionally over-asks, see its
docstring)."""

_UEFA_SLUGS = set(UEFA_LEAGUE_ROUNDS)
"""No OpenFootball coverage exists for any UEFA club competition —
TheSportsDB (plus its own known-good/per-round-immutable cache) is the
only source, same pattern for all three (see _fetch_matches_raw)."""

SEGUNDA_ROUNDS = 42
"""22 teams, double round-robin: 21 × 2 = 42 matchdays (462 matches total,
confirmed against the 22 × 21 real-data expectation)."""

RECENT_WINDOW_ROUNDS_BACK = 3
RECENT_WINDOW_ROUNDS_FORWARD = 1
"""[current_round - 3, current_round + 1]: wide enough to reach back past
OpenFootball's real staleness (verified live: as much as ~4 matchdays
behind) and one round into real upcoming fixtures."""

_OPENFOOTBALL_SLUGS = {
    "laliga",
    "premier-league",
    "serie-a",
    "ligue-1",
    "championship",
    "primeira-liga",
    "eredivisie",
}
"""The domestic leagues OpenFootball actually has a file for. Segunda is
deliberately excluded — verified live that its 2026-27 file doesn't exist
yet (see openfootball.py's _FILES comment) — and no UEFA competition is
ever in this set (see _UEFA_SLUGS)."""


def _merge_matches_by_identity(full_season: list[Match], recent: list[Match]) -> list[Match]:
    """Overwrites one OpenFootball fixture at a time with TheSportsDB's
    own version of that exact match — keyed by (home, away), both already
    canonicalized to the same naming convention (see
    sp_providers.openfootball's verified alias map) — rather than
    discarding a whole date range. Real bug found live: date-range
    replacement could drop a real OpenFootball match that TheSportsDB's
    window didn't actually end up covering (e.g. a rescheduled fixture),
    or keep a stale OpenFootball result past a TheSportsDB round that
    only partially succeeded.

    Overwrite rules, in order:
    - TheSportsDB has a real result (finished/live): always wins — a
      still-scheduled TheSportsDB entry never overwrites a real
      OpenFootball result.
    - Neither side has a real result yet (both still scheduled): prefer
      TheSportsDB's entry anyway. Real bug found live: OpenFootball's
      "scheduled" fixtures only carry a placeholder date (midnight UTC,
      no confirmed kick-off time) for anything beyond its own stale
      snapshot, while TheSportsDB's scheduled entries in this narrow
      recent window are the real, TV-confirmed day/time for the upcoming
      round — so even with no score yet, TheSportsDB's version is the
      more accurate one to show."""
    if not recent:
        return full_season
    full_season_keys = {(m.home, m.away) for m in full_season if m.home and m.away}
    recent_by_key = {(m.home, m.away): m for m in recent if m.home and m.away}

    def _resolve(m: Match) -> Match:
        if not (m.home and m.away):
            return m
        candidate = recent_by_key.get((m.home, m.away))
        if candidate is None:
            return m
        if candidate.status in (MatchStatus.FINISHED, MatchStatus.LIVE):
            return candidate
        if m.status != MatchStatus.FINISHED:
            return candidate
        return m

    merged = [_resolve(m) for m in full_season]
    # Any TheSportsDB match whose exact fixture never appeared in
    # OpenFootball's file at all (new/rescheduled pairing) — append it
    # too, rather than silently losing it. Deduplicated by identity among
    # themselves too: two overlapping requested rounds can genuinely
    # return the same fixture twice (e.g. a match postponed into the next
    # round's window).
    extra: list[Match] = []
    seen_extra_keys: set[tuple[str, str]] = set()
    for m in recent:
        key = (m.home, m.away) if m.home and m.away else None
        if key is not None and key in full_season_keys:
            continue
        if key is not None:
            if key in seen_extra_keys:
                continue
            seen_extra_keys.add(key)
        extra.append(m)
    return merged + extra


def _demote_stale_scheduled_matches(matches: list[Match]) -> list[Match]:
    """A match still marked SCHEDULED whose kickoff date has already
    passed is not a real upcoming fixture — neither source actually had
    a result for it (most often an OpenFootball entry TheSportsDB's
    window never reached). Relabel it UNKNOWN rather than ever fabricate
    a score, so the frontend can keep it strictly out of "próximos
    partidos" without claiming a result that doesn't exist."""
    today = datetime.now(timezone.utc).date()
    result: list[Match] = []
    for m in matches:
        kickoff = _kickoff_utc(m)
        if m.status == MatchStatus.SCHEDULED and kickoff is not None and kickoff.date() < today:
            m = m.model_copy(update={"status": MatchStatus.UNKNOWN})
        result.append(m)
    return result


async def _fetch_matches(client: httpx.AsyncClient, slug: str) -> list[Match]:
    matches = await _fetch_matches_raw(client, slug)
    matches = await _overlay_live_matches(client, slug, matches)
    return _demote_stale_scheduled_matches(matches)


async def _overlay_live_matches(client: httpx.AsyncClient, slug: str, matches: list[Match]) -> list[Match]:
    """Real bug found live: a match that's genuinely in progress right now
    can still be missing from a competition's own round-based fetch (its
    round's short-lived cache hasn't refreshed yet, or a request for it
    was rate-limited) even though LiveMatchesBanner already has it from
    the separate, cheap livescore call — clicking that live card then 404s
    on /analysis because the match id isn't in this competition's own
    list. Overlaying the same live data here (by real event id — TheSportsDB
    uses the same id in both endpoints) keeps every view consistent: the
    live score/minute replaces a stale scheduled entry, and a live match
    TheSportsDB's round fetch hasn't caught up with yet is still added."""
    if ALL_COMPETITIONS[slug].source != "thesportsdb":
        return matches
    try:
        live = await thesportsdb_provider.get_live_matches(client)
    except Exception:
        return matches
    live_for_slug = [m for m in live if m.competition_slug == slug]
    if not live_for_slug:
        return matches
    by_id = {m.id: m for m in matches}
    for live_match in live_for_slug:
        by_id[live_match.id] = live_match
    return list(by_id.values())


async def _cross_competition_pool(client: httpx.AsyncClient, current_slug: str) -> list[Match]:
    """Every real match this app has for every *other* competition in the
    same sport as `current_slug` — e.g. Real Madrid's LaLiga matches,
    pooled alongside the Champions League's own, so predict_match (see
    poisson.py's `pool_matches`) has more than one real data point to work
    with for a team whose sample in this one competition alone is thin.

    Each sibling competition goes through the exact same cached/
    known-good fetch path as every other request in this app
    (_fetch_matches) — a competition that's already cached from an
    earlier page view costs nothing extra; a cold one costs a real fetch,
    same as if the user had opened it directly. One competition failing
    (e.g. rate-limited) never breaks the others or the analysis itself —
    pooling is a real-data bonus, never a requirement."""
    sport = ALL_COMPETITIONS[current_slug].sport
    sibling_slugs = [
        slug for slug, comp in ALL_COMPETITIONS.items() if comp.sport == sport and slug != current_slug
    ]

    async def _safe_fetch(slug: str) -> list[Match]:
        try:
            return await _fetch_matches(client, slug)
        except Exception:
            return []

    results = await asyncio.gather(*(_safe_fetch(slug) for slug in sibling_slugs))
    pooled: list[Match] = []
    for matches in results:
        pooled.extend(matches)
    return pooled


async def _fill_gaps_from_season_bulk(
    client: httpx.AsyncClient,
    slug: str,
    season: str,
    matches: list[Match],
    expected: int,
    post_filter=lambda m: m,
) -> list[Match]:
    """Supplementary fallback for the TheSportsDB-only competitions
    (conference-league, europa-league, champions-league, segunda): when
    the per-round fetch (get_rounds), *after* whatever real filtering the
    caller applies (`post_filter` — e.g. _filter_uefa_league_phase), comes
    back short of the real expected count — almost always the free key's
    burst limit tripping on a couple of individual rounds, not a real gap
    in the season — try ONE extra call to eventsseason.php (TheSportsDB's
    whole-season endpoint) and merge in any real matches it has that the
    round fetch doesn't, by real event id. Deliberately only a
    *supplement*, never the primary source: this endpoint is documented
    (see ROUND_BASED_SLUGS) to have returned as few as ~15 events total
    for a whole competition in an earlier live check, so it may add
    nothing — but merging whatever real matches it does have costs
    nothing when the round fetch is already complete (skipped entirely in
    that case). The count check happens *after* filtering so a response
    padded with qualifying-round matches (see UEFA_LEAGUE_ROUNDS'
    conference-league docstring) isn't mistaken for a complete one."""
    if len(post_filter(matches)) >= expected:
        return matches
    try:
        bulk = await thesportsdb_provider.get_recent(client, slug, season)
    except Exception:
        return matches
    if not bulk:
        return matches
    by_id = {m.id: m for m in matches}
    added = 0
    for m in bulk:
        if m.id not in by_id:
            by_id[m.id] = m
            added += 1
    if added == 0:
        return matches
    return list(by_id.values())


async def _fetch_matches_raw(client: httpx.AsyncClient, slug: str) -> list[Match]:
    """Single source of truth for "every real match we have for this
    competition" — used by both /matches and /analysis so they see the
    same (cached) data and never issue duplicate requests against a
    rate-limited free API."""
    competition = ALL_COMPETITIONS[slug]

    if competition.source == "openligadb":
        return await openligadb_provider.get_matches(client, slug)

    if slug in _UEFA_SLUGS:
        # No OpenFootball coverage for any UEFA club competition — see
        # _UEFA_SLUGS.
        season = current_season(slug)
        matches = await thesportsdb_provider.get_rounds(
            client, slug, season, max_rounds=UEFA_LEAGUE_ROUNDS[slug]
        )
        matches = await _fill_gaps_from_season_bulk(
            client,
            slug,
            season,
            matches,
            expected=UEFA_LEAGUE_PHASE_MATCHES[slug],
            post_filter=lambda m: _filter_uefa_league_phase(m, slug),
        )
        # Real inconsistency found live (2026-10-23, conference-league):
        # a match's own `intRound` field (via eventspastleague.php) didn't
        # match what eventsround.php returned for that same round number
        # — TheSportsDB's round-indexing and its per-event intRound field
        # disagreed for this specific competition. eventspastleague.php
        # itself stayed reliable (it returned the real Oct-22 result
        # correctly), so it's merged in here too as a belt-and-braces
        # supplement — real event ids only, never replaces the round-based
        # fetch, just fills in whatever that fetch's round numbers missed.
        try:
            recent_past = await thesportsdb_provider.get_recent_past(client, slug)
        except Exception:
            recent_past = []
        if recent_past:
            by_id = {m.id: m for m in matches}
            for m in recent_past:
                by_id.setdefault(m.id, m)
            matches = list(by_id.values())
        return _filter_uefa_league_phase(matches, slug)

    if slug == "segunda":
        # Same TheSportsDB-only pattern as the UEFA competitions, for the
        # opposite reason: no qualifying-round pollution here (it's a flat
        # domestic double round-robin), but OpenFootball simply has no
        # 2026-27 file yet (verified live — see openfootball.py).
        season = current_season(slug)
        matches = await thesportsdb_provider.get_rounds(client, slug, season, max_rounds=SEGUNDA_ROUNDS)
        return await _fill_gaps_from_season_bulk(client, slug, season, matches, expected=462)

    if slug in _OPENFOOTBALL_SLUGS:
        # OpenFootball supplies the whole season's schedule (reliable for
        # anything more than a few weeks old, since it's a static
        # snapshot) and TheSportsDB supplies only a cheap, narrow window
        # around the *real current* matchday — exactly the stretch
        # OpenFootball is too stale to have. Merging the two closes the
        # gap without the 11-request burst that used to trip the free
        # key's rate limit.
        season = current_season(slug)
        full_season = await openfootball_provider.get_season(client, slug, season)

        # "Current round" from two independent signals: TheSportsDB's own
        # live discovery (1 cheap request) and a zero-network estimate
        # read straight off OpenFootball's own schedule dates (always
        # reliable, even though its *results* can be stale). Real problem
        # found live: the live discovery can itself return a stale round
        # when it's rate-limited into serving an old cached answer, which
        # silently narrowed the fetch window and left a ~10-day gap right
        # up to today uncovered. Taking whichever signal is *more
        # advanced* self-corrects that without guessing which one to
        # trust.
        discovered_round = await thesportsdb_provider.discover_current_round(client, slug)
        estimated_round = await openfootball_provider.estimate_current_round(client, slug, season)
        current_round = max((r for r in (discovered_round, estimated_round) if r), default=None)

        if current_round:
            window = range(
                max(1, current_round - RECENT_WINDOW_ROUNDS_BACK),
                current_round + RECENT_WINDOW_ROUNDS_FORWARD + 1,
            )
            recent = await thesportsdb_provider.get_recent_rounds(client, slug, season, window)
        else:
            # Both discovery signals failed — fall back to the old
            # full-season request pattern, which is often still cheap in
            # practice since it hits its own known-good cache rather than
            # the network.
            recent = await thesportsdb_provider.get_rounds(client, slug, season)
        return _merge_matches_by_identity(full_season, recent)

    season = current_season(slug)
    upcoming = await thesportsdb_provider.get_upcoming(client, slug)
    # Real bug found live: for a year-round tour (ATP/WTA), eventsseason.php
    # (get_recent) is capped from the *start* of that season — by October
    # that cap had long been used up by January's results, so real recent
    # results never surfaced. eventspastleague.php (get_recent_past) gives
    # the real most-recent events regardless of how long the season's been
    # running; both are merged (deduped by real event id) since a fresher-
    # season competition (NBA) may still have real value in get_recent too.
    recent = await thesportsdb_provider.get_recent(client, slug, season)
    recent_past = await thesportsdb_provider.get_recent_past(client, slug)
    seen_ids: set[str] = set()
    matches: list[Match] = []
    for match in [*upcoming, *recent_past, *recent]:
        if match.id in seen_ids:
            continue
        seen_ids.add(match.id)
        matches.append(match)

    if competition.sport == "tenis":
        try:
            matches = await thesportsdb_provider.enrich_player_headshots(client, matches)
        except Exception:
            pass
    return matches


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sports")
async def list_sports() -> list[dict]:
    return [{"slug": slug, "name": SPORT_NAMES[slug]} for slug in SPORTS]


@app.get("/api/sports/{sport}/competitions")
async def list_competitions(sport: str) -> list:
    if sport not in SPORTS:
        raise HTTPException(status_code=404, detail="Deporte no soportado todavía")
    # Real badge URLs harvested for free from already-fetched match data
    # (see thesportsdb.get_league_badge) — only overrides when a real one
    # has actually been seen; never fabricates one for a competition this
    # process hasn't fetched anything for yet.
    return [
        c.model_copy(update={"badge_url": c.badge_url or get_league_badge(c.slug)})
        for c in competitions_for_sport(sport)
    ]


@app.get("/api/competitions/{slug}/matches")
async def get_matches(slug: str) -> dict:
    if slug not in ALL_COMPETITIONS:
        raise HTTPException(status_code=404, detail="Competición desconocida")

    client: httpx.AsyncClient = app.state.http_client
    matches = await _snapshot_matches(client, slug)
    return {"competition": ALL_COMPETITIONS[slug], "matches": matches}


@app.get("/api/competitions/{slug}/quick-picks")
async def get_quick_picks(slug: str) -> dict:
    """A lightweight 1X2 + recommended-pick summary for every scheduled
    match in this competition — for MatchCard's favourite badge, so a
    card never needs its own /analysis round trip just to show who's
    favoured. Reads the same already-snapshotted pool/SoS/season-rating
    data as /analysis (see _snapshot_pool), so this is pure CPU (one
    small Poisson grid per scheduled match), never a network call."""
    if slug not in ALL_COMPETITIONS:
        raise HTTPException(status_code=404, detail="Competición desconocida")

    client: httpx.AsyncClient = app.state.http_client
    sport = ALL_COMPETITIONS[slug].sport
    if sport != "futbol":
        # Real bug found live: the prediction engine's markets (goles,
        # BTTS, hándicap de 0.25 goles...) are football-specific — showing
        # them on a basketball card ("Más de 1.5 goles" on an NBA game)
        # would be actively misleading, not just a labelling nit. Never
        # built/verified for baloncesto's much higher, differently-
        # distributed scoring, so it stays off rather than mislabel it.
        return {}

    matches = await _snapshot_matches(client, slug)
    scheduled = [m for m in matches if m.status == MatchStatus.SCHEDULED and m.home and m.away]
    if not scheduled:
        return {}

    pool = await _snapshot_pool(client, sport, slug)
    season_ratings = _snapshot.season_ratings_by_sport.get(sport)
    sos_corrections = _snapshot.sos_by_sport.get(sport)

    picks: dict[str, dict] = {}
    for m in scheduled:
        prediction = predict_match(
            matches,
            m.home,
            m.away,
            pool_matches=pool,
            match_kickoff=m.kickoff,
            season_ratings=season_ratings,
            sos_corrections=sos_corrections,
        )
        if prediction is None:
            continue
        picks[m.id] = {
            "label": prediction.recommended_pick_label,
            "pct": prediction.recommended_pick_pct,
            "home_win_pct": prediction.home_win_pct,
            "draw_pct": prediction.draw_pct,
            "away_win_pct": prediction.away_win_pct,
        }
    return picks


@app.get("/api/sports/{sport}/live")
async def get_live(sport: str) -> dict:
    """🔴 EN DIRECTO AHORA: every real in-progress match for this sport
    right now, from TheSportsDB's own live signal (see get_live_matches —
    one real elapsed-minute string per match, never estimated), read
    straight from the snapshot the fast background loop keeps warm (see
    LIVE_REFRESH_INTERVAL_SECONDS) — never a live call inside this
    request. When nothing is live, falls back to today's still-upcoming
    matches across every loaded competition in this sport, so the banner
    always has something honest to show."""
    if sport not in SPORTS:
        raise HTTPException(status_code=404, detail="Deporte no soportado todavía")
    if sport != "futbol":
        # TheSportsDB's free livescore endpoint is split by sport
        # (`s=Soccer`/`s=Basketball`/...) and only football's been
        # verified live so far — never claim live coverage for a sport
        # this hasn't actually been checked against.
        return {"live": [], "upcoming_today": []}

    if _snapshot.live_matches:
        return {"live": _snapshot.live_matches, "upcoming_today": []}

    client: httpx.AsyncClient = app.state.http_client
    today = datetime.now(timezone.utc).date()
    slugs = [c.slug for c in competitions_for_sport(sport)]
    pool = _snapshot.pool_by_sport.get(sport)
    if pool is None:
        results = await asyncio.gather(*(_snapshot_matches(client, slug) for slug in slugs))
        pool = [m for matches in results for m in matches]
    upcoming_today = sorted(
        (
            m
            for m in pool
            if m.status == MatchStatus.SCHEDULED
            and (k := _kickoff_utc(m)) is not None
            and k.date() == today
        ),
        key=_kickoff_utc,
    )[:10]
    return {"live": [], "upcoming_today": upcoming_today}


async def _compute_standings(
    client: httpx.AsyncClient, slug: str, competition, matches: list[Match] | None
):
    if not competition.supports_standings:
        return None
    if slug in ROUND_BASED_SLUGS:
        # TheSportsDB's own lookuptable.php is capped at exactly 5 rows on
        # the free tier (verified live — even the fixture captured
        # earlier for this project only ever had 5). Our own computed
        # table from the real matches we already fetch covers every team
        # in that window (verified live: all 20 Premier League teams) —
        # strictly more complete, and costs no extra request.
        if matches is None:
            matches = await _fetch_matches(client, slug)
        return compute_table(matches, tiebreak="uefa" if slug in _UEFA_SLUGS else "h2h")
    if competition.source == "openligadb":
        return await openligadb_provider.get_standings(client, slug)
    season = current_season(slug)
    return await thesportsdb_provider.get_standings(client, slug, season)


@app.get("/api/competitions/{slug}/standings")
async def get_standings(slug: str) -> dict:
    competition = ALL_COMPETITIONS.get(slug)
    if competition is None:
        raise HTTPException(status_code=404, detail="Competición desconocida")

    client: httpx.AsyncClient = app.state.http_client
    standings = await _snapshot_standings(client, slug, competition)
    return {"competition": competition, "standings": standings}


@app.get("/api/competitions/{slug}/audit")
async def get_completeness_audit(slug: str) -> dict:
    """Diagnostic only — never a gate on the real endpoints above. Reports
    how close the real data currently fetched is to a full season, so a
    gap is visible and can be checked, without ever refusing to answer
    when the real count is merely close (a postponed match is real life,
    not a bug)."""
    competition = ALL_COMPETITIONS.get(slug)
    if competition is None:
        raise HTTPException(status_code=404, detail="Competición desconocida")

    client: httpx.AsyncClient = app.state.http_client
    matches = await _snapshot_matches(client, slug)
    standings = await _snapshot_standings(client, slug, competition)
    audit = audit_completeness(slug, matches, standings)
    return {
        "competition_slug": audit.competition_slug,
        "matches_found": audit.matches_found,
        "matches_expected": audit.matches_expected,
        "teams_found": audit.teams_found,
        "teams_expected": audit.teams_expected,
        "matches_complete": audit.matches_complete,
        "teams_complete": audit.teams_complete,
        "is_complete": audit.is_complete,
    }


@app.get("/api/competitions/{slug}/matches/{match_id}/analysis")
async def get_match_analysis(slug: str, match_id: str) -> MatchAnalysis:
    if slug not in ALL_COMPETITIONS:
        raise HTTPException(status_code=404, detail="Competición desconocida")

    client: httpx.AsyncClient = app.state.http_client
    matches = await _snapshot_matches(client, slug)

    match = next((m for m in matches if m.id == match_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido desconocido en esta competición")

    if not match.home or not match.away:
        return MatchAnalysis(
            match_id=match_id,
            prediction=None,
            home_form=[],
            away_form=[],
            head_to_head=[],
            note=(
                "Esta fuente no da nombres de equipo/jugador estructurados para "
                "este deporte, así que no se puede calcular forma, H2H ni "
                "predicción sin inventarlos."
            ),
        )

    sport = ALL_COMPETITIONS[slug].sport
    prediction = None
    if match.status == MatchStatus.SCHEDULED and sport == "futbol":
        pool = await _snapshot_pool(client, sport, slug)
        prediction = predict_match(
            matches,
            match.home,
            match.away,
            pool_matches=pool,
            match_kickoff=match.kickoff,
            season_ratings=_snapshot.season_ratings_by_sport.get(sport),
            sos_corrections=_snapshot.sos_by_sport.get(sport),
        )
    note = None
    if sport != "futbol":
        # Real bug found live: the engine's markets (goles, BTTS, hándicap
        # en cuartos de gol...) are football-specific and were never built
        # or verified for baloncesto's much higher, differently-
        # distributed scoring — showing them would mislabel a real result,
        # not just omit one, so it stays off rather than guess.
        note = "La predicción con este motor solo está disponible para fútbol por ahora."
    elif match.status != MatchStatus.SCHEDULED:
        note = "La predicción solo se calcula para partidos aún no jugados."
    elif prediction is None:
        note = (
            "Muestra insuficiente en la fuente gratuita para calcular una "
            "predicción fiable (hace falta un mínimo de partidos reales como "
            "local/visitante de cada equipo en esta competición)."
        )

    stats = None
    if match.status == MatchStatus.FINISHED and match.source == "thesportsdb":
        stats = await thesportsdb_provider.get_match_stats(client, match.id)

    return MatchAnalysis(
        match_id=match_id,
        prediction=prediction,
        home_form=recent_form(matches, match.home, limit=10),
        away_form=recent_form(matches, match.away, limit=10),
        head_to_head=head_to_head(matches, match.home, match.away),
        stats=stats,
        note=note,
    )


@app.get("/api/home/highlights")
async def get_home_highlights() -> HomeHighlights:
    client: httpx.AsyncClient = app.state.http_client
    return await build_home_highlights(
        client,
        openligadb_provider,
        thesportsdb_provider,
        _snapshot_matches,
        _snapshot_standings,
        pool_matches=_snapshot.pool_by_sport.get("futbol"),
        season_ratings=_snapshot.season_ratings_by_sport.get("futbol"),
        sos_corrections=_snapshot.sos_by_sport.get("futbol"),
    )


@app.get("/api/teams/search")
async def search_teams(q: str) -> list[TeamSummary]:
    client: httpx.AsyncClient = app.state.http_client
    return await teams_module.search_teams(client, _snapshot_matches, q)


@app.get("/api/teams/{competition_slug}/{team_id}/history")
async def get_team_history(
    competition_slug: str,
    team_id: str,
    venue: str = "all",
    limit: int | None = None,
) -> TeamHistory:
    if venue not in {"all", "home", "away"}:
        raise HTTPException(status_code=422, detail="venue debe ser all, home o away")

    client: httpx.AsyncClient = app.state.http_client
    history = await teams_module.get_team_history(
        client, _snapshot_matches, competition_slug, team_id, venue, limit  # type: ignore[arg-type]
    )
    if history is None:
        raise HTTPException(status_code=404, detail="Competición o equipo desconocido")
    return history
