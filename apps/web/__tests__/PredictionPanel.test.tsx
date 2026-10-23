import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PredictionPanel from "@/components/PredictionPanel";
import type { MatchPrediction } from "@/lib/types";

const prediction: MatchPrediction = {
  method: "Poisson simple",
  confidence: "real_history",
  home_matches_used: 5,
  away_matches_used: 4,
  h2h_matches_considered: 0,
  h2h_adjustment_pct: 0,
  home_attack_rating: 1.1,
  home_defense_rating: 0.9,
  away_attack_rating: 0.8,
  away_defense_rating: 1.1,
  expected_goals_home: 2.1,
  expected_goals_away: 0.8,
  home_win_pct: 68,
  draw_pct: 22,
  away_win_pct: 10,
  double_chance_1x_pct: 90,
  double_chance_x2_pct: 32,
  double_chance_12_pct: 78,
  btts_yes_pct: 35,
  btts_no_pct: 65,
  over_1_5_pct: 70,
  over_2_5_pct: 48,
  over_3_5_pct: 25,
  top_scorelines: [
    { home_goals: 2, away_goals: 0, pct: 12 },
    { home_goals: 1, away_goals: 0, pct: 10 },
    { home_goals: 2, away_goals: 1, pct: 8 },
  ],
  scoreline_grid: [],
  asian_handicap: [],
  margin_distribution: [],
  recommended_pick_label: "Doble oportunidad 1X (local o empate)",
  recommended_pick_pct: 90,
  expected_corners_home: 5.8,
  expected_corners_away: 3.9,
  expected_corners_total: 9.7,
  corners_over_8_5_pct: 62,
  corners_over_9_5_pct: 48,
  corners_favoured_side: "home",
  note: "Calculado con datos reales, no una cuota de casa de apuestas.",
};

describe("PredictionPanel", () => {
  it("renders the real computed percentages, not placeholders", () => {
    render(
      <PredictionPanel prediction={prediction} note={null} homeTeam="Alpha" awayTeam="Beta" />
    );
    expect(screen.getByText("68%")).toBeInTheDocument();
    expect(screen.getByText("10%")).toBeInTheDocument();
    expect(screen.getByText(/no una cuota de casa de apuestas/)).toBeInTheDocument();
    expect(screen.queryByText("⚠ Estimación básica")).not.toBeInTheDocument();
  });

  it("shows a confidence warning when the prediction leans on the league average", () => {
    const lowConfidence: MatchPrediction = { ...prediction, confidence: "league_average" };
    render(
      <PredictionPanel prediction={lowConfidence} note={null} homeTeam="Alpha" awayTeam="Beta" />
    );
    expect(screen.getByText("⚠ Estimación básica")).toBeInTheDocument();
  });

  it("shows the honest unavailable message instead of fabricating a prediction", () => {
    render(
      <PredictionPanel
        prediction={null}
        note="Muestra insuficiente en la fuente gratuita."
        homeTeam="Alpha"
        awayTeam="Beta"
      />
    );
    expect(screen.getByText("Sin predicción para este partido")).toBeInTheDocument();
    expect(screen.getByText("Muestra insuficiente en la fuente gratuita.")).toBeInTheDocument();
  });
});
