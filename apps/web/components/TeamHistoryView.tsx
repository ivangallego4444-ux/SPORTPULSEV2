"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

import { fetchTeamHistory } from "@/lib/api";
import type { TeamHistory, TeamSummary } from "@/lib/types";

import CountUp from "./CountUp";
import CrestImage from "./CrestImage";
import EmptyState from "./EmptyState";
import { SkeletonGrid } from "./SkeletonCard";

const DEPTH_OPTIONS = [
  { label: "Últimos 10", value: 10 },
  { label: "Últimos 20", value: 20 },
  { label: "Últimos 30", value: 30 },
  { label: "Toda la temporada cargada", value: null },
];

const VENUE_OPTIONS: { label: string; value: "all" | "home" | "away" }[] = [
  { label: "Todos", value: "all" },
  { label: "Local", value: "home" },
  { label: "Visitante", value: "away" },
];

const OUTCOME_CLASSES: Record<string, string> = {
  W: "bg-emerald/20 text-emerald-bright ring-1 ring-emerald/40",
  D: "bg-graphite-700 text-graphite-300 ring-1 ring-graphite-600",
  L: "bg-red-500/15 text-red-300 ring-1 ring-red-500/30",
};

export default function TeamHistoryView({ team }: { team: TeamSummary }) {
  const [depth, setDepth] = useState<number | null>(20);
  const [venue, setVenue] = useState<"all" | "home" | "away">("all");
  const [history, setHistory] = useState<TeamHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(null);
    setError(null);
    fetchTeamHistory(team.competition_slug, team.team_id, venue, depth)
      .then(setHistory)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Error desconocido"));
  }, [team, depth, venue]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <CrestImage src={team.crest_url} alt="" className="h-10 w-10 object-contain" />
        <div>
          <h2 className="text-lg font-bold text-graphite-50">{team.team_name}</h2>
          <p className="text-xs text-graphite-500">{team.competition_name}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="flex flex-wrap gap-1.5">
          {DEPTH_OPTIONS.map((opt) => (
            <button
              key={opt.label}
              type="button"
              onClick={() => setDepth(opt.value)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                depth === opt.value
                  ? "bg-emerald/15 text-emerald-bright ring-1 ring-emerald/40"
                  : "bg-graphite-800 text-graphite-400 hover:text-graphite-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5">
          {VENUE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setVenue(opt.value)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                venue === opt.value
                  ? "bg-electric/15 text-electric-bright ring-1 ring-electric/40"
                  : "bg-graphite-800 text-graphite-400 hover:text-graphite-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {error && <EmptyState tone="error" title="No se ha podido cargar el historial" description={error} />}

      {!error && !history && <SkeletonGrid count={4} />}

      {history && !history.aggregate && (
        <EmptyState
          title="Sin partidos en este rango."
          description="No hay suficientes partidos reales cargados para este filtro todavía."
        />
      )}

      {history?.aggregate && (
        <>
          <motion.div
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.06 } } }}
            className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          >
            {[
              { label: "Partidos", value: history.aggregate.matches_played, suffix: "" },
              { label: "Goles a favor (med.)", value: history.aggregate.goals_for_avg, suffix: "" },
              { label: "Goles en contra (med.)", value: history.aggregate.goals_against_avg, suffix: "" },
              { label: "Ambos marcan", value: history.aggregate.btts_pct, suffix: "%" },
              { label: "Más de 1.5 goles", value: history.aggregate.over_1_5_pct, suffix: "%" },
              { label: "Más de 2.5 goles", value: history.aggregate.over_2_5_pct, suffix: "%" },
              { label: "Más de 3.5 goles", value: history.aggregate.over_3_5_pct, suffix: "%" },
              {
                label: "V-E-D",
                value: null,
                custom: `${history.aggregate.wins}-${history.aggregate.draws}-${history.aggregate.losses}`,
              },
            ].map((stat) => (
              <motion.div
                key={stat.label}
                variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
                className="rounded-xl border border-graphite-800 bg-graphite-900 p-3 text-center"
              >
                <p className="font-mono text-xl font-bold text-graphite-50">
                  {stat.custom ?? <CountUp value={stat.value!} decimals={stat.suffix ? 0 : 2} suffix={stat.suffix} />}
                </p>
                <p className="mt-1 text-[11px] text-graphite-500">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>

          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
              Partidos ({history.matches.length})
            </h3>
            <div className="space-y-1.5">
              {history.matches.map((m) => (
                <div
                  key={m.match_id}
                  className="flex items-center gap-3 rounded-lg border border-graphite-800 bg-graphite-900 px-3 py-2 text-sm"
                >
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded text-xs font-bold ${OUTCOME_CLASSES[m.outcome]}`}>
                    {m.outcome}
                  </span>
                  <span className="text-xs text-graphite-500">
                    {m.date
                      ? new Date(m.date).toLocaleDateString("es-ES", { timeZone: "Europe/Madrid" })
                      : "—"}
                  </span>
                  <span className="flex-1 truncate text-graphite-300">
                    {m.venue === "home" ? "vs" : "@"} {m.opponent}
                  </span>
                  <span className="font-mono text-graphite-100">
                    {m.goals_for}-{m.goals_against}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
