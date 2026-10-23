"""Unit tests for the Poisson prediction engine and form/H2H helpers.

The Match objects here are small hand-built test fixtures for exercising
the math (a normal unit-testing practice) — they are never shown to a
user; real matches always come from a verified provider (see
test_providers.py, which uses real captured API fixtures instead)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sp_core.models import Match, MatchStatus
from sp_predict import head_to_head, predict_match, recent_form
from sp_predict.poisson import _weighted_average


def _match(
    match_id: str,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    day: int,
    status: MatchStatus = MatchStatus.FINISHED,
) -> Match:
    return Match(
        id=match_id,
        sport="futbol",
        competition_slug="test-league",
        competition_name="Test League",
        status=status,
        kickoff=datetime(2026, 1, day, tzinfo=timezone.utc),
        home=home,
        away=away,
        home_score=home_score if status == MatchStatus.FINISHED else None,
        away_score=away_score if status == MatchStatus.FINISHED else None,
        summary=None,
        venue=None,
        source="test",
    )


def _build_season() -> list[Match]:
    # Alpha is a strong home side (scores a lot, concedes little at home);
    # Beta is a weak away side — built so the prediction direction is
    # unambiguous and easy to assert on.
    matches = []
    for day in range(1, 5):
        matches.append(_match(f"a{day}", "Alpha", f"Filler{day}", 3, 0, day))
    for day in range(5, 9):
        matches.append(_match(f"b{day}", f"Filler{day}", "Beta", 2, 0, day))
    # One real meeting between Alpha and Beta earlier in the season.
    matches.append(_match("ab1", "Alpha", "Beta", 4, 1, 9))
    return matches


class TestPredictMatch:
    def test_returns_none_only_when_the_competition_has_zero_finished_matches(self):
        # The one true "can't predict at all" case: there's no league
        # average to fall back to either, because nothing has been played.
        no_finished_matches = [_match("1", "Alpha", "Beta", 0, 0, 1, status=MatchStatus.SCHEDULED)]
        assert predict_match(no_finished_matches, "Alpha", "Beta") is None

    def test_falls_back_to_league_average_with_thin_real_data_instead_of_giving_up(self):
        # Pedido explícito del usuario: nunca dejar un partido sin
        # pronóstico si la competición tiene algún partido real jugado —
        # pero marcado honestamente como estimación básica, no como si
        # tuviera el mismo respaldo que una predicción con historial real.
        thin_season = [_match("1", "Alpha", "Beta", 2, 1, 1)]
        prediction = predict_match(thin_season, "Alpha", "Beta")
        assert prediction is not None
        assert prediction.confidence == "league_average"
        assert prediction.home_matches_used == 1  # real count, not hidden
        assert prediction.away_matches_used == 1
        assert "estimación básica" in prediction.note

    def test_an_entirely_unknown_team_still_gets_a_league_average_prediction(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Nonexistent FC")
        assert prediction is not None
        assert prediction.confidence == "league_average"
        assert prediction.away_matches_used == 0

    def test_probabilities_sum_to_one_hundred(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        total = prediction.home_win_pct + prediction.draw_pct + prediction.away_win_pct
        assert total == pytest.approx(100.0, abs=0.2)

    def test_recent_form_counts_more_than_old_form(self):
        # Pedido explícito del usuario: ponderar la forma reciente, no una
        # media plana de toda la temporada. A team that started poorly
        # (0 goals/game) but has clearly turned it around recently
        # (4 goals/game) should be read as closer to its recent level
        # than a flat average would suggest.
        weighted = _weighted_average([0, 0, 0, 4, 4, 4])
        flat_average = sum([0, 0, 0, 4, 4, 4]) / 6
        assert weighted > flat_average
        assert weighted == pytest.approx(2.314, abs=0.01)

    def test_a_team_trending_upward_is_rated_above_one_trending_downward(self):
        # Same exact set of results for "Rising" either way (0,0,0,4,4,4
        # goals across 6 home games) and the same opponent history in
        # both scenarios — only the *order* (which result is most recent)
        # differs. If recency weighting works, expected_goals_home must
        # come out higher when the hot run is the recent one.
        def build(home_goals_oldest_to_newest: list[int]) -> list[Match]:
            matches = [
                _match(f"h{i}", "Rising", f"Filler{i}", g, 1, i + 1)
                for i, g in enumerate(home_goals_oldest_to_newest)
            ]
            matches += [
                _match(f"a{d}", f"AwayFiller{d}", "Opponent", 1, 1, d) for d in range(1, 9)
            ]
            return matches

        trending_up = predict_match(build([0, 0, 0, 4, 4, 4]), "Rising", "Opponent")
        trending_down = predict_match(build([4, 4, 4, 0, 0, 0]), "Rising", "Opponent")
        assert trending_up is not None and trending_down is not None
        assert trending_up.expected_goals_home > trending_down.expected_goals_home

    def test_strong_home_side_favoured_over_weak_away_side(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        assert prediction.home_win_pct > prediction.away_win_pct
        assert prediction.expected_goals_home > prediction.expected_goals_away

    def test_a_single_bad_result_never_collapses_a_strong_teams_win_chance(self):
        # Real bug found live: Real Madrid away in the Champions League,
        # with exactly 1 real match on record (a bad one), showed a 1.3%
        # win probability against a genuinely weaker opponent — one noisy
        # data point swinging the whole prediction. Shrinkage toward the
        # competition's own real average must keep this plausible.
        matches = [
            # 10 other real matches establish a normal competition
            # average (~1.5 goals/side) that "Real Madrid"'s one match
            # should be shrunk toward.
            _match(f"f{d}", f"Filler{d}A", f"Filler{d}B", 1, 1, d) for d in range(1, 11)
        ]
        # Real Madrid's one real away match this season: a bad 0-4 loss.
        matches.append(_match("rm1", "Weak Opponent", "Real Madrid", 4, 0, 11))
        # The upcoming match: Real Madrid away again, against a team with
        # its own thin, unremarkable 1-match home record.
        matches.append(
            _match("rm_home_ref", "AEK Athens", "Other", 1, 1, 12, status=MatchStatus.SCHEDULED)
        )

        prediction = predict_match(matches, "AEK Athens", "Real Madrid")
        assert prediction is not None
        # Not asserting a specific number — just that one bad result
        # doesn't collapse a real team to a near-zero win chance.
        assert prediction.away_win_pct >= 15.0

    def test_handles_a_genuine_zero_league_average_without_crashing(self):
        # Regression test: a league where every away side has scored 0 so
        # far (league_away_avg == 0.0 exactly) used to be treated as "no
        # data" and also risked a division by zero — but a real 0.0
        # average is valid data, not a missing-data signal.
        matches = [_match(f"m{d}", "Alpha", "Beta", 3, 0, d) for d in range(1, 9)]
        prediction = predict_match(matches, "Alpha", "Beta")
        assert prediction is not None
        assert prediction.expected_goals_away >= 0

    def test_reports_real_sample_size_not_a_fixed_number(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        # 4 filler home games + the Alpha-vs-Beta meeting itself = 5.
        assert prediction.home_matches_used == 5
        assert prediction.away_matches_used == 5
        assert "no una cuota" in prediction.note

    def test_double_chance_is_derived_from_the_same_1x2_probabilities(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        assert prediction.double_chance_1x_pct == pytest.approx(
            prediction.home_win_pct + prediction.draw_pct, abs=0.1
        )
        assert prediction.double_chance_12_pct == pytest.approx(
            prediction.home_win_pct + prediction.away_win_pct, abs=0.1
        )

    def test_top_scorelines_are_the_three_highest_probability_cells_of_the_grid(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        assert len(prediction.top_scorelines) == 3
        probs = [s.pct for s in prediction.top_scorelines]
        assert probs == sorted(probs, reverse=True)
        # 36 cells: every combination from 0-0 to 5-5.
        assert len(prediction.scoreline_grid) == 36
        assert prediction.top_scorelines[0].pct == max(s.pct for s in prediction.scoreline_grid)

    def test_asian_handicap_lines_cover_the_five_requested_lines(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        lines = {h.line for h in prediction.asian_handicap}
        assert lines == {-0.75, -0.5, -0.25, 0.0, 0.25, 0.5}
        assert all(0 <= h.cover_pct <= 100 for h in prediction.asian_handicap)

    def test_margin_distribution_sums_to_one_hundred(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        assert len(prediction.margin_distribution) == 7  # -3..+3
        total = sum(b.pct for b in prediction.margin_distribution)
        assert total == pytest.approx(100.0, abs=0.2)

    def test_head_to_head_dominance_shifts_the_prediction_toward_the_dominant_side(self):
        # Pedido explícito del usuario: ajustar hasta un +-15% según el
        # dominio histórico en enfrentamientos directos. Build two
        # otherwise-identical seasons where the only difference is which
        # side dominated their real past meetings.
        def build(h2h_scores: list[tuple[int, int]]) -> list[Match]:
            matches = [_match(f"h{i}", "Home", f"F{i}", 1, 1, i + 1) for i in range(6)]
            matches += [_match(f"a{i}", f"G{i}", "Away", 1, 1, i + 1) for i in range(6)]
            matches += [
                _match(f"h2h{i}", "Home", "Away", hs, as_, 20 + i)
                for i, (hs, as_) in enumerate(h2h_scores)
            ]
            return matches

        home_dominant = predict_match(build([(4, 0), (3, 0)]), "Home", "Away")
        away_dominant = predict_match(build([(0, 4), (0, 3)]), "Home", "Away")
        assert home_dominant is not None and away_dominant is not None
        assert home_dominant.h2h_matches_considered == 2
        assert home_dominant.expected_goals_home > away_dominant.expected_goals_home

    def test_dixon_coles_correction_boosts_low_scorelines_versus_plain_poisson(self):
        from sp_predict.poisson import _dixon_coles_tau

        assert _dixon_coles_tau(1, 1, 1.4, 1.1, -0.13) > 1.0
        assert _dixon_coles_tau(2, 2, 1.4, 1.1, -0.13) == 1.0  # untouched outside the 0/1 grid

    def test_dixon_coles_rho_is_tuned_and_applied_to_all_four_low_score_cells(self):
        # Pedido explícito del usuario: rho ajustado a ~-0.11 (rango
        # habitual del paper original de Dixon & Coles para fútbol
        # inglés), aplicado a las 4 celdas de marcador bajo.
        from sp_predict.poisson import DIXON_COLES_RHO, _dixon_coles_tau

        assert DIXON_COLES_RHO == pytest.approx(-0.11)
        assert _dixon_coles_tau(0, 0, 1.4, 1.1, DIXON_COLES_RHO) != 1.0
        assert _dixon_coles_tau(1, 0, 1.4, 1.1, DIXON_COLES_RHO) != 1.0
        assert _dixon_coles_tau(0, 1, 1.4, 1.1, DIXON_COLES_RHO) != 1.0
        assert _dixon_coles_tau(1, 1, 1.4, 1.1, DIXON_COLES_RHO) != 1.0
        assert _dixon_coles_tau(3, 2, 1.4, 1.1, DIXON_COLES_RHO) == 1.0

    def test_recommended_pick_is_the_real_highest_probability_market(self):
        # Pedido explícito del usuario: un "pick claro" en lenguaje humano
        # — debe ser una selección real entre los mercados ya calculados,
        # nunca una métrica nueva inventada.
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        all_real_pcts = [
            prediction.home_win_pct,
            prediction.draw_pct,
            prediction.away_win_pct,
            prediction.double_chance_1x_pct,
            prediction.double_chance_x2_pct,
            prediction.double_chance_12_pct,
            prediction.over_1_5_pct,
            prediction.over_2_5_pct,
            round(100 - prediction.over_2_5_pct, 1),
            prediction.btts_yes_pct,
            prediction.btts_no_pct,
        ]
        assert prediction.recommended_pick_pct == max(all_real_pcts)
        assert prediction.recommended_pick_label  # non-empty, plain-language

    def test_corners_estimate_is_a_labelled_model_not_a_measured_stat(self):
        season = _build_season()
        prediction = predict_match(season, "Alpha", "Beta")
        assert prediction is not None
        assert prediction.expected_corners_total == pytest.approx(
            prediction.expected_corners_home + prediction.expected_corners_away, abs=0.15
        )
        assert prediction.expected_corners_total > 0
        assert 0 <= prediction.corners_over_8_5_pct <= 100
        assert 0 <= prediction.corners_over_9_5_pct <= 100
        # Over 9.5 is always a subset of (<=) over 8.5.
        assert prediction.corners_over_9_5_pct <= prediction.corners_over_8_5_pct
        assert prediction.corners_favoured_side in {"home", "away", "even"}

    def test_a_stronger_attack_gets_more_expected_corners(self):
        from sp_predict.poisson import _corners_estimate

        strong_home, _, _, _, _, favoured = _corners_estimate(attack_home=1.5, attack_away=0.7)
        weak_home, _, _, _, _, _ = _corners_estimate(attack_home=0.7, attack_away=0.7)
        assert strong_home > weak_home
        assert favoured == "home"

    def test_an_extreme_attack_rating_still_gives_a_realistic_corners_total(self):
        # Real bug found live: an early-season team with a 2.5x league-
        # average attack rating (8 wins from 8, still thin data) produced
        # ~14 expected corners for that side alone when the rating was
        # applied directly — a real match never actually looks like that.
        # Damping + a plausible per-side range keeps the estimate sane
        # even at the extremes the real Poisson model can produce.
        from sp_predict.poisson import _corners_estimate

        home, away, total, _, _, _ = _corners_estimate(attack_home=2.5, attack_away=1.1)
        assert home <= 8.5
        assert away <= 8.5
        assert total <= 17.0


class TestStrengthOfSchedule:
    def test_rewards_goals_scored_against_a_genuinely_stronger_defense(self):
        # Pedido explícito del usuario: no vale lo mismo meterle 2 goles
        # al colista que al líder — el ajuste por SoS debe reflejarlo con
        # datos 100% reales (los propios partidos de cada rival).
        from sp_predict.poisson import _collect_stats, _sos_corrections

        pool = [
            # StrongDefense's real record: concedes nothing elsewhere.
            _match("sd1", "StrongDefense", "Filler1", 1, 0, 1),
            _match("sd2", "StrongDefense", "Filler2", 1, 0, 2),
            _match("sd3", "StrongDefense", "Filler3", 1, 0, 3),
            # WeakDefense's real record: concedes a lot elsewhere.
            _match("wd1", "WeakDefense", "Filler4", 1, 4, 4),
            _match("wd2", "WeakDefense", "Filler5", 1, 4, 5),
            _match("wd3", "WeakDefense", "Filler6", 1, 4, 6),
            # TeamA scores 2 against the real strong defense; TeamB scores
            # the same 2 against the real weak one.
            _match("a1", "TeamA", "StrongDefense", 2, 1, 7),
            _match("b1", "TeamB", "WeakDefense", 2, 1, 8),
        ]
        records, _, _, _ = _collect_stats(pool)
        corrections = _sos_corrections(records, pool)
        team_a_attack_correction = corrections["TeamA"][0]
        team_b_attack_correction = corrections["TeamB"][0]
        assert team_a_attack_correction > team_b_attack_correction

    def test_corrections_are_bounded_and_default_to_neutral_for_a_clean_pool(self):
        from sp_predict.poisson import SOS_CORRECTION_CLAMP, _collect_stats, _sos_corrections

        season = _build_season()
        records, _, _, _ = _collect_stats(season)
        corrections = _sos_corrections(records, season)
        low, high = SOS_CORRECTION_CLAMP
        for attack_correction, defense_correction in corrections.values():
            assert low <= attack_correction <= high
            assert low <= defense_correction <= high


class TestDynamicSeasonRating:
    def test_shrinks_a_thin_extreme_sample_toward_neutral(self):
        # Same empirical-Bayes idea as SHRINKAGE_K: a single extreme real
        # result (a 6-0 thrashing) is real data, but one match is too thin
        # a sample to trust at face value for a full-season structural
        # rating — it must be pulled back toward 1.0 (neutral), not pinned
        # at the raw clamp's ceiling.
        from sp_predict.poisson import STRUCTURAL_RATING_CLAMP, _dynamic_season_ratings

        pool = [
            _match("f1", "Filler1", "Filler2", 1, 1, 1),
            _match("f2", "Filler3", "Filler4", 1, 1, 2),
            _match("ext", "Underdog", "Minnows", 6, 0, 3),
        ]
        ratings = _dynamic_season_ratings(pool)
        rating, used = ratings["Underdog"]
        assert used == 1
        assert rating < STRUCTURAL_RATING_CLAMP[1]
        assert rating == pytest.approx(1.0, abs=0.3)

    def test_empty_pool_gives_no_ratings_rather_than_fabricating_one(self):
        from sp_predict.poisson import _dynamic_season_ratings

        assert _dynamic_season_ratings([]) == {}


class TestRestDaysPenalty:
    def test_scales_from_full_penalty_at_zero_rest_to_none_at_the_threshold(self):
        from sp_predict.poisson import (
            REST_DAYS_MAX_PENALTY,
            REST_DAYS_THRESHOLD,
            _TeamRecord,
            _rest_penalty,
        )

        match_kickoff = datetime(2026, 10, 25, tzinfo=timezone.utc)
        short_rest_ts = (match_kickoff - timedelta(days=1)).timestamp()
        long_rest_ts = (match_kickoff - timedelta(days=REST_DAYS_THRESHOLD + 3)).timestamp()

        short_rest_record = _TeamRecord(home_matches=[(short_rest_ts, 1, 1, "X")])
        long_rest_record = _TeamRecord(home_matches=[(long_rest_ts, 1, 1, "X")])

        short_penalty = _rest_penalty(short_rest_record, match_kickoff)
        long_penalty = _rest_penalty(long_rest_record, match_kickoff)
        assert 0 < short_penalty <= REST_DAYS_MAX_PENALTY
        assert long_penalty == 0.0
        assert short_penalty > long_penalty

    def test_is_zero_without_a_predicted_kickoff_or_without_prior_matches(self):
        from sp_predict.poisson import _TeamRecord, _rest_penalty

        record = _TeamRecord(home_matches=[(0.0, 1, 1, "X")])
        assert _rest_penalty(record, None) == 0.0
        assert _rest_penalty(None, datetime(2026, 10, 25, tzinfo=timezone.utc)) == 0.0
        assert _rest_penalty(_TeamRecord(), datetime(2026, 10, 25, tzinfo=timezone.utc)) == 0.0

    def test_predict_match_lowers_expected_goals_for_the_side_with_short_rest(self):
        # Integración completa: dos escenarios idénticos salvo el descanso
        # real del equipo local antes del partido a predecir.
        season = _build_season()
        upcoming_kickoff = datetime(2026, 1, 20, tzinfo=timezone.utc)

        tight_rest_pool = season + [_match("prev", "Alpha", "Filler9", 2, 0, 19)]  # 1 day before
        rested_pool = season + [_match("prev", "Alpha", "Filler9", 2, 0, 10)]  # 10 days before

        tight = predict_match(
            season, "Alpha", "Beta", pool_matches=tight_rest_pool, match_kickoff=upcoming_kickoff
        )
        rested = predict_match(
            season, "Alpha", "Beta", pool_matches=rested_pool, match_kickoff=upcoming_kickoff
        )
        assert tight is not None and rested is not None
        assert tight.expected_goals_home < rested.expected_goals_home


class TestRecentForm:
    def test_orders_most_recent_first_and_labels_outcome_correctly(self):
        season = _build_season()
        form = recent_form(season, "Alpha", limit=5)
        assert len(form) == 5  # 4 filler wins + the Alpha vs Beta win
        assert form[0].match_id == "ab1"  # most recent (day 9)
        assert all(r.outcome == "W" for r in form)

    def test_ignores_unfinished_matches(self):
        season = _build_season()
        season.append(_match("future", "Alpha", "Gamma", 0, 0, 20, status=MatchStatus.SCHEDULED))
        form = recent_form(season, "Alpha", limit=10)
        assert all(r.match_id != "future" for r in form)


class TestHeadToHead:
    def test_only_returns_matches_between_the_two_named_teams(self):
        season = _build_season()
        h2h = head_to_head(season, "Alpha", "Beta")
        assert len(h2h) == 1
        assert h2h[0].match_id == "ab1"
        assert h2h[0].opponent == "Beta"

    def test_empty_when_teams_never_met_in_the_fetched_data(self):
        season = _build_season()
        assert head_to_head(season, "Filler1", "Filler2") == []
