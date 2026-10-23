import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import EmptyState from "@/components/EmptyState";

describe("EmptyState", () => {
  it("renders the title and optional description", () => {
    render(<EmptyState title="Sin datos" description="La fuente no tiene esta información." />);
    expect(screen.getByText("Sin datos")).toBeInTheDocument();
    expect(screen.getByText("La fuente no tiene esta información.")).toBeInTheDocument();
  });

  it("renders without a description", () => {
    render(<EmptyState title="Cargando…" />);
    expect(screen.getByText("Cargando…")).toBeInTheDocument();
  });
});
