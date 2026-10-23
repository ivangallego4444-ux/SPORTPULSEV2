"""Real statistical match prediction from real historical goals data.

This is a Poisson goals model (team attack/defense strength relative to
the competition's own average) with the Dixon-Coles low-score correlation
correction, plus a bounded head-to-head adjustment — not a bookmaker odds
feed. It only ever runs on `Match` objects already fetched from a
verified free source (see docs/DATA_SOURCES.md), and never invents a
team's scoring rate.

Each team's attack/defense ratio is a *recency-weighted* average over
every real finished match it has in the given venue role this season (not
just the last 5) — more recent matches count more, on the theory that a
team's current form matters more than how it played months ago. See
`_weighted_average` for the exact decay.

Every side (home/away) uses whatever real matches it actually has. When a
side has fewer than `MIN_MATCHES` real appearances in that venue role —
including zero, e.g. a newly-promoted team or an early Champions League
matchday — its missing attack/defense ratio is assumed neutral (exactly
the competition's own average, not invented out of thin air), so a
prediction is still produced instead of silently giving up. What changes
is `confidence` and the `method`/`note` text: a prediction leaning on the
league average for either side is clearly labelled "league_average", not
presented as being as reliable as one backed by real team-specific
history. The only case with no prediction at all is when the competition
itself has zero finished matches yet — then there's no league average to
fall back to either.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sp_core.models import (
    HandicapLine,
    MarginBucket,
    Match,
    MatchPrediction,
    MatchStatus,
    ScorelineProbability,
)

from .history import head_to_head

MIN_MATCHES = 3
"""Minimum real home (resp. away) matches a team needs for its side of
the prediction to count as "real history" rather than "league average"."""

SHRINKAGE_K = 8.0
"""Real bug found live: Real Madrid away in the Champions League, with
exactly 1 real match on record so far this season, showed a 1.3% win
probability — one noisy data point (expected_goals_away collapsed to
0.05) swinging the whole prediction, with nothing to pull it back toward
plausibility. SHRINKAGE_K is the weight (in "matches worth") given to the
competition's own real average in an empirical-Bayes blend: a team's
shrunk rate is (raw_rate * played + league_avg * K) / (played + K) — at
played=1 that's ~89% league average, 11% the one real result; at
played=8 it's an even split; well past played=8 it converges to the
team's own real number. This is a standard, textbook small-sample
technique (it only ever blends two real numbers — a team's own average
and the competition's own average — never injects an external opinion
about how good a team "really" is), and K=8 is a fixed, documented
constant in the same spirit as RECENCY_DECAY/DIXON_COLES_RHO below, not
fitted per-team or per-competition.

Deliberately NOT implemented: a hardcoded "club strength" prior/tier
list (e.g. "Real Madrid = 1.40"). That would mean hand-assigning a
fabricated number to every notable club across 6 competitions based on
reputation rather than any real data this project has access to —
exactly the kind of invented figure this project has refused everywhere
else. Shrinkage toward the competition's own real average fixes the
actual failure mode (a tiny sample swinging wildly) without needing to
invent an opinion about any specific club."""

MAX_GOALS_GRID = 12
"""Poisson grid upper bound per side. Wide enough that the tail mass
beyond it stays negligible even for a strongly-favoured team with a high
expected-goals estimate (lambda up to the 6.0 clamp below)."""

DISPLAY_GOALS_GRID = 5
"""Upper bound for the scoreline heatmap/top-scorelines — 0-5 per side
(36 cells) covers the overwhelming majority of real probability mass and
matches what a scoreline heatmap conventionally shows."""

RECENCY_DECAY = 0.90
"""Each match one step further back in a team's own sequence counts 10%
less than the next most recent one (weight = DECAY**matches_ago). A
plain, well-understood exponential-decay weighting — not a fitted/tuned
parameter, since we have no held-out data in this project to tune it
against without risking overfitting to a handful of matches."""

DIXON_COLES_RHO = -0.11
"""Fixed low-score correlation correction from Dixon & Coles (1997): a
plain Poisson model assumes home and away goals are independent, which
systematically under-rates real-world low-scoring results (0-0, 1-0, 0-1,
1-1 occur more often than independence predicts, because a cautious game
state suppresses both sides' scoring at once). -0.11 sits in the
commonly-cited range for this correction (Dixon & Coles' own fitted value
for English football was close to this); like RECENCY_DECAY, it is a
fixed, documented constant rather than a value fitted per-competition —
this project has no held-out dataset to fit it against without
overfitting to a handful of matches. Applied only to the four low-score
cells (0,0), (1,0), (0,1), (1,1) — see _dixon_coles_tau — then the whole
grid is renormalized so probabilities still sum to 1."""

H2H_ADJUSTMENT_CAP = 0.08
"""Head-to-head dominance can shift each side's expected goals by at most
±8% — a real signal from real past meetings between these two exact
teams, but bounded so a single historical blowout can't swing the whole
prediction. Tightened from an earlier ±15%: now that attack/defense
ratios already draw on a cross-competition pool, SoS, and a structural
season rating (see STRUCTURAL_RATING_WEIGHT), H2H is one real signal
among several rather than the dominant one."""

HANDICAP_LINES = [-0.75, -0.5, -0.25, 0.0, 0.25, 0.5]
"""Asian handicap lines applied to the home team, as requested: quarter
lines are reported as a blend of their two neighbouring clean lines (see
HandicapLine.cover_pct), matching how a real split-stake handicap settles.
0.0 ("pick'em") is a clean line with a genuine push on an exact draw."""

BASE_HOME_CORNERS = 5.5
BASE_AWAY_CORNERS = 4.3
"""Fixed baseline average corners per side in a typical top-five European
league (~9.8 total, home side usually attacks more and draws more
corners) — NOT fitted to any specific competition's real data, because no
free source integrated here gives real corner counts at all (pre- or
post-match — see MatchStats's own docstring on the shots-only free
endpoint). This is a documented, widely-cited starting point, scaled per
match by each side's real attack rating (the same ratios driving the
goal expectation). Always presented in the UI as a modelled estimate,
never as a measured statistic."""

CORNERS_ATTACK_DAMPING = 0.5
"""Real bug found live: an early-season team with an extreme attack
rating (e.g. 2.5x league average after winning every match) produced an
implausible ~14 expected corners for that side alone — corners don't
scale 1:1 with goal-scoring dominance the way the rating implies; a team
that converts chances efficiently can rack up a lopsided scoreline
without a proportionally lopsided corner count. Only half of the
rating's deviation from "exactly average" (1.0) carries through to the
corners estimate; CORNERS_PER_SIDE_RANGE below bounds the result to what
a real match can plausibly show either way."""

CORNERS_PER_SIDE_RANGE = (2.0, 8.5)
"""Realistic bounds for one side's expected corners in a single match —
even a very one-sided real game rarely sits outside this range."""

CORNERS_GRID = 25
"""Upper bound for the corners-total Poisson sum — corner counts rarely
exceed the high teens, so this leaves negligible tail mass uncounted."""

VENUE_BLEND_WEIGHT = 0.6
GLOBAL_BLEND_WEIGHT = 0.4
"""Real bug found live: Real Madrid away in the Champions League had
exactly 1 real away match on record — SHRINKAGE_K alone still leaned the
prediction almost entirely on the competition average because the *venue-
specific* sample was so thin, even though Real Madrid's overall real
record (home and away, and — via `pool_matches`, see predict_match — other
competitions too) was large and strong. Blending 60% of the team's
venue-specific rate with 40% of its *global* rate (every real match it
has, any venue, from whatever `pool_matches` was given) before shrinkage
means a thin venue-specific sample still benefits from the team's broader
real form instead of collapsing to "we don't know this team." When a team
has no matches in the other venue role (every single-competition test
fixture in this project, by construction), global == venue and this is a
no-op — only a genuinely richer sample changes anything."""

FULL_SEASON_WEIGHT = 0.65
RECENT_FORM_WEIGHT = 0.35
RECENT_FORM_MATCHES = 5
"""Explicit two-window split (replaces a single exponential decay):
FULL_SEASON_WEIGHT of the plain mean over every real match this team has
in a given role + RECENT_FORM_WEIGHT of the plain mean over just its last
RECENT_FORM_MATCHES — current form counts extra without letting only a
handful of recent results define the whole rate (see _dual_window_average).
Pedido explícito del usuario: separar la base de temporada completa de la
forma reciente en vez de un decaimiento implícito."""

STRUCTURAL_RATING_WEIGHT = 0.35
EMPIRICAL_RATE_WEIGHT = 0.65
STRUCTURAL_RATING_CLAMP = (0.5, 1.8)
"""Weight given to each team's Dynamic Season Rating (see
_dynamic_season_ratings) versus its empirical, dual-windowed,
shrunk goal rate when forming the final attack/defense ratio. The
structural rating is itself shrunk toward neutral (1.0) by real sample
size before this blend (same empirical-Bayes technique as SHRINKAGE_K),
so a team with almost no real matches yet contributes almost nothing
unusual here — this can never swing a prediction on its own, only
stabilize one that already has some real signal."""

SOS_ITERATIONS = 2
SOS_LOOKUP_CLAMP = (0.5, 2.0)
SOS_CORRECTION_CLAMP = (0.85, 1.20)
"""Strength-of-Schedule: a real, iterative adjustment of each team's
attack/defense index by the actual strength of the opponents it faced in
each real match (3 goals against the pool's best defense means more than
3 against its worst) — 2 passes over the same real pool of matches, each
refining every team's index using the *previous* pass's opponent
strengths. The result is only ever used as a bounded correction on the
team's own already-computed rate (SOS_CORRECTION_CLAMP), never a
standalone number — this keeps a thin sample's one unusual opponent from
swinging a prediction, while still rewarding/penalising real, verifiable
schedule difficulty. See _sos_adjusted_indices."""

REST_DAYS_THRESHOLD = 4.0
REST_DAYS_MAX_PENALTY = 0.07
"""Real fixture-congestion fatigue: a team whose previous *real* match
(any competition, any venue, from the same pool used for its attack/
defense numbers) was fewer than REST_DAYS_THRESHOLD days before this one
has its expected goals reduced, linearly from 0% at the threshold up to
REST_DAYS_MAX_PENALTY at 0 days' rest — e.g. a team that played in Europe
midweek and is back again at the weekend. Needs the match being predicted
to carry its own real kickoff (see predict_match's `match_kickoff`); with
none given, or no real prior match to measure from, the penalty is 0 —
never guessed."""



def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def _dixon_coles_tau(h: int, a: int, lam: float, mu: float, rho: float) -> float:
    """Low-score correlation correction factor — 1.0 outside {0,1}x{0,1}."""
    if h == 0 and a == 0:
        return 1 - lam * mu * rho
    if h == 0 and a == 1:
        return 1 + lam * rho
    if h == 1 and a == 0:
        return 1 + mu * rho
    if h == 1 and a == 1:
        return 1 - rho
    return 1.0


def _kickoff_sort_key(match: Match) -> float:
    if match.kickoff is None:
        return 0.0
    kickoff = match.kickoff if match.kickoff.tzinfo else match.kickoff.replace(tzinfo=timezone.utc)
    return kickoff.timestamp()


def _weighted_average(values_oldest_first: list[float], decay: float = RECENCY_DECAY) -> float:
    """Exponentially recency-weighted mean — the last element (most
    recent) gets weight 1, the one before it `decay`, two before `decay^2`,
    and so on. Falls back to a plain mean when there's only one value."""
    n = len(values_oldest_first)
    if n == 0:
        return 0.0
    weights = [decay ** (n - 1 - i) for i in range(n)]
    return sum(v * w for v, w in zip(values_oldest_first, weights)) / sum(weights)


def _dual_window_average(values_oldest_first: list[float]) -> float:
    """See FULL_SEASON_WEIGHT/RECENT_FORM_WEIGHT: FULL_SEASON_WEIGHT of
    the plain mean over every value + RECENT_FORM_WEIGHT of the plain mean
    over just the last RECENT_FORM_MATCHES. Falls back to the single
    available value when there's only one."""
    n = len(values_oldest_first)
    if n == 0:
        return 0.0
    full_season_avg = sum(values_oldest_first) / n
    recent = values_oldest_first[-RECENT_FORM_MATCHES:]
    recent_avg = sum(recent) / len(recent)
    return full_season_avg * FULL_SEASON_WEIGHT + recent_avg * RECENT_FORM_WEIGHT


@dataclass
class _TeamRecord:
    # Each tuple is (kickoff_sort_key, goals_for, goals_against, opponent),
    # appended in chronological order so recency/dual-window weighting and
    # Strength-of-Schedule (which needs to know who the opponent actually
    # was) can both apply directly.
    home_matches: list[tuple[float, int, int, str]] = field(default_factory=list)
    away_matches: list[tuple[float, int, int, str]] = field(default_factory=list)


def _finished_matches(matches: list[Match]) -> list[Match]:
    finished = [
        m
        for m in matches
        if m.status == MatchStatus.FINISHED
        and m.home_score is not None
        and m.away_score is not None
        and m.home
        and m.away
    ]
    finished.sort(key=_kickoff_sort_key)  # oldest first, so weighting-by-recency is well-defined
    return finished


def _collect_stats(matches: list[Match]) -> tuple[dict[str, _TeamRecord], float, float, int]:
    finished = _finished_matches(matches)

    records: dict[str, _TeamRecord] = {}
    total_home_goals = 0
    total_away_goals = 0

    for m in finished:
        home_record = records.setdefault(m.home, _TeamRecord())
        away_record = records.setdefault(m.away, _TeamRecord())

        key = _kickoff_sort_key(m)
        home_record.home_matches.append((key, m.home_score, m.away_score, m.away))
        away_record.away_matches.append((key, m.away_score, m.home_score, m.home))

        total_home_goals += m.home_score
        total_away_goals += m.away_score

    n = len(finished)
    league_home_avg = total_home_goals / n if n else 0.0
    league_away_avg = total_away_goals / n if n else 0.0
    return records, league_home_avg, league_away_avg, n


@dataclass
class _SeasonStats:
    matches: int = 0
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0
    scored_count: int = 0
    clean_sheet_count: int = 0


def _season_stats_by_team(pool_matches: list[Match]) -> dict[str, _SeasonStats]:
    stats: dict[str, _SeasonStats] = {}
    for m in _finished_matches(pool_matches):
        for team, gf, ga in ((m.home, m.home_score, m.away_score), (m.away, m.away_score, m.home_score)):
            s = stats.setdefault(team, _SeasonStats())
            s.matches += 1
            s.goals_for += gf
            s.goals_against += ga
            if gf > 0:
                s.scored_count += 1
            if ga == 0:
                s.clean_sheet_count += 1
            if gf > ga:
                s.points += 3
            elif gf == ga:
                s.points += 1
    return stats


def _dynamic_season_ratings(pool_matches: list[Match]) -> dict[str, tuple[float, int]]:
    """team -> (rating, real_matches_used). A single composite index,
    1.0 = exactly average among the real teams actually present in this
    pool, combining real points-per-game, goal-difference-per-game, % of
    matches scored in, and % of clean sheets — each team's WHOLE real
    record across every competition in `pool_matches`, not just its most
    recent matches, so a 2-match hot/cold stretch alone can't move it
    much. Shrunk toward neutral (1.0) by real sample size via SHRINKAGE_K
    (same empirical-Bayes technique the rest of this module already uses)
    so a team with almost no real matches yet barely registers here."""
    by_team = _season_stats_by_team(pool_matches)
    if not by_team:
        return {}

    avg_ppg = sum(s.points / s.matches for s in by_team.values()) / len(by_team)
    avg_gd = sum((s.goals_for - s.goals_against) / s.matches for s in by_team.values()) / len(by_team)
    avg_scored = sum(s.scored_count / s.matches for s in by_team.values()) / len(by_team)
    avg_clean = sum(s.clean_sheet_count / s.matches for s in by_team.values()) / len(by_team)

    low, high = STRUCTURAL_RATING_CLAMP
    ratings: dict[str, tuple[float, int]] = {}
    for team, s in by_team.items():
        n = s.matches
        ppg_ratio = (s.points / n) / avg_ppg if avg_ppg > 0 else 1.0
        gd_ratio = 1 + ((s.goals_for - s.goals_against) / n - avg_gd) * 0.15
        scored_ratio = (s.scored_count / n) / avg_scored if avg_scored > 0 else 1.0
        clean_ratio = (s.clean_sheet_count / n) / avg_clean if avg_clean > 0 else 1.0

        raw_rating = max(low, min((ppg_ratio + gd_ratio + scored_ratio + clean_ratio) / 4, high))
        shrunk = (raw_rating * n + 1.0 * SHRINKAGE_K) / (n + SHRINKAGE_K)
        ratings[team] = (shrunk, n)
    return ratings


def _initial_sos_indices(
    records: dict[str, _TeamRecord], league_avg_goals: float
) -> dict[str, tuple[float, float]]:
    indices: dict[str, tuple[float, float]] = {}
    for team, record in records.items():
        all_matches = record.home_matches + record.away_matches
        if not all_matches or league_avg_goals <= 0:
            indices[team] = (1.0, 1.0)
            continue
        gf_avg = sum(gf for _, gf, _, _ in all_matches) / len(all_matches)
        ga_avg = sum(ga for _, _, ga, _ in all_matches) / len(all_matches)
        indices[team] = (gf_avg / league_avg_goals, ga_avg / league_avg_goals)
    return indices


def _sos_adjusted_indices(
    records: dict[str, _TeamRecord], league_avg_goals: float
) -> dict[str, tuple[float, float]]:
    """Strength-of-Schedule: SOS_ITERATIONS passes re-weighting each real
    match's goals by the real strength of the specific opponent actually
    faced (3 goals against the pool's best defense means more than 3
    against its worst) — see SOS_ITERATIONS' docstring. Every input is a
    real match already in the pool; nothing here is estimated."""
    if league_avg_goals <= 0:
        return {team: (1.0, 1.0) for team in records}

    indices = _initial_sos_indices(records, league_avg_goals)
    low, high = SOS_LOOKUP_CLAMP
    for _ in range(SOS_ITERATIONS):
        adjusted_for: dict[str, list[float]] = {}
        adjusted_against: dict[str, list[float]] = {}
        for team, record in records.items():
            for _, gf, ga, opponent in record.home_matches + record.away_matches:
                opp_attack, opp_defense = indices.get(opponent, (1.0, 1.0))
                opp_attack = max(low, min(opp_attack, high))
                opp_defense = max(low, min(opp_defense, high))
                adjusted_for.setdefault(team, []).append(gf / opp_defense)
                adjusted_against.setdefault(team, []).append(ga / opp_attack)
        indices = {
            team: (
                (sum(adjusted_for[team]) / len(adjusted_for[team]) / league_avg_goals)
                if team in adjusted_for
                else indices[team][0],
                (sum(adjusted_against[team]) / len(adjusted_against[team]) / league_avg_goals)
                if team in adjusted_against
                else indices[team][1],
            )
            for team in records
        }
    return indices


def _sos_corrections(pool_records: dict[str, _TeamRecord], pool_matches: list[Match]) -> dict[str, tuple[float, float]]:
    """team -> (attack_correction, defense_correction), each a bounded
    ratio (SOS_CORRECTION_CLAMP) of the SoS-adjusted index over the naive
    one — "how much this team's real record changes once you account for
    who it actually played"."""
    finished = _finished_matches(pool_matches)
    if not finished:
        return {}
    total_goals = sum((m.home_score or 0) + (m.away_score or 0) for m in finished)
    league_avg_goals = total_goals / (2 * len(finished))

    naive = _initial_sos_indices(pool_records, league_avg_goals)
    adjusted = _sos_adjusted_indices(pool_records, league_avg_goals)
    low, high = SOS_CORRECTION_CLAMP
    corrections: dict[str, tuple[float, float]] = {}
    for team, (naive_attack, naive_defense) in naive.items():
        adj_attack, adj_defense = adjusted.get(team, (naive_attack, naive_defense))
        attack_correction = (adj_attack / naive_attack) if naive_attack > 0 else 1.0
        defense_correction = (adj_defense / naive_defense) if naive_defense > 0 else 1.0
        corrections[team] = (max(low, min(attack_correction, high)), max(low, min(defense_correction, high)))
    return corrections


def _rest_penalty(record: _TeamRecord | None, match_kickoff: datetime | None) -> float:
    """0.0..REST_DAYS_MAX_PENALTY: how much to reduce this team's expected
    goals for short real rest since its last real match (any competition,
    any venue, from the same pool used for its attack/defense numbers)
    before the match being predicted. See REST_DAYS_THRESHOLD/
    REST_DAYS_MAX_PENALTY. 0.0 whenever the predicted match's own kickoff
    isn't given, or there's no real prior match to measure from."""
    if match_kickoff is None or record is None:
        return 0.0
    match_ts_dt = match_kickoff if match_kickoff.tzinfo else match_kickoff.replace(tzinfo=timezone.utc)
    match_ts = match_ts_dt.timestamp()
    prior = [key for key, *_ in (record.home_matches + record.away_matches) if key < match_ts]
    if not prior:
        return 0.0
    rest_days = (match_ts - max(prior)) / 86400
    if rest_days >= REST_DAYS_THRESHOLD:
        return 0.0
    if rest_days <= 0:
        return REST_DAYS_MAX_PENALTY
    return REST_DAYS_MAX_PENALTY * (1 - rest_days / REST_DAYS_THRESHOLD)


def _team_strength(
    record: _TeamRecord | None,
    venue: str,
    safe_home_avg: float,
    safe_away_avg: float,
    structural_rating: float,
    sos_correction: tuple[float, float],
) -> tuple[float, float, int]:
    """(attack_ratio, defense_ratio, real_matches_used) for one team's one
    venue role. Combines, from real data only:
    - a dual-windowed (FULL_SEASON_WEIGHT/RECENT_FORM_WEIGHT), venue/
      global-blended (VENUE_BLEND_WEIGHT/GLOBAL_BLEND_WEIGHT) empirical
      goal rate, shrunk toward the competition's own real average via
      SHRINKAGE_K (see its docstring — a real bug found live);
    - that team's Dynamic Season Rating (STRUCTURAL_RATING_WEIGHT), a
      full-season structural anchor;
    - a bounded Strength-of-Schedule correction for the real opponents
      actually faced.
    Falls back to (structural_rating, 1/structural_rating) when there are
    zero real matches for this venue role — still real, cross-competition
    data about this team, never a fabricated number."""
    sos_attack_correction, sos_defense_correction = sos_correction
    venue_matches = (record.home_matches if venue == "home" else record.away_matches) if record else []
    played = len(venue_matches)
    if played == 0:
        safe_rating = max(structural_rating, STRUCTURAL_RATING_CLAMP[0])
        return structural_rating, 1 / safe_rating, 0

    venue_goals_for = _dual_window_average([gf for _, gf, _, _ in venue_matches])
    venue_goals_against = _dual_window_average([ga for _, _, ga, _ in venue_matches])

    # See VENUE_BLEND_WEIGHT/GLOBAL_BLEND_WEIGHT docstring: the team's
    # *global* rate across every real match it has (any venue) — when it
    # has none in the other role, this is just the venue matches again, so
    # the blend below is a no-op.
    all_matches = sorted((record.home_matches + record.away_matches) if record else [], key=lambda t: t[0])
    global_goals_for = _dual_window_average([gf for _, gf, _, _ in all_matches]) if all_matches else venue_goals_for
    global_goals_against = (
        _dual_window_average([ga for _, _, ga, _ in all_matches]) if all_matches else venue_goals_against
    )

    raw_goals_for = venue_goals_for * VENUE_BLEND_WEIGHT + global_goals_for * GLOBAL_BLEND_WEIGHT
    raw_goals_against = venue_goals_against * VENUE_BLEND_WEIGHT + global_goals_against * GLOBAL_BLEND_WEIGHT

    league_for_avg = safe_home_avg if venue == "home" else safe_away_avg
    league_against_avg = safe_away_avg if venue == "home" else safe_home_avg

    # Empirical-Bayes shrinkage: blends the team's own (real) average with
    # the competition's own (real) average, weighted by real sample size.
    # At played=0 this would be 100% league average (handled above); at
    # played >> SHRINKAGE_K it converges to the team's own raw average;
    # in between — e.g. a real 1-match Champions League sample — it stays
    # close to the league average instead of swinging on one data point.
    goals_for = (raw_goals_for * played + league_for_avg * SHRINKAGE_K) / (played + SHRINKAGE_K)
    goals_against = (raw_goals_against * played + league_against_avg * SHRINKAGE_K) / (played + SHRINKAGE_K)

    if venue == "home":
        empirical_attack = goals_for / safe_home_avg
        empirical_defense = goals_against / safe_away_avg
    else:
        empirical_attack = goals_for / safe_away_avg
        empirical_defense = goals_against / safe_home_avg

    safe_structural = max(structural_rating, STRUCTURAL_RATING_CLAMP[0])
    attack = empirical_attack * EMPIRICAL_RATE_WEIGHT + structural_rating * STRUCTURAL_RATING_WEIGHT
    defense = empirical_defense * EMPIRICAL_RATE_WEIGHT + (1 / safe_structural) * STRUCTURAL_RATING_WEIGHT

    attack *= sos_attack_correction
    defense *= sos_defense_correction

    return attack, defense, played


def _h2h_adjustment(matches: list[Match], home_team: str, away_team: str) -> tuple[float, int]:
    """Real head-to-head dominance, capped at ±H2H_ADJUSTMENT_CAP. Positive
    means the home side has historically dominated this exact matchup."""
    meetings = head_to_head(matches, home_team, away_team)
    if not meetings:
        return 0.0, 0
    avg_goal_diff = sum(m.goals_for - m.goals_against for m in meetings) / len(meetings)
    # 5% of a lambda shift per average goal of historical margin, capped.
    adjustment = max(-H2H_ADJUSTMENT_CAP, min(H2H_ADJUSTMENT_CAP, avg_goal_diff * 0.05))
    return adjustment, len(meetings)


def _clean_line_outcome(diff: int, line: float) -> float:
    """1.0 win / 0.5 push / 0.0 loss for the home side on one clean
    (integer or half) Asian handicap line."""
    adjusted = diff + line
    if adjusted > 0:
        return 1.0
    if adjusted == 0:
        return 0.5
    return 0.0


def _handicap_cover_pct(diff_probs: dict[int, float], line: float) -> float:
    is_quarter = abs((line * 4) % 2) != 0
    if is_quarter:
        lo, hi = line - 0.25, line + 0.25
        return round(
            sum(
                p * ((_clean_line_outcome(d, lo) + _clean_line_outcome(d, hi)) / 2)
                for d, p in diff_probs.items()
            )
            * 100,
            1,
        )
    return round(sum(p * _clean_line_outcome(d, line) for d, p in diff_probs.items()) * 100, 1)


def _recommend_pick(candidates: dict[str, float]) -> tuple[str, float]:
    """Picks whichever real candidate market has the highest probability
    — a selection among already-computed numbers, in plain Spanish."""
    label, pct = max(candidates.items(), key=lambda item: item[1])
    return label, round(pct, 1)


def _corners_estimate(
    attack_home: float, attack_away: float
) -> tuple[float, float, float, float, float, str]:
    """Modelled corners estimate — see BASE_HOME_CORNERS/BASE_AWAY_CORNERS
    docstring for why this is a proxy, not a measured statistic. Treats
    total corners as Poisson-distributed (a standard count-data
    approximation) around the scaled baseline to get Over 8.5/9.5
    probabilities, the same technique already used for goals."""
    damped_home = 1 + (attack_home - 1) * CORNERS_ATTACK_DAMPING
    damped_away = 1 + (attack_away - 1) * CORNERS_ATTACK_DAMPING
    low, high = CORNERS_PER_SIDE_RANGE
    corners_home = max(low, min(BASE_HOME_CORNERS * damped_home, high))
    corners_away = max(low, min(BASE_AWAY_CORNERS * damped_away, high))
    corners_total = corners_home + corners_away

    over_8_5 = over_9_5 = 0.0
    for k in range(CORNERS_GRID + 1):
        p = _poisson_pmf(k, corners_total)
        if k > 8.5:
            over_8_5 += p
        if k > 9.5:
            over_9_5 += p

    if corners_home > corners_away * 1.1:
        favoured = "home"
    elif corners_away > corners_home * 1.1:
        favoured = "away"
    else:
        favoured = "even"

    return (
        round(corners_home, 1),
        round(corners_away, 1),
        round(corners_total, 1),
        round(over_8_5 * 100, 1),
        round(over_9_5 * 100, 1),
        favoured,
    )


def predict_match(
    matches: list[Match],
    home_team: str,
    away_team: str,
    pool_matches: list[Match] | None = None,
    match_kickoff: datetime | None = None,
    season_ratings: dict[str, tuple[float, int]] | None = None,
    sos_corrections: dict[str, tuple[float, float]] | None = None,
) -> MatchPrediction | None:
    """`matches` should be every real match fetched for one competition
    (any status) — it alone defines "this competition's own real average"
    (the environment the two teams are about to play in) and is what H2H
    is scoped to. Returns None only when the competition has zero finished
    matches yet — otherwise always returns a prediction, with
    `confidence`/`method`/`note` stating plainly how much of it rests on
    real team-specific history versus the competition's average.

    `pool_matches`, when given, is a larger real cross-competition match
    pool (e.g. a team's LaLiga *and* Champions League matches combined) —
    see apps/api/app/main.py's analysis endpoint — used for each team's
    attack/defense numbers (see _team_strength), its Dynamic Season Rating
    (_dynamic_season_ratings) and its Strength-of-Schedule correction
    (_sos_corrections). Defaults to `matches` (no pooling), which keeps
    this fully backward-compatible with a single-competition call.

    `match_kickoff`, when given, is the real kickoff of the match being
    predicted — used only to compute each side's real rest days since its
    previous match (see REST_DAYS_THRESHOLD). None (the default) means no
    rest-days adjustment, same as before this factor existed.

    `season_ratings`/`sos_corrections`, when given, are the already-
    computed outputs of `_dynamic_season_ratings`/`_sos_corrections` over
    `pool_matches` — e.g. precomputed once in the background every
    FULL_REFRESH_INTERVAL_SECONDS in apps/api/app/main.py's `_snapshot`,
    rather than recomputed from scratch on every single request. None (the
    default) computes them here instead, same as before these params
    existed — this is a pure performance optimization, never a change in
    what gets computed."""

    records, league_home_avg, league_away_avg, n = _collect_stats(matches)
    if n == 0:
        return None

    effective_pool = matches if pool_matches is None else pool_matches
    pool_records = records if pool_matches is None else _collect_stats(effective_pool)[0]
    home_record = pool_records.get(home_team)
    away_record = pool_records.get(away_team)

    # A genuine league-wide average of exactly 0 (every match so far
    # 0-0) is real data, not "missing" — floor only the denominator to
    # avoid a division by zero, never the lambda itself.
    safe_home_avg = max(league_home_avg, 0.01)
    safe_away_avg = max(league_away_avg, 0.01)

    if season_ratings is None:
        season_ratings = _dynamic_season_ratings(effective_pool)
    home_rating, _ = season_ratings.get(home_team, (1.0, 0))
    away_rating, _ = season_ratings.get(away_team, (1.0, 0))

    if sos_corrections is None:
        sos_corrections = _sos_corrections(pool_records, effective_pool)
    home_sos = sos_corrections.get(home_team, (1.0, 1.0))
    away_sos = sos_corrections.get(away_team, (1.0, 1.0))

    attack_home, defense_home, home_used = _team_strength(
        home_record, "home", safe_home_avg, safe_away_avg, home_rating, home_sos
    )
    attack_away, defense_away, away_used = _team_strength(
        away_record, "away", safe_home_avg, safe_away_avg, away_rating, away_sos
    )

    lambda_home = league_home_avg * attack_home * defense_away
    lambda_away = league_away_avg * attack_away * defense_home

    h2h_adjustment, h2h_used = _h2h_adjustment(matches, home_team, away_team)
    lambda_home *= 1 + h2h_adjustment
    lambda_away *= 1 - h2h_adjustment

    home_rest_penalty = _rest_penalty(home_record, match_kickoff)
    away_rest_penalty = _rest_penalty(away_record, match_kickoff)
    lambda_home *= 1 - home_rest_penalty
    lambda_away *= 1 - away_rest_penalty

    # Clamp against wild early-season ratios (e.g. a team with 3 home
    # games and 0 goals conceded) blowing up the Poisson tail.
    lambda_home = max(0.05, min(lambda_home, 6.0))
    lambda_away = max(0.05, min(lambda_away, 6.0))

    home_win = draw = away_win = 0.0
    btts_yes = 0.0
    over_counts = {1.5: 0.0, 2.5: 0.0, 3.5: 0.0}
    diff_probs: dict[int, float] = {}
    scoreline_probs: dict[tuple[int, int], float] = {}

    raw_grid: list[list[float]] = [[0.0] * (MAX_GOALS_GRID + 1) for _ in range(MAX_GOALS_GRID + 1)]
    total_mass = 0.0
    for h in range(MAX_GOALS_GRID + 1):
        p_h = _poisson_pmf(h, lambda_home)
        for a in range(MAX_GOALS_GRID + 1):
            p = p_h * _poisson_pmf(a, lambda_away) * _dixon_coles_tau(
                h, a, lambda_home, lambda_away, DIXON_COLES_RHO
            )
            p = max(p, 0.0)
            raw_grid[h][a] = p
            total_mass += p

    # Renormalize: the Dixon-Coles correction nudges mass around a finite
    # grid, so the probabilities must still sum to 1 exactly.
    norm = total_mass if total_mass > 0 else 1.0
    for h in range(MAX_GOALS_GRID + 1):
        for a in range(MAX_GOALS_GRID + 1):
            p = raw_grid[h][a] / norm
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
            if h >= 1 and a >= 1:
                btts_yes += p
            total_goals = h + a
            for threshold in over_counts:
                if total_goals > threshold:
                    over_counts[threshold] += p

            diff = max(-3, min(3, h - a))
            diff_probs[diff] = diff_probs.get(diff, 0.0) + p

            if h <= DISPLAY_GOALS_GRID and a <= DISPLAY_GOALS_GRID:
                scoreline_probs[(h, a)] = scoreline_probs.get((h, a), 0.0) + p

    has_full_history = home_used >= MIN_MATCHES and away_used >= MIN_MATCHES
    confidence = "real_history" if has_full_history else "league_average"

    if home_used == 0 and away_used == 0:
        method = "Media general de la competición (sin historial de ninguno de los dos equipos todavía)"
    elif has_full_history:
        method = (
            "Poisson-Dixon-Coles multifactorial: historial real completo "
            "(temporada completa + forma reciente), ajustado por fuerza real del "
            "rival (SoS), rating de temporada dinámico, H2H y descanso"
        )
    else:
        method = (
            "Poisson-Dixon-Coles multifactorial con historial parcial, "
            "completado con la media de la competición"
        )

    sample_scope = "en esta competición" if pool_matches is None else "en todas las competiciones cargadas"
    rest_note = ""
    if home_rest_penalty > 0 or away_rest_penalty > 0:
        rest_note = (
            f" Penalización por descanso corto aplicada: "
            f"{home_team} -{round(home_rest_penalty * 100, 1)}%, "
            f"{away_team} -{round(away_rest_penalty * 100, 1)}% (sobre sus goles esperados)."
        )
    note = (
        f"Calculado con {home_used} partidos reales de {home_team} como local y "
        f"{away_used} de {away_team} como visitante {sample_scope} (base de "
        f"temporada completa {round(FULL_SEASON_WEIGHT * 100)}% + forma de los "
        f"últimos {RECENT_FORM_MATCHES} partidos {round(RECENT_FORM_WEIGHT * 100)}%, "
        f"ajustado por la fuerza real de cada rival al que se enfrentaron), "
        f"con un rating de temporada dinámico (PPG + diferencia de goles + "
        f"consistencia, peso {round(STRUCTURAL_RATING_WEIGHT * 100)}%), corrección "
        "Dixon-Coles para resultados bajos y ajuste de hasta "
        f"{round(H2H_ADJUSTMENT_CAP * 100)}% por el historial de enfrentamientos "
        f"directos reales en esta competición ({h2h_used} encontrados)."
        f"{rest_note} "
    )
    if confidence == "league_average":
        note += (
            "Historial insuficiente todavía para uno de los dos equipos (o para "
            "ambos): la parte que falta se estima con la media general de goles "
            "de la competición, no con el rendimiento real de ese equipo — trátalo "
            "como una estimación básica, no como una predicción afinada."
        )
    else:
        note += "Es una probabilidad estadística estimada, no una cuota de casa de apuestas."

    sorted_scorelines = sorted(scoreline_probs.items(), key=lambda item: item[1], reverse=True)
    top_scorelines = [
        ScorelineProbability(home_goals=hg, away_goals=ag, pct=round(p * 100, 1))
        for (hg, ag), p in sorted_scorelines[:3]
    ]
    scoreline_grid = [
        ScorelineProbability(home_goals=hg, away_goals=ag, pct=round(p * 100, 1))
        for (hg, ag), p in sorted(scoreline_probs.items())
    ]

    asian_handicap = [
        HandicapLine(line=line, cover_pct=_handicap_cover_pct(diff_probs, line)) for line in HANDICAP_LINES
    ]

    margin_labels = {-3: "-3 o más", -2: "-2", -1: "-1", 0: "Empate", 1: "+1", 2: "+2", 3: "+3 o más"}
    margin_distribution = [
        MarginBucket(label=margin_labels[m], margin=m, pct=round(diff_probs.get(m, 0.0) * 100, 1))
        for m in range(-3, 4)
    ]

    home_win_pct = round(home_win * 100, 1)
    draw_pct = round(draw * 100, 1)
    away_win_pct = round(away_win * 100, 1)
    over_2_5_pct = round(over_counts[2.5] * 100, 1)
    double_chance_1x_pct = round((home_win + draw) * 100, 1)
    double_chance_x2_pct = round((draw + away_win) * 100, 1)
    double_chance_12_pct = round((home_win + away_win) * 100, 1)
    btts_yes_pct = round(btts_yes * 100, 1)

    pick_candidates = {
        "Victoria local": home_win_pct,
        "Empate": draw_pct,
        "Victoria visitante": away_win_pct,
        "Doble oportunidad 1X (local o empate)": double_chance_1x_pct,
        "Doble oportunidad X2 (empate o visitante)": double_chance_x2_pct,
        "Doble oportunidad 12 (sin empate)": double_chance_12_pct,
        "Más de 1.5 goles": round(over_counts[1.5] * 100, 1),
        "Más de 2.5 goles": over_2_5_pct,
        "Menos de 2.5 goles": round(100 - over_2_5_pct, 1),
        "Ambos equipos marcan: sí": btts_yes_pct,
        "Ambos equipos marcan: no": round(100 - btts_yes_pct, 1),
    }
    pick_label, pick_pct = _recommend_pick(pick_candidates)

    (
        corners_home,
        corners_away,
        corners_total,
        corners_over_8_5_pct,
        corners_over_9_5_pct,
        corners_favoured_side,
    ) = _corners_estimate(attack_home, attack_away)

    return MatchPrediction(
        method=method,
        confidence=confidence,
        home_matches_used=home_used,
        away_matches_used=away_used,
        h2h_matches_considered=h2h_used,
        h2h_adjustment_pct=round(h2h_adjustment * 100, 1),
        home_attack_rating=round(attack_home, 2),
        home_defense_rating=round(defense_home, 2),
        away_attack_rating=round(attack_away, 2),
        away_defense_rating=round(defense_away, 2),
        expected_goals_home=round(lambda_home, 2),
        expected_goals_away=round(lambda_away, 2),
        home_win_pct=home_win_pct,
        draw_pct=draw_pct,
        away_win_pct=away_win_pct,
        double_chance_1x_pct=double_chance_1x_pct,
        double_chance_x2_pct=double_chance_x2_pct,
        double_chance_12_pct=double_chance_12_pct,
        btts_yes_pct=btts_yes_pct,
        btts_no_pct=round((1 - btts_yes) * 100, 1),
        over_1_5_pct=round(over_counts[1.5] * 100, 1),
        over_2_5_pct=over_2_5_pct,
        over_3_5_pct=round(over_counts[3.5] * 100, 1),
        top_scorelines=top_scorelines,
        scoreline_grid=scoreline_grid,
        asian_handicap=asian_handicap,
        margin_distribution=margin_distribution,
        recommended_pick_label=pick_label,
        recommended_pick_pct=pick_pct,
        expected_corners_home=corners_home,
        expected_corners_away=corners_away,
        expected_corners_total=corners_total,
        corners_over_8_5_pct=corners_over_8_5_pct,
        corners_over_9_5_pct=corners_over_9_5_pct,
        corners_favoured_side=corners_favoured_side,
        note=note,
    )
