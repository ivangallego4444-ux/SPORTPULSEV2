"use client";

import { motion } from "framer-motion";

import type { MatchPrediction } from "@/lib/types";

function confidenceColors(pct: number): { bg: string; text: string; ring: string; label: string } {
  if (pct >= 70) {
    return {
      bg: "bg-neon-emerald/10",
      text: "text-neon-emerald",
      ring: "ring-neon-emerald/40",
      label: "Confianza alta",
    };
  }
  if (pct >= 50) {
    return {
      bg: "bg-electric/10",
      text: "text-electric-bright",
      ring: "ring-electric/40",
      label: "Confianza media",
    };
  }
  return {
    bg: "bg-graphite-700/40",
    text: "text-graphite-300",
    ring: "ring-graphite-600",
    label: "Confianza baja",
  };
}

/** The single clearest takeaway for this match, in plain Spanish — a
 * selection among the real markets already computed (see
 * sp_predict.poisson._recommend_pick), never a separately-invented
 * metric. Designed to be understood in 3 seconds. */
export default function RecommendedPickCard({ prediction }: { prediction: MatchPrediction }) {
  const colors = confidenceColors(prediction.recommended_pick_pct);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border p-4 ${colors.bg} ${colors.ring} ring-1`}
    >
      <p className="text-[11px] uppercase tracking-wide text-graphite-500">Pronóstico recomendado</p>
      <p className={`mt-1 text-xl font-extrabold leading-tight ${colors.text}`}>
        {prediction.recommended_pick_label}
      </p>
      <div className="mt-2 flex items-center gap-2">
        <span className={`font-mono text-2xl font-bold ${colors.text}`}>
          {prediction.recommended_pick_pct.toFixed(0)}%
        </span>
        <span className={`text-xs font-medium ${colors.text}`}>{colors.label}</span>
      </div>
      {prediction.confidence === "league_average" && (
        <p className="mt-2 text-[11px] text-amber-300">
          ⚠ Estimación básica: historial real insuficiente todavía para uno de los dos equipos.
        </p>
      )}
    </motion.div>
  );
}
