import type { FormResult } from "@/lib/types";

const OUTCOME_CLASSES: Record<FormResult["outcome"], string> = {
  W: "bg-emerald/20 text-emerald-bright ring-1 ring-emerald/40",
  D: "bg-graphite-700 text-graphite-300 ring-1 ring-graphite-600",
  L: "bg-red-500/15 text-red-300 ring-1 ring-red-500/30",
};

export default function FormStrip({ teamName, results }: { teamName: string; results: FormResult[] }) {
  return (
    <div>
      <p className="mb-1.5 text-xs uppercase tracking-wide text-graphite-500">{teamName}</p>
      {results.length === 0 ? (
        <p className="text-sm text-graphite-500">
          Sin partidos recientes disponibles en esta fuente.
        </p>
      ) : (
        <div className="flex gap-1.5">
          {results.map((result) => (
            <div
              key={result.match_id}
              title={`${result.venue === "home" ? "vs" : "@"} ${result.opponent}: ${result.goals_for}-${result.goals_against}`}
              className={`flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold ${OUTCOME_CLASSES[result.outcome]}`}
            >
              {result.outcome}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
