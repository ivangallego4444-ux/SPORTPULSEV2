"""Orchestrates the home dashboard's real-data aggregation across every
wired football competition. This is the only place that fans out to
several competitions at once — kept separate from main.py's per-
competition routes so that logic (and its honest partial-failure
handling) is easy to find and test independently of the fetch layer.
"""

from __future__ import annotations

from datetime import timezone

import httpx

from sp_core.models import HighlightMatch, HomeHighlights, MatchStatus, PlatformTelemetry
from sp_predict import (
    backtest_accuracy,
    compute_table,
    pick_featured,
    pick_top_btts,
    pick_top_by_favorite,
    pick_top_over_2_5,
    predict_match,
)
from sp_providers.openligadb import OpenLigaDBProvider
from sp_providers.registry import ALL_COMPETITIONS
from sp_providers.thesportsdb import ROUND_BASED_SLUGS, TheSportsDBProvider, current_season

FOOTBALL_COMPETITION_SLUGS = [slug for slug, c in ALL_COMPETITIONS.items() if c.sport == "futbol"]

MINI_STANDINGS_SLUGS = ["laliga", "premier-league", "bundesliga", "serie-a", "champions-league"]

TICKER_MAX = 20


async def build_home_highlights(
    client: httpx.AsyncClient,
    openligadb_provider: OpenLigaDBProvider,
    thesportsdb_provider: TheSportsDBProvider,
    fetch_matches,
    fetch_standings=None,
    pool_matches: list | None = None,
    season_ratings: dict | None = None,
    sos_corrections: dict | None = None,
) -> HomeHighlights:
    """`fetch_standings`, when given, is a `(client, slug, competition) ->
    standings` callable (see apps/api/app/main.py's `_snapshot_standings`)
    used instead of a direct provider call — keeps this request off the
    network the same way `fetch_matches` already does. None (the default)
    falls back to the original direct-fetch behavior, unchanged.

    `pool_matches`/`season_ratings`/`sos_corrections`, when given, are
    passed straight through to predict_match for every scheduled match
    here too (see poisson.py) — the same cross-competition, SoS- and
    season-rating-aware prediction the match analysis endpoint uses,
    rather than a plain single-competition one just because this is the
    home page."""
    all_highlights: list[HighlightMatch] = []
    unavailable: list[str] = []
    mini_standings: dict[str, list] = {}
    matches_loaded = 0
    total_correct = 0
    total_checked = 0

    for slug in FOOTBALL_COMPETITION_SLUGS:
        competition = ALL_COMPETITIONS[slug]
        try:
            matches = await fetch_matches(client, slug)
        except Exception:  # noqa: BLE001 - a single competition failing must never break the home page
            matches = []

        if not matches:
            unavailable.append(slug)
            continue

        matches_loaded += len(matches)

        correct, checked = backtest_accuracy(matches)
        total_correct += correct
        total_checked += checked

        for match in matches:
            prediction = None
            if (
                match.status == MatchStatus.SCHEDULED
                and match.home
                and match.away
            ):
                prediction = predict_match(
                    matches,
                    match.home,
                    match.away,
                    pool_matches=pool_matches,
                    match_kickoff=match.kickoff,
                    season_ratings=season_ratings,
                    sos_corrections=sos_corrections,
                )
            all_highlights.append(HighlightMatch(match=match, prediction=prediction))

        if slug in MINI_STANDINGS_SLUGS and competition.supports_standings:
            if fetch_standings is not None:
                standings = await fetch_standings(client, slug, competition)
            elif slug in ROUND_BASED_SLUGS:
                # lookuptable.php is capped at 5 rows on the free tier
                # (verified live) — compute the real table from the
                # matches already fetched instead, same fix as main.py.
                standings = compute_table(matches, tiebreak="uefa" if slug == "champions-league" else "h2h")
            elif competition.source == "openligadb":
                standings = await openligadb_provider.get_standings(client, slug)
            else:
                standings = await thesportsdb_provider.get_standings(client, slug, current_season(slug))
            if standings:
                mini_standings[slug] = standings[:5]

    def _kickoff_sort_key(highlight: HighlightMatch) -> float:
        kickoff = highlight.match.kickoff
        if kickoff is None:
            return 0.0
        aware = kickoff if kickoff.tzinfo else kickoff.replace(tzinfo=timezone.utc)
        return aware.timestamp()

    all_highlights.sort(key=_kickoff_sort_key, reverse=True)
    ticker = all_highlights[:TICKER_MAX]
    predictions_computed = sum(1 for h in all_highlights if h.prediction is not None)

    telemetry = PlatformTelemetry(
        leagues_connected=len(FOOTBALL_COMPETITION_SLUGS),
        matches_loaded=matches_loaded,
        predictions_computed=predictions_computed,
        model_accuracy_pct=round(100 * total_correct / total_checked, 1) if total_checked else None,
        model_accuracy_sample=total_checked,
    )

    return HomeHighlights(
        featured=pick_featured(all_highlights),
        ticker=ticker,
        top_by_favorite=pick_top_by_favorite(all_highlights),
        top_over_2_5=pick_top_over_2_5(all_highlights),
        top_btts=pick_top_btts(all_highlights),
        mini_standings=mini_standings,
        unavailable=unavailable,
        telemetry=telemetry,
    )
