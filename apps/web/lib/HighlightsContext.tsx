"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { fetchHomeHighlights } from "./api";
import type { HomeHighlights } from "./types";

interface HighlightsState {
  data: HomeHighlights | null;
  loading: boolean;
  error: string | null;
  latencyMs: number | null;
  lastUpdated: Date | null;
  refresh: () => void;
}

const HighlightsContext = createContext<HighlightsState | null>(null);

export function HighlightsProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<HomeHighlights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const inFlight = useRef(false);

  const load = useCallback(() => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    const start = performance.now();
    fetchHomeHighlights()
      .then((result) => {
        setLatencyMs(Math.round(performance.now() - start));
        setData(result);
        setLastUpdated(new Date());
        setError(null);
      })
      .catch((err: unknown) => {
        setLatencyMs(Math.round(performance.now() - start));
        setError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => {
        setLoading(false);
        inFlight.current = false;
      });
  }, []);

  useEffect(() => {
    load();
    // One fetch per session on mount — no auto-polling. TheSportsDB's
    // free tier rate-limits bursts (confirmed repeatedly building this),
    // so refreshing is an explicit user action (see the "Sincronizar"
    // control), never a timer hammering the API in the background.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <HighlightsContext.Provider value={{ data, loading, error, latencyMs, lastUpdated, refresh: load }}>
      {children}
    </HighlightsContext.Provider>
  );
}

export function useHighlights(): HighlightsState {
  const ctx = useContext(HighlightsContext);
  if (!ctx) throw new Error("useHighlights debe usarse dentro de HighlightsProvider");
  return ctx;
}
