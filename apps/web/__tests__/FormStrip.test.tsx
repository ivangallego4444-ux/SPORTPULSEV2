import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import FormStrip from "@/components/FormStrip";
import type { FormResult } from "@/lib/types";

const results: FormResult[] = [
  {
    match_id: "1",
    date: "2026-10-18T00:00:00Z",
    opponent: "Sevilla",
    venue: "home",
    goals_for: 4,
    goals_against: 1,
    outcome: "W",
  },
  {
    match_id: "2",
    date: "2026-10-11T00:00:00Z",
    opponent: "Valencia",
    venue: "away",
    goals_for: 1,
    goals_against: 1,
    outcome: "D",
  },
];

describe("FormStrip", () => {
  it("renders one badge per real result with the real outcome letter", () => {
    render(<FormStrip teamName="Real Madrid" results={results} />);
    expect(screen.getByText("Real Madrid")).toBeInTheDocument();
    expect(screen.getByText("W")).toBeInTheDocument();
    expect(screen.getByText("D")).toBeInTheDocument();
  });

  it("shows an explicit message instead of empty space when there's no data", () => {
    render(<FormStrip teamName="Real Madrid" results={[]} />);
    expect(
      screen.getByText("Sin partidos recientes disponibles en esta fuente.")
    ).toBeInTheDocument();
  });
});
