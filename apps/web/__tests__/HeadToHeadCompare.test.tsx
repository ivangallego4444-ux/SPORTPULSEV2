import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HeadToHeadCompare from "@/components/HeadToHeadCompare";
import type { FormResult, MatchPrediction } from "@/lib/types";

function result(id: string, outcome: FormResult["outcome"], goalsFor: number, goalsAgainst: number): FormResult {
  return { match_id: id, date: null, opponent: "X", venue: "home", goals_for: goalsFor, goals_against: goalsAgainst, outcome };
}

const prediction: MatchPrediction = {
  method: "test",
  confidence: "real_history",
  home_matches_used: 5,
  away_matches_used: 5,
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
  expected_corners_home: 6.0,
  expected_corners_away: 3.5,
  expected_corners_total: 9.5,
  corners_over_8_5_pct: 55,
  corners_over_9_5_pct: 42,
  corners_favoured_side: "home",
  note: "test",
};

describe("HeadToHeadCompare", () => {
  it("summarizes real head-to-head dominance from the actual results", () => {
    const h2h = [result("1", "W", 2, 0), result("2", "W", 1, 0), result("3", "L", 0, 1)];
    render(
      <HeadToHeadCompare
        homeLabel="Alpha"
        awayLabel="Beta"
        homeForm={[result("h1", "W", 3, 1)]}
        awayForm={[result("a1", "L", 1, 3)]}
        headToHead={h2h}
        prediction={prediction}
      />
    );
    expect(screen.getByText(/Alpha domina el historial directo/)).toBeInTheDocument();
  });

  it("is honest when there is no real head-to-head data", () => {
    render(
      <HeadToHeadCompare
        homeLabel="Alpha"
        awayLabel="Beta"
        homeForm={[]}
        awayForm={[]}
        headToHead={[]}
        prediction={prediction}
      />
    );
    expect(
      screen.getByText("Sin enfrentamientos directos reales en los datos disponibles.")
    ).toBeInTheDocument();
  });
});
