import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MatchCard from "@/components/MatchCard";
import type { Match } from "@/lib/types";

const baseMatch: Match = {
  id: "1",
  sport: "futbol",
  competition_slug: "bundesliga",
  competition_name: "1. Bundesliga",
  status: "finished",
  kickoff: "2026-10-17T15:30:00",
  home: "FC Schalke 04",
  away: "1. FSV Mainz 05",
  home_id: "9",
  away_id: "81",
  home_crest: null,
  away_crest: null,
  home_score: 0,
  away_score: 1,
  live_minute: null,
  title: null,
  summary: null,
  venue: null,
  source: "openligadb",
};

describe("MatchCard", () => {
  it("renders structured team names and the real score", () => {
    render(<MatchCard match={baseMatch} />);
    expect(screen.getByText("FC Schalke 04")).toBeInTheDocument();
    expect(screen.getByText("1. FSV Mainz 05")).toBeInTheDocument();
    expect(screen.getByText(/0 : 1/)).toBeInTheDocument();
    expect(screen.getByText("Finalizado")).toBeInTheDocument();
  });

  it("never fabricates a score split for unstructured (tennis) matches", () => {
    const tennisMatch: Match = {
      ...baseMatch,
      id: "2",
      sport: "tenis",
      home: null,
      away: null,
      home_score: null,
      away_score: null,
      title: "Wimbledon Sinner vs Zverev",
      summary: "Sinner beat Zverev 3-1",
    };
    render(<MatchCard match={tennisMatch} />);
    expect(screen.getByText("Wimbledon Sinner vs Zverev")).toBeInTheDocument();
    expect(screen.getByText("Sinner beat Zverev 3-1")).toBeInTheDocument();
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();
  });

  it("renders real crest images when the source provides them", () => {
    const withCrests: Match = {
      ...baseMatch,
      home_crest: "https://example.com/schalke.png",
      away_crest: "https://example.com/mainz.png",
    };
    const { container } = render(<MatchCard match={withCrests} />);
    const images = container.querySelectorAll("img");
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute("src", "https://example.com/schalke.png");
  });

  it("shows an explicit label instead of a blank date when kickoff is missing", () => {
    render(<MatchCard match={{ ...baseMatch, kickoff: null }} />);
    expect(screen.getByText("Fecha no disponible")).toBeInTheDocument();
  });
});
