"use client";

import { motion } from "framer-motion";

import { useTilt } from "@/lib/useTilt";
import type { HighlightMatch } from "@/lib/types";

import CountUp from "../CountUp";
import CrestImage from "../CrestImage";

const LABELS: Record<string, string> = {
  favorite: "1X2",
  over_2_5: "+2.5 goles",
  btts: "Ambos marcan",
};

const KIND_GLOW: Record<string, string> = {
  favorite: "rgba(0,255,136,0.35)",
  over_2_5: "rgba(0,240,255,0.35)",
  btts: "rgba(168,85,247,0.35)",
};

export default function PickCard3D({
  highlight,
  kind,
}: {
  highlight: HighlightMatch;
  kind: "favorite" | "over_2_5" | "btts";
}) {
  const { rotateX, rotateY, onMouseMove, onMouseLeave } = useTilt(14);
  const prediction = highlight.prediction!;
  const pct =
    kind === "favorite"
      ? Math.max(prediction.home_win_pct, prediction.away_win_pct)
      : kind === "over_2_5"
        ? prediction.over_2_5_pct
        : prediction.btts_yes_pct;
  const elite = pct >= 80;

  return (
    <motion.div
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{ rotateX, rotateY, transformPerspective: 1400 }}
      whileHover={{ z: 30, transition: { type: "spring", stiffness: 300, damping: 20 } }}
      className={`gradient-border rounded-xl border p-3 backdrop-blur-md ${
        elite
          ? "border-neon-gold/50 bg-neon-gold/[0.06]"
          : "border-white/10 bg-white/[0.03]"
      }`}
    >
      <div
        className="rounded-xl"
        style={{
          boxShadow: `0 20px 40px -12px ${KIND_GLOW[kind]}, inset 0 1px 0 rgba(255,255,255,0.08)`,
        }}
      >
        <div className="flex items-center justify-between gap-1">
          <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-semibold text-graphite-300">
            {LABELS[kind]}
          </span>
          <div className="flex items-center gap-1">
            {prediction.confidence === "league_average" && (
              <span
                title="Estimación básica: historial real insuficiente"
                className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-graphite-500"
              >
                ~ est.
              </span>
            )}
            {elite && (
              <span className="rounded bg-neon-gold/20 px-1.5 py-0.5 text-[10px] font-bold text-neon-gold">
                PRO
              </span>
            )}
          </div>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-xs text-graphite-300">
          <CrestImage src={highlight.match.home_crest} alt="" className="h-4 w-4 object-contain" />
          <span className="truncate">{highlight.match.home}</span>
          <span className="text-graphite-600">-</span>
          <span className="truncate">{highlight.match.away}</span>
          <CrestImage src={highlight.match.away_crest} alt="" className="h-4 w-4 object-contain" />
        </div>
        <p
          className={`mt-1 font-mono text-2xl font-extrabold ${
            elite ? "text-neon-gold" : "text-neon-emerald"
          }`}
        >
          <CountUp value={pct} suffix="%" />
        </p>
      </div>
    </motion.div>
  );
}
