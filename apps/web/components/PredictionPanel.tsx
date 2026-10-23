"use client";

import { motion } from "framer-motion";

import type { MatchPrediction } from "@/lib/types";

import EmptyState from "./EmptyState";

function Bar({ pct, colorClass, delay }: { pct: number; colorClass: string; delay: number }) {
  return (
    <motion.div
      className={`h-full ${colorClass}`}
      initial={{ width: 0 }}
      animate={{ width: `${pct}%` }}
      transition={{ duration: 0.6, delay, ease: "easeOut" }}
    />
  );
}

function StatBadge({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="rounded-lg border border-graphite-800 bg-graphite-900 px-3 py-2 text-center">
      <p className="text-xs text-graphite-500">{label}</p>
      <p className="mt-0.5 font-mono text-lg font-semibold text-graphite-100">
        {pct.toFixed(0)}%
      </p>
    </div>
  );
}

export default function PredictionPanel({
  prediction,
  note,
  homeTeam,
  awayTeam,
}: {
  prediction: MatchPrediction | null;
  note: string | null;
  homeTeam: string;
  awayTeam: string;
}) {
  if (!prediction) {
    return (
      <EmptyState
        title="Sin predicción para este partido"
        description={note ?? "La fuente de datos gratuita no da suficiente información."}
      />
    );
  }

  return (
    <div className="space-y-4">
      {prediction.confidence === "league_average" && (
        <div className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-300">
          <span className="font-bold">⚠ Estimación básica</span>
          <span className="text-amber-300/80">
            — historial real insuficiente, parte calculada con la media de la competición.
          </span>
        </div>
      )}
      <div>
        <div className="flex justify-between text-sm font-medium text-graphite-300">
          <span>{homeTeam}</span>
          <span className="text-graphite-500">Empate</span>
          <span>{awayTeam}</span>
        </div>
        <div className="mt-2 flex h-3 overflow-hidden rounded-full bg-graphite-800">
          <Bar pct={prediction.home_win_pct} colorClass="bg-emerald" delay={0} />
          <Bar pct={prediction.draw_pct} colorClass="bg-graphite-500" delay={0.1} />
          <Bar pct={prediction.away_win_pct} colorClass="bg-electric" delay={0.2} />
        </div>
        <div className="mt-1 flex justify-between font-mono text-sm">
          <span className="text-emerald-bright">{prediction.home_win_pct.toFixed(0)}%</span>
          <span className="text-graphite-400">{prediction.draw_pct.toFixed(0)}%</span>
          <span className="text-electric-bright">{prediction.away_win_pct.toFixed(0)}%</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatBadge label="Doble oportunidad 1X" pct={prediction.double_chance_1x_pct} />
        <StatBadge label="Doble oportunidad 12" pct={prediction.double_chance_12_pct} />
        <StatBadge label="Doble oportunidad X2" pct={prediction.double_chance_x2_pct} />
      </div>

      {prediction.top_scorelines.length > 0 && (
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-graphite-500">
            Marcadores exactos más probables
          </p>
          <div className="flex gap-2">
            {prediction.top_scorelines.map((s) => (
              <div
                key={`${s.home_goals}-${s.away_goals}`}
                className="flex-1 rounded-lg border border-graphite-800 bg-graphite-900 px-2 py-1.5 text-center"
              >
                <p className="font-mono text-sm font-semibold text-graphite-100">
                  {s.home_goals}-{s.away_goals}
                </p>
                <p className="font-mono text-xs text-graphite-500">{s.pct.toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs leading-relaxed text-graphite-500">{prediction.note}</p>
    </div>
  );
}
