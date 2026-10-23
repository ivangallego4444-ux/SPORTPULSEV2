import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RecommendedPickCard from "@/components/RecommendedPickCard";
import type { MatchPrediction } from "@/lib/types";

const basePrediction: MatchPrediction = {
  method: "test",
  confidence: "real_history",
  home_matches_used: 8,
  away_matches_used: 8,
  h2h_matches_considered: 0,
  h2h_adjustment_pct: 0,
  home_attack_rating: 1.2,
  home_defense_rating: 0.9,
  away_attack_rating: 0.8,
  away_defense_rating: 1.0,
  expected_goals_home: 1.8,
  expected_goals_away: 1.0,
  home_win_pct: 50,
  draw_pct: 28,
  away_win_pct: 22,
  double_chance_1x_pct: 78,
  double_chance_x2_pct: 50,
  double_chance_12_pct: 72,
  btts_yes_pct: 55,
  btts_no_pct: 45,
  over_1_5_pct: 70,
  over_2_5_pct: 50,
  over_3_5_pct: 20,
  top_scorelines: [],
  scoreline_grid: [],
  asian_handicap: [],
  margin_distribution: [],
  recommended_pick_label: "Doble oportunidad 1X (local o empate)",
  recommended_pick_pct: 78,
  expected_corners_home: 5.0,
  expected_corners_away: 4.0,
  expected_corners_total: 9.0,
  corners_over_8_5_pct: 55,
  corners_over_9_5_pct: 42,
  corners_favoured_side: "home",
  note: "test",
};

describe("RecommendedPickCard", () => {
  it("shows the real recommended pick label and percentage in plain language", () => {
    render(<RecommendedPickCard prediction={basePrediction} />);
    expect(screen.getByText("Doble oportunidad 1X (local o empate)")).toBeInTheDocument();
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("Confianza alta")).toBeInTheDocument();
  });

  it("warns when the pick leans on the league average", () => {
    const lowConfidence: MatchPrediction = { ...basePrediction, confidence: "league_average" };
    render(<RecommendedPickCard prediction={lowConfidence} />);
    expect(screen.getByText(/Estimación básica/)).toBeInTheDocument();
  });

  it("uses a lower confidence label for a middling percentage", () => {
    const middling: MatchPrediction = { ...basePrediction, recommended_pick_pct: 55 };
    render(<RecommendedPickCard prediction={middling} />);
    expect(screen.getByText("Confianza media")).toBeInTheDocument();
  });
});
