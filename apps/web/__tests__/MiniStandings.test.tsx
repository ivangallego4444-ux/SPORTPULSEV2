import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MiniStandings from "@/components/MiniStandings";
import type { StandingRow } from "@/lib/types";

const rows: StandingRow[] = [
  {
    rank: 1,
    team: "Barcelona",
    played: 9,
    wins: 9,
    draws: 0,
    losses: 0,
    points: 27,
    crest_url: null,
  },
];

describe("MiniStandings", () => {
  it("renders real rows with the competition name and points", () => {
    render(<MiniStandings competitionName="LaLiga" rows={rows} />);
    expect(screen.getByText("LaLiga")).toBeInTheDocument();
    expect(screen.getByText("Barcelona")).toBeInTheDocument();
    expect(screen.getByText("27")).toBeInTheDocument();
  });
});
