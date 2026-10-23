from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    UNKNOWN = "unknown"


class Match(BaseModel):
    """One event, shared across every sport.

    Some sources (e.g. tennis via TheSportsDB) don't give structured
    home/away team objects or numeric scores, only free text. `home`/`away`
    and `home_score`/`away_score` are None in that case, and `summary`
    carries the real result text instead — never invent numbers to fill
    the gap.
    """

    id: str
    sport: str
    competition_slug: str
    competition_name: str
    status: MatchStatus
    kickoff: datetime | None
    home: str | None
    away: str | None
    home_id: str | None = None
    away_id: str | None = None
    """Source-native team id, when the source gives one. Used internally to
    line up recent-form/H2H lookups reliably (names can repeat or vary in
    spelling); exposed on the API too since it's harmless."""
    home_crest: str | None = None
    away_crest: str | None = None
    home_score: int | None
    away_score: int | None
    live_minute: str | None = None
    """Real elapsed-time string straight from the source (e.g. "63",
    "90+2", "HT") for a MatchStatus.LIVE match — only ever populated from
    a source's own live signal (see thesportsdb's get_live_matches), never
    estimated from kickoff time."""
    title: str | None = None
    """Fallback display string for sources with no clean home/away split
    (e.g. tennis player-vs-player events from TheSportsDB)."""
    summary: str | None
    venue: str | None
    source: str


class StandingRow(BaseModel):
    rank: int
    team: str
    played: int | None
    wins: int | None
    draws: int | None
    losses: int | None
    points: int | None
    crest_url: str | None


class FormResult(BaseModel):
    """One past result for a team, as shown in a W/D/L recent-form strip."""

    match_id: str
    date: datetime | None
    opponent: str
    venue: Literal["home", "away"]
    goals_for: int
    goals_against: int
    outcome: Literal["W", "D", "L"]


class ScorelineProbability(BaseModel):
    home_goals: int
    away_goals: int
    pct: float


class HandicapLine(BaseModel):
    line: float
    """Asian handicap line applied to the home team (negative favours the
    home team, e.g. -0.5 means it must win outright)."""
    cover_pct: float
    """Expected fraction of the stake won (0-100): 100 = always covers,
    50 = an exact push, 0 = never covers. Quarter lines (e.g. -0.25) are a
    50/50 blend of their two neighbouring clean lines, matching how a
    real split-stake Asian handicap settles — never a bookmaker price."""


class MarginBucket(BaseModel):
    label: str
    margin: int
    """Home goals minus away goals, clamped to [-3, 3] (3 means "by 3 or
    more", -3 means "by 3 or more" the other way)."""
    pct: float


class MatchPrediction(BaseModel):
    """Real statistical estimate from each team's actual goals-for/against
    record in the competition's fetched real matches — never a bookmaker
    odds figure, never a fabricated number. `sample_size` and `note` make
    the data basis explicit so the UI never presents this as more certain
    than it is.
    """

    method: str
    confidence: Literal["real_history", "league_average"]
    """"real_history": both sides met the minimum real-match threshold.
    "league_average": at least one side's attack/defense ratio leans on
    the competition's average because it doesn't have enough (or any)
    real matches yet — still a real number, just a weaker basis, and the
    UI should say so rather than showing it identically to a full
    real-history prediction."""
    home_matches_used: int
    away_matches_used: int
    h2h_matches_considered: int
    """How many real past meetings between these two exact teams fed the
    head-to-head adjustment below — 0 means that adjustment was neutral."""
    h2h_adjustment_pct: float
    """How much the head-to-head record shifted the goal expectation
    (positive favours the home side), already capped at ±15 — 0.0 when
    h2h_matches_considered is 0."""
    home_attack_rating: float
    home_defense_rating: float
    away_attack_rating: float
    away_defense_rating: float
    """Each team's real attack/defense strength in its venue role,
    relative to the competition's own average (1.0 = exactly average,
    1.25 = 25% above average, recency-weighted). These four numbers are
    what the Dixon-Coles lambdas below are actually built from — exposed
    so the UI can show *why* a prediction leans the way it does, not just
    the final percentages."""
    expected_goals_home: float
    expected_goals_away: float
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    double_chance_1x_pct: float
    double_chance_x2_pct: float
    double_chance_12_pct: float
    btts_yes_pct: float
    btts_no_pct: float
    over_1_5_pct: float
    over_2_5_pct: float
    over_3_5_pct: float
    top_scorelines: list[ScorelineProbability]
    """The 3 most probable exact final scores, highest probability first."""
    scoreline_grid: list[ScorelineProbability]
    """Every combination from 0-0 to 5-5 (36 cells) for a scoreline heatmap
    — the same probabilities as `top_scorelines`, just unfiltered."""
    asian_handicap: list[HandicapLine]
    margin_distribution: list[MarginBucket]
    recommended_pick_label: str
    """Plain-language description of whichever real computed market has
    the highest probability for this match (e.g. "Doble oportunidad 1X
    (Local o Empate)") — a selection among the numbers above, never a
    new, separately-invented metric."""
    recommended_pick_pct: float
    expected_corners_home: float
    expected_corners_away: float
    expected_corners_total: float
    """A modelled estimate, not a measured statistic: no free source
    integrated here gives real corner counts, pre- or post-match (see
    MatchStats's own docstring). Scales a fixed, documented baseline
    corners-per-side figure by each team's real, already-computed attack
    rating — the same numbers behind the goal expectation above — as a
    transparent proxy for attacking intent. Always label this as an
    estimate in the UI, never as a measured figure."""
    corners_over_8_5_pct: float
    corners_over_9_5_pct: float
    corners_favoured_side: Literal["home", "away", "even"]
    note: str


class MatchStatLine(BaseModel):
    label: str
    home_value: float
    away_value: float


class MatchStats(BaseModel):
    """Real per-match statistics (shots, etc.) from TheSportsDB's free
    `lookupeventstats.php` — only available for already-finished matches,
    and only shots-related figures; corners and cards were checked across
    several real matches and are consistently absent from this free
    endpoint, so we don't claim to have them (see docs/DATA_SOURCES.md)."""

    lines: list[MatchStatLine]


class MatchAnalysis(BaseModel):
    """Everything we can honestly say about one upcoming match from real
    data already fetched for its competition. Any field can be None/empty
    — that means the data genuinely isn't available, not an error."""

    match_id: str
    prediction: MatchPrediction | None
    home_form: list[FormResult]
    away_form: list[FormResult]
    head_to_head: list[FormResult]
    stats: MatchStats | None = None
    note: str | None = None


class HighlightMatch(BaseModel):
    """A `Match` plus its prediction (if any), for the home dashboard's
    ticker / "top picks" / "partido del día" — always built from matches
    a provider already fetched, never a new synthetic match."""

    match: Match
    prediction: MatchPrediction | None


class PlatformTelemetry(BaseModel):
    """Real, computed-from-actual-data counters for the "PRO" dashboard
    panels — never invented numbers. `model_accuracy_pct` is a genuine
    walk-forward backtest (see sp_predict.backtest): each past match is
    graded using only the matches that happened strictly before it, so a
    match's own result never leaks into its own prediction."""

    leagues_connected: int
    matches_loaded: int
    predictions_computed: int
    model_accuracy_pct: float | None
    model_accuracy_sample: int
    """How many past matches the accuracy figure above is based on — show
    this next to the percentage so it's never read as more certain than
    the sample supports."""


class HomeHighlights(BaseModel):
    """Real-data aggregation across every wired football competition. Any
    list can be empty and `featured` can be None — that means nothing in
    the currently-fetched data qualified, not an error. `unavailable`
    lists which competitions couldn't be loaded this time (e.g. rate
    limited) so the UI can say so instead of silently showing less."""

    featured: HighlightMatch | None
    ticker: list[HighlightMatch]
    top_by_favorite: list[HighlightMatch]
    top_over_2_5: list[HighlightMatch]
    top_btts: list[HighlightMatch]
    mini_standings: dict[str, list[StandingRow]]
    unavailable: list[str]
    telemetry: PlatformTelemetry


class TeamSummary(BaseModel):
    team_id: str
    team_name: str
    crest_url: str | None
    competition_slug: str
    competition_name: str
    sport: str


class TeamAggregateStats(BaseModel):
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for_avg: float
    goals_against_avg: float
    over_1_5_pct: float
    over_2_5_pct: float
    over_3_5_pct: float
    btts_pct: float


class TeamHistory(BaseModel):
    team: TeamSummary
    venue_filter: Literal["all", "home", "away"]
    matches: list[FormResult]
    aggregate: TeamAggregateStats | None
    """None when there are zero matches in the selected window — nothing
    to average."""


class Competition(BaseModel):
    """Describes one competition a provider exposes, including honest
    limitations so the API/UI never has to guess what's actually available.
    """

    sport: str
    slug: str
    name: str
    source: str
    supports_standings: bool
    supports_upcoming: bool
    notes: str | None = None
    badge_url: str | None = None
    """Real competition logo, verified live against the source (TheSportsDB's
    own `strBadge`/`strLogo` for a league, or OpenLigaDB's equivalent) —
    never a guessed/constructed CDN URL. None when not yet verified rather
    than a broken image."""
    country: str | None = None
    """Real country/region this competition is organized in (e.g. "España",
    "Europa" for UEFA club competitions) — used only for filtering, never
    guessed."""
