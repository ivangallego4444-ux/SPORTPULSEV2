import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TopPicksGrid from "@/components/TopPicksGrid";
import type { HighlightMatch, Match, MatchPrediction } from "@/lib/types";

const baseMatch: Match = {
  id: "1",
  sport: "futbol",
  competition_slug: "laliga",
  competition_name: "LaLiga",
  status: "scheduled",
  kickoff: "2026-10-25T20:00:00Z",
  home: "Barcelona",
  away: "Real Madrid",
  home_id: "83",
  away_id: "86",
  home_crest: null,
  away_crest: null,
  home_score: null,
  away_score: null,
  live_minute: null,
  title: null,
  summary: null,
  venue: null,
  source: "thesportsdb",
};

const prediction: MatchPrediction = {
  method: "test",
  confidence: "real_history",
  home_matches_used: 4,
  away_matches_used: 4,
  h2h_matches_considered: 0,
  h2h_adjustment_pct: 0,
  home_attack_rating: 1.4,
  home_defense_rating: 0.8,
  away_attack_rating: 0.7,
  away_defense_rating: 1.2,
  expected_goals_home: 3.7,
  expected_goals_away: 1.1,
  home_win_pct: 82,
  draw_pct: 10,
  away_win_pct: 8,
  double_chance_1x_pct: 92,
  double_chance_x2_pct: 18,
  double_chance_12_pct: 90,
  btts_yes_pct: 64,
  btts_no_pct: 36,
  over_1_5_pct: 94,
  over_2_5_pct: 85,
  over_3_5_pct: 70,
  top_scorelines: [],
  scoreline_grid: [],
  asian_handicap: [],
  margin_distribution: [],
  recommended_pick_label: "Victoria local",
  recommended_pick_pct: 82,
  expected_corners_home: 6.5,
  expected_corners_away: 3.2,
  expected_corners_total: 9.7,
  corners_over_8_5_pct: 60,
  corners_over_9_5_pct: 45,
  corners_favoured_side: "home",
  note: "test",
};

describe("TopPicksGrid", () => {
  it("renders the real favourite team and percentage", () => {
    const highlights: HighlightMatch[] = [{ match: baseMatch, prediction }];
    render(<TopPicksGrid title="Favoritos" highlights={highlights} statKey="favorite" />);
    expect(screen.getByText("Gana Barcelona")).toBeInTheDocument();
  });

  it("shows an honest empty state instead of an empty grid", () => {
    render(<TopPicksGrid title="Favoritos" highlights={[]} statKey="favorite" />);
    expect(
      screen.getByText("Sin datos suficientes ahora mismo para calcular esto.")
    ).toBeInTheDocument();
  });
});
