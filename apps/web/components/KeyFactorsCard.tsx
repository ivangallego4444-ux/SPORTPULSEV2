"use client";

import type { MatchPrediction } from "@/lib/types";

function RatingBar({ label, rating }: { label: string; rating: number }) {
  // rating is relative to the league average (1.0 = average). Clamp the
  // visual bar to a sane 0-2x range so one wild early-season number
  // doesn't blow out the layout.
  const pct = Math.max(0, Math.min(rating / 2, 1)) * 100;
  const aboveAverage = rating >= 1;
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-graphite-400">
        <span>{label}</span>
        <span className={aboveAverage ? "text-neon-emerald" : "text-graphite-400"}>
          {rating.toFixed(2)}×
        </span>
      </div>
      <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-graphite-800">
        <div
          className={`h-full rounded-full ${aboveAverage ? "bg-neon-emerald" : "bg-graphite-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/** A plain-language breakdown of the real numbers already behind the
 * Dixon-Coles prediction — attack/defense ratios relative to the
 * competition's own average, and the real head-to-head adjustment —
 * instead of only showing the final percentages. */
export default function KeyFactorsCard({
  prediction,
  homeLabel,
  awayLabel,
}: {
  prediction: MatchPrediction;
  homeLabel: string;
  awayLabel: string;
}) {
  const h2hDirection =
    prediction.h2h_adjustment_pct > 0
      ? homeLabel
      : prediction.h2h_adjustment_pct < 0
        ? awayLabel
        : null;

  return (
    <div className="space-y-3 rounded-xl border border-graphite-800 bg-graphite-900 p-3">
      <p className="text-[11px] uppercase tracking-wide text-graphite-500">
        Factores clave del pronóstico
      </p>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        <RatingBar label={`${homeLabel} · ataque local`} rating={prediction.home_attack_rating} />
        <RatingBar label={`${awayLabel} · ataque visitante`} rating={prediction.away_attack_rating} />
        <RatingBar
          label={`${homeLabel} · solidez local`}
          rating={1 / Math.max(prediction.home_defense_rating, 0.01)}
        />
        <RatingBar
          label={`${awayLabel} · solidez visitante`}
          rating={1 / Math.max(prediction.away_defense_rating, 0.01)}
        />
      </div>

      <div className="border-t border-graphite-800 pt-2 text-[11px] text-graphite-400">
        {prediction.h2h_matches_considered === 0 ? (
          <span>Sin enfrentamientos directos reales en los datos disponibles.</span>
        ) : h2hDirection ? (
          <span>
            Historial directo ({prediction.h2h_matches_considered} partido
            {prediction.h2h_matches_considered === 1 ? "" : "s"}): favorece a{" "}
            <span className="text-graphite-200">{h2hDirection}</span> (
            {Math.abs(prediction.h2h_adjustment_pct).toFixed(1)}% de ajuste).
          </span>
        ) : (
          <span>
            Historial directo ({prediction.h2h_matches_considered} partidos): equilibrado, sin
            ajuste neto.
          </span>
        )}
      </div>

      <p className="text-[10px] leading-relaxed text-graphite-600">
        1.00× = exactamente la media de la competición. Son las razones reales detrás del cálculo,
        no una explicación añadida a posteriori.
      </p>
    </div>
  );
}
