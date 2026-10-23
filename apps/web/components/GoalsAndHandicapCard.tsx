"use client";

import type { HandicapLine, MatchPrediction } from "@/lib/types";

function semaphoreColor(pct: number): string {
  if (pct >= 65) return "bg-neon-emerald";
  if (pct >= 45) return "bg-electric";
  return "bg-graphite-600";
}

function GoalBar({ label, pct }: { label: string; pct: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-graphite-400">
        <span>{label}</span>
        <span className="font-mono font-semibold text-graphite-100">{pct.toFixed(0)}%</span>
      </div>
      <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-graphite-800">
        <div className={`h-full rounded-full ${semaphoreColor(pct)}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function describeHandicapLine(line: number): string {
  if (line === 0) return "Hándicap 0.0 (empate = apuesta no válida)";
  const sign = line > 0 ? "+" : "";
  const meaning = line < 0 ? "gana el partido o cubre el margen" : "gana, empata o pierde por poco";
  return `Hándicap ${sign}${line} (local ${meaning})`;
}

const SIMPLE_LINES = [-0.5, 0.0, 0.5];

export default function GoalsAndHandicapCard({ prediction }: { prediction: MatchPrediction }) {
  const simpleHandicap = SIMPLE_LINES.map((line) =>
    prediction.asian_handicap.find((h: HandicapLine) => h.line === line)
  ).filter((h): h is HandicapLine => h !== undefined);

  return (
    <div className="space-y-4">
      <div>
        <p className="mb-2 text-[11px] uppercase tracking-wide text-graphite-500">Mercado de goles</p>
        <div className="space-y-2">
          <GoalBar label="Más de 1.5 goles" pct={prediction.over_1_5_pct} />
          <GoalBar label="Más de 2.5 goles" pct={prediction.over_2_5_pct} />
          <GoalBar label="Ambos equipos marcan" pct={prediction.btts_yes_pct} />
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] uppercase tracking-wide text-graphite-500">
          Hándicap asiático (equipo local)
        </p>
        <div className="space-y-1.5">
          {simpleHandicap.map((h) => (
            <div
              key={h.line}
              className="flex items-center justify-between rounded-lg border border-graphite-800 bg-graphite-900 px-3 py-2"
            >
              <span className="text-xs text-graphite-300">{describeHandicapLine(h.line)}</span>
              <span className="font-mono text-sm font-bold text-graphite-100">
                {h.cover_pct.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
        <p className="mt-1.5 text-[10px] leading-relaxed text-graphite-600">
          % = probabilidad estadística de cubrir esa línea, calculada con el mismo modelo que el resto
          del pronóstico — nunca una cuota de casa de apuestas.
        </p>
      </div>
    </div>
  );
}
