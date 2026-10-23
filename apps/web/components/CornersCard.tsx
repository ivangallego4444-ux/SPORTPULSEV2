"use client";

import type { MatchPrediction } from "@/lib/types";

const FAVOURED_LABEL: Record<MatchPrediction["corners_favoured_side"], string> = {
  home: "El local sacará más córners",
  away: "El visitante sacará más córners",
  even: "Reparto equilibrado de córners",
};

export default function CornersCard({
  prediction,
  homeLabel,
  awayLabel,
}: {
  prediction: MatchPrediction;
  homeLabel: string;
  awayLabel: string;
}) {
  return (
    <div className="rounded-xl border border-graphite-800 bg-graphite-900 p-3">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-graphite-500">
        Córners esperados (estimación)
      </p>

      <div className="flex items-end justify-center gap-6">
        <div className="text-center">
          <p className="text-xs text-graphite-500">{homeLabel}</p>
          <p className="font-mono text-2xl font-bold text-neon-emerald">
            {prediction.expected_corners_home.toFixed(1)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] text-graphite-600">TOTAL</p>
          <p className="font-mono text-3xl font-extrabold text-graphite-100">
            {prediction.expected_corners_total.toFixed(1)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-graphite-500">{awayLabel}</p>
          <p className="font-mono text-2xl font-bold text-neon-cyan">
            {prediction.expected_corners_away.toFixed(1)}
          </p>
        </div>
      </div>

      <p className="mt-2 text-center text-xs text-graphite-400">
        {FAVOURED_LABEL[prediction.corners_favoured_side]}
      </p>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-graphite-800/60 px-2 py-1.5 text-center">
          <p className="text-[10px] text-graphite-500">Más de 8.5 córners</p>
          <p className="font-mono text-sm font-semibold text-graphite-100">
            {prediction.corners_over_8_5_pct.toFixed(0)}%
          </p>
        </div>
        <div className="rounded-lg bg-graphite-800/60 px-2 py-1.5 text-center">
          <p className="text-[10px] text-graphite-500">Más de 9.5 córners</p>
          <p className="font-mono text-sm font-semibold text-graphite-100">
            {prediction.corners_over_9_5_pct.toFixed(0)}%
          </p>
        </div>
      </div>

      <p className="mt-2 text-[10px] leading-relaxed text-graphite-600">
        Estimación estadística basada en el potencial ofensivo real de ambos equipos — ninguna fuente
        gratuita da córners medidos (reales), ni antes ni después del partido, así que esto es un
        modelo, no un dato oficial.
      </p>
    </div>
  );
}
