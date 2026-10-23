"use client";

import type { FormResult, MatchPrediction } from "@/lib/types";

const OUTCOME_CLASSES: Record<FormResult["outcome"], string> = {
  W: "bg-emerald/20 text-emerald-bright ring-1 ring-emerald/40",
  D: "bg-graphite-700 text-graphite-300 ring-1 ring-graphite-600",
  L: "bg-red-500/15 text-red-300 ring-1 ring-red-500/30",
};

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function StreakRow({ results }: { results: FormResult[] }) {
  return (
    <div className="flex justify-center gap-1">
      {results.slice(0, 5).map((r) => (
        <span
          key={r.match_id}
          className={`flex h-6 w-6 items-center justify-center rounded text-[10px] font-bold ${OUTCOME_CLASSES[r.outcome]}`}
        >
          {r.outcome}
        </span>
      ))}
      {results.length === 0 && <span className="text-xs text-graphite-600">—</span>}
    </div>
  );
}

function CompareRow({
  label,
  homeValue,
  awayValue,
  format = (v: number) => v.toFixed(2),
}: {
  label: string;
  homeValue: number;
  awayValue: number;
  format?: (v: number) => string;
}) {
  const total = homeValue + awayValue || 1;
  const homePct = (homeValue / total) * 100;
  return (
    <div>
      <p className="mb-1 text-center text-[11px] text-graphite-500">{label}</p>
      <div className="flex items-center gap-2">
        <span className="w-12 text-right font-mono text-sm font-semibold text-neon-emerald">
          {format(homeValue)}
        </span>
        <div className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-graphite-800">
          <div className="h-full bg-neon-emerald" style={{ width: `${homePct}%` }} />
          <div className="h-full bg-neon-cyan" style={{ width: `${100 - homePct}%` }} />
        </div>
        <span className="w-12 font-mono text-sm font-semibold text-neon-cyan">
          {format(awayValue)}
        </span>
      </div>
    </div>
  );
}

export default function HeadToHeadCompare({
  homeLabel,
  awayLabel,
  homeForm,
  awayForm,
  headToHead,
  prediction,
}: {
  homeLabel: string;
  awayLabel: string;
  homeForm: FormResult[];
  awayForm: FormResult[];
  headToHead: FormResult[];
  prediction: MatchPrediction;
}) {
  const homeGoalsForSeason = average(homeForm.map((r) => r.goals_for));
  const awayGoalsForSeason = average(awayForm.map((r) => r.goals_for));
  const homeGoalsForLast5 = average(homeForm.slice(0, 5).map((r) => r.goals_for));
  const awayGoalsForLast5 = average(awayForm.slice(0, 5).map((r) => r.goals_for));
  const homeGoalsAgainstSeason = average(homeForm.map((r) => r.goals_against));
  const awayGoalsAgainstSeason = average(awayForm.map((r) => r.goals_against));

  const h2hWins = headToHead.filter((r) => r.outcome === "W").length;
  const h2hDraws = headToHead.filter((r) => r.outcome === "D").length;
  const h2hLosses = headToHead.filter((r) => r.outcome === "L").length;
  const h2hSummary =
    headToHead.length === 0
      ? "Sin enfrentamientos directos reales en los datos disponibles."
      : h2hWins > h2hLosses
        ? `${homeLabel} domina el historial directo (${h2hWins}V ${h2hDraws}E ${h2hLosses}D en los últimos ${headToHead.length}).`
        : h2hLosses > h2hWins
          ? `${awayLabel} domina el historial directo (${h2hLosses}V ${h2hDraws}E ${h2hWins}D en los últimos ${headToHead.length}, desde la óptica de ${homeLabel}).`
          : `Historial directo equilibrado (${h2hWins}V ${h2hDraws}E ${h2hLosses}D en los últimos ${headToHead.length}).`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs font-semibold text-graphite-300">
        <span className="text-neon-emerald">{homeLabel}</span>
        <span className="text-graphite-600">cara a cara</span>
        <span className="text-neon-cyan">{awayLabel}</span>
      </div>

      <div>
        <p className="mb-1 text-center text-[11px] text-graphite-500">
          Racha (últimos 5, más reciente primero)
        </p>
        <div className="flex items-center justify-between gap-2">
          <StreakRow results={homeForm} />
          <StreakRow results={awayForm} />
        </div>
      </div>

      <CompareRow label="Goles a favor/partido (temporada)" homeValue={homeGoalsForSeason} awayValue={awayGoalsForSeason} />
      <CompareRow label="Goles a favor/partido (últimos 5)" homeValue={homeGoalsForLast5} awayValue={awayGoalsForLast5} />
      <CompareRow
        label="Goles en contra/partido (solidez)"
        homeValue={homeGoalsAgainstSeason}
        awayValue={awayGoalsAgainstSeason}
      />
      <CompareRow
        label="Córners estimados a favor (este partido)"
        homeValue={prediction.expected_corners_home}
        awayValue={prediction.expected_corners_away}
        format={(v) => v.toFixed(1)}
      />

      <div className="rounded-lg bg-graphite-800/60 px-3 py-2 text-center text-[11px] text-graphite-300">
        {h2hSummary}
      </div>
    </div>
  );
}
