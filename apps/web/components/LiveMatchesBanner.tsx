"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

import { fetchLive } from "@/lib/api";
import { useCountdown } from "@/lib/useCountdown";
import type { Match } from "@/lib/types";

import CrestImage from "./CrestImage";
import MatchDetailModal from "./MatchDetailModal";

const POLL_INTERVAL_MS = 60_000;

function formatKickoffTime(kickoff: string | null): string {
  if (!kickoff) return "";
  const date = new Date(kickoff);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-ES", {
    timeZone: "Europe/Madrid",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function LiveMinuteBadge({ minute }: { minute: string | null }) {
  // Real source-given elapsed time (e.g. "63", "90+2", "HT") — never
  // estimated from kickoff. Falls back to a plain "EN DIRECTO" label on
  // the rare event the source gives a live status with no minute yet.
  return (
    <span className="flex items-center gap-1.5 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-bold text-red-300 ring-1 ring-red-500/40">
      <motion.span
        className="h-1.5 w-1.5 rounded-full bg-red-400"
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      />
      {minute ? `${minute}'` : "EN DIRECTO"}
    </span>
  );
}

function LiveMatchCard({ match, onOpen }: { match: Match; onOpen: (match: Match) => void }) {
  return (
    <motion.button
      type="button"
      onClick={() => onOpen(match)}
      whileHover={{ y: -2 }}
      className="flex w-64 shrink-0 flex-col gap-2 rounded-xl border border-red-500/20 bg-graphite-900 p-3 text-left shadow-card"
    >
      <div className="flex items-center justify-between">
        <span className="truncate text-[11px] font-medium text-graphite-500">{match.competition_name}</span>
        <LiveMinuteBadge minute={match.live_minute} />
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 text-sm font-semibold text-graphite-100">
          <CrestImage src={match.home_crest} alt="" className="h-5 w-5 shrink-0 object-contain" />
          <span className="truncate">{match.home}</span>
        </span>
        <span className="shrink-0 rounded-lg bg-graphite-800 px-2 py-0.5 font-mono text-sm text-graphite-100">
          {match.home_score ?? "–"}:{match.away_score ?? "–"}
        </span>
        <span className="flex min-w-0 items-center justify-end gap-1.5 text-right text-sm font-semibold text-graphite-100">
          <span className="truncate">{match.away}</span>
          <CrestImage src={match.away_crest} alt="" className="h-5 w-5 shrink-0 object-contain" />
        </span>
      </div>
    </motion.button>
  );
}

function NextUpBar({ matches, onOpen }: { matches: Match[]; onOpen: (match: Match) => void }) {
  const next = matches[0];
  const countdown = useCountdown(next?.kickoff ?? null);
  if (!next) return null;

  return (
    <div className="rounded-xl border border-graphite-800 bg-graphite-900 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-graphite-500">
          Próximos en empezar hoy
        </p>
        {countdown && !countdown.isPast && (
          <p className="font-mono text-xs text-graphite-400">
            Empieza en {String(countdown.hours).padStart(2, "0")}h {String(countdown.minutes).padStart(2, "0")}m
          </p>
        )}
      </div>
      <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
        {matches.map((match) => (
          <button
            key={match.id}
            type="button"
            onClick={() => onOpen(match)}
            className="flex shrink-0 items-center gap-2 rounded-lg bg-graphite-800 px-3 py-1.5 text-xs text-graphite-200 hover:bg-graphite-700"
          >
            <span className="font-mono text-graphite-400">{formatKickoffTime(match.kickoff)}</span>
            <span className="truncate">{match.home} - {match.away}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function LiveMatchesBanner({ sport }: { sport: string }) {
  const [live, setLive] = useState<Match[]>([]);
  const [upcomingToday, setUpcomingToday] = useState<Match[]>([]);
  const [detailMatch, setDetailMatch] = useState<Match | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = () => {
      fetchLive(sport)
        .then((res) => {
          if (cancelled) return;
          setLive(res.live);
          setUpcomingToday(res.upcoming_today);
        })
        .catch(() => {
          // A failed poll just keeps showing the last real data — never
          // flash an error over a banner that already has something
          // real on screen.
        });
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [sport]);

  if (live.length === 0 && upcomingToday.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      {live.length > 0 ? (
        <>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-red-300">
            <span className="h-2 w-2 rounded-full bg-red-400" />
            En directo ahora
          </p>
          <div className="flex gap-3 overflow-x-auto pb-1">
            {live.map((match) => (
              <LiveMatchCard key={match.id} match={match} onOpen={setDetailMatch} />
            ))}
          </div>
        </>
      ) : (
        <NextUpBar matches={upcomingToday} onOpen={setDetailMatch} />
      )}

      <MatchDetailModal
        match={detailMatch}
        competitionSlug={detailMatch?.competition_slug ?? ""}
        onClose={() => setDetailMatch(null)}
      />
    </div>
  );
}
