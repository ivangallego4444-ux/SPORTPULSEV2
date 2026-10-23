import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StandingsTable from "@/components/StandingsTable";
import type { StandingRow } from "@/lib/types";

const rows: StandingRow[] = [
  {
    rank: 1,
    team: "FC Bayern München",
    played: 6,
    wins: 4,
    draws: 2,
    losses: 0,
    points: 14,
    crest_url: null,
  },
];

describe("StandingsTable", () => {
  it("renders real standings rows with their actual points", () => {
    render(<StandingsTable rows={rows} />);
    expect(screen.getByText("FC Bayern München")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("shows a dash instead of a fabricated number for missing fields", () => {
    render(
      <StandingsTable
        rows={[{ ...rows[0], played: null, wins: null, draws: null, losses: null }]}
      />
    );
    expect(screen.getAllByText("–")).toHaveLength(4);
  });
});
