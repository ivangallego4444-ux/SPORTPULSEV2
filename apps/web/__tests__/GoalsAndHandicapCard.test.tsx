import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import GoalsAndHandicapCard from "@/components/GoalsAndHandicapCard";
import type { MatchPrediction } from "@/lib/types";

const prediction: MatchPrediction = {
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
  asian_handicap: [
    { line: -0.75, cover_pct: 40 },
    { line: -0.5, cover_pct: 48 },
    { line: -0.25, cover_pct: 55 },
    { line: 0.0, cover_pct: 62 },
    { line: 0.25, cover_pct: 68 },
    { line: 0.5, cover_pct: 74 },
  ],
  margin_distribution: [],
  recommended_pick_label: "test",
  recommended_pick_pct: 78,
  expected_corners_home: 5.0,
  expected_corners_away: 4.0,
  expected_corners_total: 9.0,
  corners_over_8_5_pct: 55,
  corners_over_9_5_pct: 42,
  corners_favoured_side: "home",
  note: "test",
};

describe("GoalsAndHandicapCard", () => {
  it("renders the real goal markets and the three simplified handicap lines in plain Spanish", () => {
    render(<GoalsAndHandicapCard prediction={prediction} />);
    expect(screen.getByText("Más de 1.5 goles")).toBeInTheDocument();
    expect(screen.getByText("Más de 2.5 goles")).toBeInTheDocument();
    expect(screen.getByText("Ambos equipos marcan")).toBeInTheDocument();
    expect(screen.getByText("Hándicap -0.5 (local gana el partido o cubre el margen)")).toBeInTheDocument();
    expect(screen.getByText("Hándicap 0.0 (empate = apuesta no válida)")).toBeInTheDocument();
    expect(screen.getByText("Hándicap +0.5 (local gana, empata o pierde por poco)")).toBeInTheDocument();
  });
});
