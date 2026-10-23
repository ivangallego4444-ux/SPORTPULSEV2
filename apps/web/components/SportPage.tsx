"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

import { fetchCompetitions } from "@/lib/api";
import type { Competition } from "@/lib/types";

import CompetitionNavigator from "./CompetitionNavigator";
import CompetitionSection from "./CompetitionSection";
import EmptyState from "./EmptyState";
import LiveMatchesBanner from "./LiveMatchesBanner";

export default function SportPage({ sport, title }: { sport: string; title: string }) {
  const [competitions, setCompetitions] = useState<Competition[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCompetitions(sport)
      .then((comps) => {
        setCompetitions(comps);
        setSelected(comps[0]?.slug ?? null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Error desconocido");
      });
  }, [sport]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-5 text-2xl font-extrabold text-graphite-50">{title}</h1>

      {sport === "futbol" && <LiveMatchesBanner sport={sport} />}

      {error && (
        <EmptyState
          tone="error"
          title="No se ha podido conectar con la API"
          description={error}
        />
      )}

      {!error && competitions === null && (
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-8 w-28 animate-shimmer rounded-full" />
          ))}
        </div>
      )}

      {competitions && competitions.length === 0 && (
        <EmptyState
          title={`Todavía no hay una fuente de datos verificada para ${title.toLowerCase()}.`}
        />
      )}

      {competitions && competitions.length > 0 && selected && (
        <>
          {competitions.length > 4 ? (
            <CompetitionNavigator competitions={competitions} selected={selected} onSelect={setSelected} />
          ) : competitions.length > 1 ? (
            <div className="mb-5 flex flex-wrap gap-2">
              {competitions.map((competition) => {
                const active = selected === competition.slug;
                return (
                  <button
                    key={competition.slug}
                    type="button"
                    onClick={() => setSelected(competition.slug)}
                    className="relative rounded-full px-3 py-1.5 text-sm font-medium text-graphite-400 transition-colors hover:text-graphite-100"
                  >
                    {active && (
                      <motion.span
                        layoutId={`tab-pill-${sport}`}
                        className="absolute inset-0 rounded-full bg-emerald/15 ring-1 ring-emerald/40"
                        transition={{ type: "spring", stiffness: 500, damping: 35 }}
                      />
                    )}
                    <span className={`relative ${active ? "text-emerald-bright" : ""}`}>
                      {competition.name}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : null}
          <CompetitionSection slug={selected} />
        </>
      )}
    </div>
  );
}
