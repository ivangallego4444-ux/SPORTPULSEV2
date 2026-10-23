"use client";

import { motion } from "framer-motion";

import { useCountdown } from "@/lib/useCountdown";
import type { HighlightMatch } from "@/lib/types";

import CountUp from "./CountUp";
import CrestImage from "./CrestImage";

function formatKickoff(kickoff: string | null): string {
  if (!kickoff) return "";
  const date = new Date(kickoff);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-ES", {
    timeZone: "Europe/Madrid",
    weekday: "long",
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function CountdownUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="font-mono text-2xl font-bold text-graphite-50 sm:text-3xl">
        {String(value).padStart(2, "0")}
      </span>
      <span className="text-[10px] uppercase tracking-wide text-graphite-500">{label}</span>
    </div>
  );
}

export default function FeaturedMatch({ highlight }: { highlight: HighlightMatch | null }) {
  const countdown = useCountdown(highlight?.match.kickoff ?? null);

  if (!highlight) {
    return null;
  }

  const { match, prediction } = highlight;

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="gradient-border relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#062c1f] via-graphite-900 to-graphite-950 p-6 shadow-card sm:p-8"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 38px, rgba(255,255,255,0.4) 39px), repeating-linear-gradient(90deg, transparent, transparent 38px, rgba(255,255,255,0.4) 39px)",
        }}
      />

      <p className="relative text-xs font-semibold uppercase tracking-widest text-emerald-bright">
        Partido del día · {match.competition_name}
      </p>

      <div className="relative mt-4 flex items-center justify-center gap-4 sm:gap-10">
        <div className="flex flex-1 flex-col items-center gap-2 text-center">
          <CrestImage src={match.home_crest} alt="" className="h-16 w-16 object-contain sm:h-20 sm:w-20" />
          <span className="text-sm font-bold text-graphite-50 sm:text-lg">{match.home}</span>
        </div>

        <div className="flex shrink-0 flex-col items-center gap-2">
          {countdown && !countdown.isPast ? (
            <div className="flex gap-2 sm:gap-3">
              <CountdownUnit value={countdown.days} label="días" />
              <span className="text-2xl text-graphite-600">:</span>
              <CountdownUnit value={countdown.hours} label="horas" />
              <span className="text-2xl text-graphite-600">:</span>
              <CountdownUnit value={countdown.minutes} label="min" />
            </div>
          ) : (
            <span className="text-xl font-bold text-graphite-400">VS</span>
          )}
          <span className="text-xs text-graphite-500">{formatKickoff(match.kickoff)}</span>
        </div>

        <div className="flex flex-1 flex-col items-center gap-2 text-center">
          <CrestImage src={match.away_crest} alt="" className="h-16 w-16 object-contain sm:h-20 sm:w-20" />
          <span className="text-sm font-bold text-graphite-50 sm:text-lg">{match.away}</span>
        </div>
      </div>

      {prediction && (
        <div className="relative mt-6">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-graphite-800/80">
            <motion.div
              className="h-full bg-emerald"
              initial={{ width: 0 }}
              animate={{ width: `${prediction.home_win_pct}%` }}
              transition={{ duration: 0.7, ease: "easeOut" }}
            />
            <motion.div
              className="h-full bg-graphite-500"
              initial={{ width: 0 }}
              animate={{ width: `${prediction.draw_pct}%` }}
              transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
            />
            <motion.div
              className="h-full bg-electric"
              initial={{ width: 0 }}
              animate={{ width: `${prediction.away_win_pct}%` }}
              transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
            />
          </div>
          <div className="mt-1.5 flex justify-between font-mono text-sm">
            <span className="text-emerald-bright">
              <CountUp value={prediction.home_win_pct} decimals={0} suffix="%" />
            </span>
            <span className="text-graphite-500">
              <CountUp value={prediction.draw_pct} decimals={0} suffix="%" />
            </span>
            <span className="text-electric-bright">
              <CountUp value={prediction.away_win_pct} decimals={0} suffix="%" />
            </span>
          </div>
          <p className="mt-2 text-center text-xs text-graphite-500">
            Probabilidad estadística real, calculada con {prediction.home_matches_used} partidos
            reales de {match.home} como local y {prediction.away_matches_used} de {match.away} como
            visitante.
          </p>
        </div>
      )}
    </motion.section>
  );
}
