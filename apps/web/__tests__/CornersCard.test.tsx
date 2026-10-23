import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CornersCard from "@/components/CornersCard";
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
  asian_handicap: [],
  margin_distribution: [],
  recommended_pick_label: "test",
  recommended_pick_pct: 78,
  expected_corners_home: 6.2,
  expected_corners_away: 3.5,
  expected_corners_total: 9.7,
  corners_over_8_5_pct: 62,
  corners_over_9_5_pct: 48,
  corners_favoured_side: "home",
  note: "test",
};

describe("CornersCard", () => {
  it("shows the real corners estimate, clearly labelled as a model", () => {
    render(<CornersCard prediction={prediction} homeLabel="Alpha" awayLabel="Beta" />);
    expect(screen.getByText("9.7")).toBeInTheDocument();
    expect(screen.getByText("6.2")).toBeInTheDocument();
    expect(screen.getByText("3.5")).toBeInTheDocument();
    expect(screen.getByText("El local sacará más córners")).toBeInTheDocument();
    expect(screen.getByText(/no un dato oficial/)).toBeInTheDocument();
  });
});
