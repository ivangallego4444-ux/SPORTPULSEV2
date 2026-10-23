import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import KeyFactorsCard from "@/components/KeyFactorsCard";
import type { MatchPrediction } from "@/lib/types";

const basePrediction: MatchPrediction = {
  method: "test",
  confidence: "real_history",
  home_matches_used: 8,
  away_matches_used: 8,
  h2h_matches_considered: 2,
  h2h_adjustment_pct: 7.5,
  home_attack_rating: 1.3,
  home_defense_rating: 0.85,
  away_attack_rating: 0.7,
  away_defense_rating: 1.1,
  expected_goals_home: 2.0,
  expected_goals_away: 0.9,
  home_win_pct: 60,
  draw_pct: 25,
  away_win_pct: 15,
  double_chance_1x_pct: 85,
  double_chance_x2_pct: 40,
  double_chance_12_pct: 75,
  btts_yes_pct: 40,
  btts_no_pct: 60,
  over_1_5_pct: 70,
  over_2_5_pct: 50,
  over_3_5_pct: 20,
  top_scorelines: [],
  scoreline_grid: [],
  asian_handicap: [],
  margin_distribution: [],
  recommended_pick_label: "Doble oportunidad 1X (local o empate)",
  recommended_pick_pct: 85,
  expected_corners_home: 5.0,
  expected_corners_away: 4.0,
  expected_corners_total: 9.0,
  corners_over_8_5_pct: 55,
  corners_over_9_5_pct: 42,
  corners_favoured_side: "home",
  note: "test",
};

describe("KeyFactorsCard", () => {
  it("shows the real attack/defense ratings and which side the h2h record favours", () => {
    render(<KeyFactorsCard prediction={basePrediction} homeLabel="Alpha" awayLabel="Beta" />);
    expect(screen.getByText("1.30×")).toBeInTheDocument();
    expect(screen.getByText(/favorece a/)).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
  });

  it("is honest when there is no real head-to-head history", () => {
    const noH2h: MatchPrediction = { ...basePrediction, h2h_matches_considered: 0, h2h_adjustment_pct: 0 };
    render(<KeyFactorsCard prediction={noH2h} homeLabel="Alpha" awayLabel="Beta" />);
    expect(
      screen.getByText("Sin enfrentamientos directos reales en los datos disponibles.")
    ).toBeInTheDocument();
  });
});
