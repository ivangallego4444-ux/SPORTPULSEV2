import Link from "next/link";

import type { StandingRow } from "@/lib/types";

import CrestImage from "./CrestImage";

export default function MiniStandings({
  competitionName,
  rows,
}: {
  competitionName: string;
  rows: StandingRow[];
}) {
  return (
    <div className="rounded-xl border border-graphite-800 bg-graphite-900 p-3">
      <h4 className="mb-2 truncate text-xs font-semibold uppercase tracking-wide text-graphite-500">
        {competitionName}
      </h4>
      <ol className="space-y-1">
        {rows.map((row) => (
          <li key={row.rank} className="flex items-center gap-2 text-sm">
            <span className="w-4 text-right text-graphite-500">{row.rank}</span>
            <CrestImage src={row.crest_url} alt="" className="h-4 w-4 object-contain" />
            <span className="flex-1 truncate text-graphite-200">{row.team}</span>
            <span className="font-mono text-xs font-semibold text-emerald-bright">{row.points}</span>
          </li>
        ))}
      </ol>
      <Link href="/futbol" className="mt-2 block text-center text-[11px] text-graphite-500 hover:text-emerald-bright">
        Ver completa →
      </Link>
    </div>
  );
}
