"use client";

import { motion } from "framer-motion";

import type { Competition, Match } from "@/lib/types";

import CrestImage from "./CrestImage";

function formatKickoffShort(kickoff: string | null): string {
  if (!kickoff) return "";
  const date = new Date(kickoff);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-ES", {
    timeZone: "Europe/Madrid",
    weekday: "short",
    day: "2-digit",
    month: "short",
  }).format(date);
}

export default function LeagueHeroHeader({
  competition,
  matches,
}: {
  competition: Competition;
  matches: Match[];
}) {
  const finished = matches.filter(
    (m) => m.status === "finished" && m.home_score !== null && m.away_score !== null
  );
  const totalGoals = finished.reduce((sum, m) => sum + (m.home_score ?? 0) + (m.away_score ?? 0), 0);
  const avgGoals = finished.length > 0 ? totalGoals / finished.length : null;
  const scoreUnitLabel = competition.sport === "baloncesto" ? "Puntos / partido" : "Goles / partido";

  const upcoming = matches
    .filter((m) => m.status === "scheduled" && m.kickoff && m.home && m.away)
    .sort((a, b) => new Date(a.kickoff as string).getTime() - new Date(b.kickoff as string).getTime());
  const featured = upcoming[0] ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="relative overflow-hidden rounded-2xl border border-graphite-800 bg-gradient-to-br from-[#0d2a20] via-graphite-900 to-graphite-950 p-5 shadow-card sm:p-6"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 34px, rgba(255,255,255,0.5) 35px), repeating-linear-gradient(90deg, transparent, transparent 34px, rgba(255,255,255,0.5) 35px)",
        }}
      />

      <div className="relative flex items-center gap-4">
        {competition.badge_url ? (
          <CrestImage
            src={competition.badge_url}
            alt=""
            className="h-14 w-14 shrink-0 object-contain drop-shadow-lg"
          />
        ) : (
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-graphite-800 text-xl font-bold text-graphite-400 ring-1 ring-graphite-700">
            {competition.name.slice(0, 1)}
          </div>
        )}
        <div className="min-w-0">
          <h2 className="truncate text-xl font-extrabold text-graphite-50 sm:text-2xl">
            {competition.name}
          </h2>
          {competition.country && <p className="text-xs text-graphite-500">{competition.country}</p>}
        </div>
      </div>

      <div className="relative mt-5 grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-graphite-800 bg-graphite-900/60 p-3 text-center">
          <p className="font-mono text-lg font-bold text-graphite-50 sm:text-xl">{finished.length}</p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-graphite-500">Partidos jugados</p>
        </div>
        <div className="rounded-xl border border-graphite-800 bg-graphite-900/60 p-3 text-center">
          <p className="font-mono text-lg font-bold text-emerald-bright sm:text-xl">
            {avgGoals !== null ? avgGoals.toFixed(2) : "–"}
          </p>
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-graphite-500">{scoreUnitLabel}</p>
        </div>
        <div className="rounded-xl border border-graphite-800 bg-graphite-900/60 p-3 text-center">
          {featured ? (
            <>
              <p className="truncate text-xs font-semibold text-graphite-100">
                {featured.home} - {featured.away}
              </p>
              <p className="mt-0.5 text-[10px] text-graphite-500">{formatKickoffShort(featured.kickoff)}</p>
            </>
          ) : (
            <p className="text-xs text-graphite-500">Sin partido destacado</p>
          )}
          <p className="mt-0.5 text-[10px] uppercase tracking-wide text-graphite-500">Partido destacado</p>
        </div>
      </div>
    </motion.div>
  );
}
