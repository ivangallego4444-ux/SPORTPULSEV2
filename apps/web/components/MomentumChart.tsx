"use client";

import { motion } from "framer-motion";

import type { FormResult } from "@/lib/types";

const WIDTH = 280;
const HEIGHT = 90;
const PAD = 10;

/** Real points-per-game (W=3, D=1, L=0) from each team's own last N real
 * results — the same `FormResult` data behind the W/D/L strip, just
 * plotted match-by-match instead of as a strip, oldest to newest. */
function toPoints(outcome: FormResult["outcome"]): number {
  return outcome === "W" ? 3 : outcome === "D" ? 1 : 0;
}

function buildPath(results: FormResult[]): string {
  // recent_form() returns most-recent-first; plot oldest -> newest left to right.
  const oldestFirst = [...results].reverse();
  const n = oldestFirst.length;
  if (n === 0) return "";
  const stepX = n > 1 ? (WIDTH - PAD * 2) / (n - 1) : 0;
  return oldestFirst
    .map((r, i) => {
      const x = PAD + i * stepX;
      const y = PAD + (1 - toPoints(r.outcome) / 3) * (HEIGHT - PAD * 2);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function MomentumChart({
  homeLabel,
  awayLabel,
  homeForm,
  awayForm,
}: {
  homeLabel: string;
  awayLabel: string;
  homeForm: FormResult[];
  awayForm: FormResult[];
}) {
  if (homeForm.length === 0 && awayForm.length === 0) return null;

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }}>
        {[0, 1, 3].map((pts) => {
          const y = PAD + (1 - pts / 3) * (HEIGHT - PAD * 2);
          return (
            <line
              key={pts}
              x1={PAD}
              y1={y}
              x2={WIDTH - PAD}
              y2={y}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth={1}
            />
          );
        })}
        <motion.path
          d={buildPath(awayForm)}
          fill="none"
          stroke="#00f0ff"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
        <motion.path
          d={buildPath(homeForm)}
          fill="none"
          stroke="#00ff88"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        />
      </svg>
      <div className="mt-1 flex items-center justify-between text-[10px] text-graphite-600">
        <span>Más antiguo</span>
        <span>Más reciente</span>
      </div>
      <div className="mt-1 flex gap-4 text-[10px]">
        <span className="flex items-center gap-1 text-neon-emerald">
          <span className="h-1.5 w-1.5 rounded-full bg-neon-emerald" /> {homeLabel}
        </span>
        <span className="flex items-center gap-1 text-neon-cyan">
          <span className="h-1.5 w-1.5 rounded-full bg-neon-cyan" /> {awayLabel}
        </span>
      </div>
      <p className="mt-1 text-[10px] text-graphite-600">
        Puntos reales por partido (victoria=3, empate=1, derrota=0) en los últimos{" "}
        {Math.max(homeForm.length, awayForm.length)} partidos de cada equipo.
      </p>
    </div>
  );
}
