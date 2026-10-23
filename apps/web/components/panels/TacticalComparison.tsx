"use client";

import { motion } from "framer-motion";

import { useTilt } from "@/lib/useTilt";
import type { HighlightMatch } from "@/lib/types";

import CrestImage from "../CrestImage";

/** A real-data comparison (expected goals from the Poisson model) drawn
 * as two 3D-tilted force bars over a laser grid — not a literal
 * pitch/positional map, since we have no positional data to show
 * honestly. */
export default function TacticalComparison({ highlight }: { highlight: HighlightMatch }) {
  const { rotateX, rotateY, onMouseMove, onMouseLeave } = useTilt(10);
  const prediction = highlight.prediction;
  if (!prediction) return null;

  const total = prediction.expected_goals_home + prediction.expected_goals_away || 1;
  const homePct = (prediction.expected_goals_home / total) * 100;

  return (
    <motion.div
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{ rotateX, rotateY, transformPerspective: 1400 }}
      className="gradient-border relative overflow-hidden rounded-xl border border-neon-cyan/15 bg-obsidian/60 p-4"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.12]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 13px, rgba(0,240,255,0.5) 14px), repeating-linear-gradient(90deg, transparent, transparent 13px, rgba(0,240,255,0.5) 14px)",
        }}
      />
      <p className="relative mb-3 text-center text-[11px] uppercase tracking-wide text-graphite-500">
        Fuerza ofensiva estimada (xG real del modelo)
      </p>
      <div className="relative flex h-28 items-end justify-center gap-6" style={{ perspective: "1400px" }}>
        <div className="flex flex-col items-center gap-1.5">
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: `${Math.max(homePct, 8)}%` }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            style={{ transform: "rotateX(35deg) rotateZ(-6deg) translateZ(10px)", transformStyle: "preserve-3d" }}
            className="w-10 rounded-t-md bg-gradient-to-t from-neon-emerald/60 to-neon-emerald shadow-[0_0_20px_rgba(0,255,136,0.65)]"
          />
          <CrestImage src={highlight.match.home_crest} alt="" className="h-6 w-6 object-contain" />
        </div>
        <div className="flex flex-col items-center gap-1.5">
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: `${Math.max(100 - homePct, 8)}%` }}
            transition={{ duration: 0.7, ease: "easeOut", delay: 0.1 }}
            style={{ transform: "rotateX(35deg) rotateZ(6deg) translateZ(10px)", transformStyle: "preserve-3d" }}
            className="w-10 rounded-t-md bg-gradient-to-t from-neon-cyan/60 to-neon-cyan shadow-[0_0_20px_rgba(0,240,255,0.65)]"
          />
          <CrestImage src={highlight.match.away_crest} alt="" className="h-6 w-6 object-contain" />
        </div>
      </div>
      <p className="data-stream relative mt-2 text-center font-mono text-xs text-neon-cyan">
        {prediction.expected_goals_home.toFixed(1)} — {prediction.expected_goals_away.toFixed(1)} xG
      </p>
    </motion.div>
  );
}
