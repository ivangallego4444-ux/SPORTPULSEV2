"use client";

import { motion } from "framer-motion";

import { useTilt } from "@/lib/useTilt";
import type { Match, QuickPick } from "@/lib/types";

import CrestImage from "./CrestImage";

const STATUS_LABEL: Record<Match["status"], string> = {
  scheduled: "Próximo",
  live: "En juego",
  finished: "Finalizado",
  // Not "Aplazado" (postponed) — that's rarely what's actually true here.
  // This status means the real kickoff has already passed but neither
  // free data source has reported a result yet (see apps/api's
  // _demote_stale_scheduled_matches), so the match is still waiting on
  // its score, not necessarily rescheduled.
  unknown: "Resultado pendiente",
};

const STATUS_CLASSES: Record<Match["status"], string> = {
  scheduled: "bg-electric/15 text-electric-bright ring-1 ring-electric/30",
  live: "bg-emerald/15 text-emerald-bright ring-1 ring-emerald/30",
  finished: "bg-graphite-700 text-graphite-300",
  unknown: "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30",
};

function formatKickoff(kickoff: string | null): string {
  if (!kickoff) return "Fecha no disponible";
  const date = new Date(kickoff);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  // Explicit Europe/Madrid regardless of the viewing browser's own
  // timezone — real bug found live: without this, the same UTC kickoff
  // rendered at the wrong local hour (or even the wrong day) depending
  // on where the browser itself was set to.
  return new Intl.DateTimeFormat("es-ES", {
    timeZone: "Europe/Madrid",
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function MatchCard({
  match,
  onOpenDetail,
  index = 0,
  pick,
}: {
  match: Match;
  onOpenDetail?: (match: Match) => void;
  index?: number;
  pick?: QuickPick;
}) {
  const isTennis = match.sport === "tenis" && match.home !== null && match.away !== null;
  const hasStructuredScore = !isTennis && match.home !== null && match.away !== null;
  const clickable = Boolean(onOpenDetail);
  const { rotateX, rotateY, onMouseMove, onMouseLeave } = useTilt(6);

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 10) * 0.04, duration: 0.3 }}
      style={clickable ? { rotateX, rotateY, transformPerspective: 1000 } : undefined}
      onMouseMove={clickable ? onMouseMove : undefined}
      onMouseLeave={clickable ? onMouseLeave : undefined}
      whileHover={
        clickable
          ? {
              y: -3,
              boxShadow:
                "0 0 0 1px rgba(16,185,129,0.4), 0 12px 28px -8px rgba(16,185,129,0.35)",
              transition: { type: "spring", stiffness: 400, damping: 25 },
            }
          : undefined
      }
      onClick={clickable ? () => onOpenDetail!(match) : undefined}
      className={`rounded-xl border border-graphite-800 bg-graphite-900 p-4 shadow-card ${
        clickable ? "cursor-pointer" : ""
      }`}
    >
      <div className="flex items-center justify-between text-xs text-graphite-400">
        <span className="font-mono tabular-nums">{formatKickoff(match.kickoff)}</span>
        <span className={`rounded-full px-2 py-0.5 font-medium ${STATUS_CLASSES[match.status]}`}>
          {STATUS_LABEL[match.status]}
        </span>
      </div>

      {isTennis ? (
        <div className="mt-3">
          <div className="flex items-center justify-between gap-3">
            <span className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center font-semibold text-graphite-100">
              <CrestImage
                src={match.home_crest}
                alt=""
                className="h-11 w-11 shrink-0 rounded-full object-cover ring-2 ring-emerald/40"
              />
              <span className="w-full truncate text-xs sm:text-sm">{match.home}</span>
            </span>
            <span className="shrink-0 text-xs font-bold text-graphite-500">VS</span>
            <span className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center font-semibold text-graphite-100">
              <CrestImage
                src={match.away_crest}
                alt=""
                className="h-11 w-11 shrink-0 rounded-full object-cover ring-2 ring-electric/40"
              />
              <span className="w-full truncate text-xs sm:text-sm">{match.away}</span>
            </span>
          </div>
          {match.summary && (
            <p className="mt-2.5 text-center font-mono text-xs tabular-nums text-graphite-400">
              {match.summary}
            </p>
          )}
        </div>
      ) : hasStructuredScore ? (
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center font-semibold text-graphite-100">
            <CrestImage src={match.home_crest} alt="" className="h-10 w-10 shrink-0 object-contain" />
            <span className="w-full truncate text-xs sm:text-sm">{match.home}</span>
          </span>
          <span
            data-testid="score"
            className="shrink-0 rounded-lg bg-graphite-800 px-2.5 py-1 font-mono text-base tabular-nums text-graphite-100"
          >
            {match.home_score ?? "–"} : {match.away_score ?? "–"}
          </span>
          <span className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center font-semibold text-graphite-100">
            <CrestImage src={match.away_crest} alt="" className="h-10 w-10 shrink-0 object-contain" />
            <span className="w-full truncate text-xs sm:text-sm">{match.away}</span>
          </span>
        </div>
      ) : (
        <div className="mt-3">
          <p className="font-semibold text-graphite-100">
            {match.title ?? "Partido sin detalle estructurado"}
          </p>
          {match.summary && <p className="mt-1 text-sm text-graphite-400">{match.summary}</p>}
        </div>
      )}

      {pick && (
        <p className="mt-2.5 flex items-center justify-center gap-1.5 rounded-lg bg-emerald/10 px-2 py-1 text-center text-[11px] font-medium text-emerald-bright ring-1 ring-emerald/20">
          <span aria-hidden>⭐</span>
          {pick.label} · {pick.pct}%
        </p>
      )}

      {match.venue && <p className="mt-2 text-xs text-graphite-500">{match.venue}</p>}
    </motion.article>
  );
}
