import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MomentumChart from "@/components/MomentumChart";
import type { FormResult } from "@/lib/types";

function result(id: string, outcome: FormResult["outcome"]): FormResult {
  return {
    match_id: id,
    date: null,
    opponent: "X",
    venue: "home",
    goals_for: outcome === "W" ? 2 : 1,
    goals_against: outcome === "L" ? 2 : 1,
    outcome,
  };
}

describe("MomentumChart", () => {
  it("renders a real line per team from the actual W/D/L sequence", () => {
    const homeForm = [result("1", "W"), result("2", "W"), result("3", "D")];
    const awayForm = [result("4", "L"), result("5", "D")];
    const { container } = render(
      <MomentumChart homeLabel="Alpha" awayLabel="Beta" homeForm={homeForm} awayForm={awayForm} />
    );
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBe(2);
    // Real data, not an empty placeholder path.
    expect(paths[0].getAttribute("d")).not.toBe("");
    expect(paths[1].getAttribute("d")).not.toBe("");
  });

  it("renders nothing when neither team has real recent form", () => {
    const { container } = render(
      <MomentumChart homeLabel="Alpha" awayLabel="Beta" homeForm={[]} awayForm={[]} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
