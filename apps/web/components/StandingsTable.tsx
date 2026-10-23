import { recentStreak, STREAK_DOT_CLASSES } from "@/lib/recentStreak";
import { zoneBarClass, zoneForRank, ZONE_LABELS } from "@/lib/standingsZones";
import type { Match, StandingRow } from "@/lib/types";

export default function StandingsTable({
  rows,
  competitionSlug,
  matches,
}: {
  rows: StandingRow[];
  competitionSlug?: string;
  matches?: Match[];
}) {
  const zonesShown = competitionSlug
    ? Array.from(
        new Set(
          rows
            .map((r) => zoneForRank(competitionSlug, r.rank)?.tone)
            .filter((t): t is NonNullable<typeof t> => Boolean(t))
        )
      )
    : [];

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-xl border border-graphite-800 bg-graphite-900">
        <table className="w-full min-w-[480px] text-sm">
          <thead>
            <tr className="border-b border-graphite-800 text-left text-graphite-500">
              <th className="w-1.5 px-0 py-2" />
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Equipo</th>
              <th className="px-3 py-2 text-center">PJ</th>
              <th className="px-3 py-2 text-center">G</th>
              <th className="px-3 py-2 text-center">E</th>
              <th className="px-3 py-2 text-center">P</th>
              <th className="px-3 py-2 text-center">Pts</th>
              {matches && <th className="px-3 py-2 text-center">Racha</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const zone = competitionSlug ? zoneForRank(competitionSlug, row.rank) : null;
              const streak = matches ? recentStreak(matches, row.team) : null;
              return (
                <tr
                  key={row.rank}
                  className="border-b border-graphite-800/60 last:border-0 hover:bg-graphite-800/40"
                >
                  <td className="w-1.5 px-0 py-2">
                    {zone && <div className={`h-5 w-1 rounded-full ${zoneBarClass(zone.tone)}`} />}
                  </td>
                  <td className="px-3 py-2 text-graphite-500">{row.rank}</td>
                  <td className="flex items-center gap-2 px-3 py-2 font-medium text-graphite-100">
                    {row.crest_url && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={row.crest_url}
                        alt=""
                        className="h-5 w-5 object-contain"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                      />
                    )}
                    {row.team}
                  </td>
                  <td className="px-3 py-2 text-center text-graphite-300">{row.played ?? "–"}</td>
                  <td className="px-3 py-2 text-center text-graphite-300">{row.wins ?? "–"}</td>
                  <td className="px-3 py-2 text-center text-graphite-300">{row.draws ?? "–"}</td>
                  <td className="px-3 py-2 text-center text-graphite-300">{row.losses ?? "–"}</td>
                  <td className="px-3 py-2 text-center font-semibold text-emerald-bright">
                    {row.points ?? "–"}
                  </td>
                  {matches && (
                    <td className="px-3 py-2">
                      <div className="flex justify-center gap-1">
                        {streak && streak.length > 0 ? (
                          streak.map((r, i) => (
                            <span
                              key={i}
                              title={r === "W" ? "Victoria" : r === "D" ? "Empate" : "Derrota"}
                              className={`h-2 w-2 rounded-full ${STREAK_DOT_CLASSES[r]}`}
                            />
                          ))
                        ) : (
                          <span className="text-xs text-graphite-600">–</span>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {zonesShown.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 px-1 text-[11px] text-graphite-500">
          {zonesShown.map((tone) => (
            <span key={tone} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${zoneBarClass(tone)}`} />
              {ZONE_LABELS[tone]}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
