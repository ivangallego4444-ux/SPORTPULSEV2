import type { Match } from "./types";

export type StreakResult = "W" | "D" | "L";

// Real recent-form sequence (oldest -> newest) for one team, built purely
// from already-fetched real finished matches — never a separate request,
// never a fabricated letter.
export function recentStreak(matches: Match[], team: string, limit = 5): StreakResult[] {
  const finished = matches
    .filter((m) => m.status === "finished" && (m.home === team || m.away === team) && m.kickoff)
    .sort((a, b) => new Date(a.kickoff as string).getTime() - new Date(b.kickoff as string).getTime());

  const results: StreakResult[] = [];
  for (const m of finished) {
    if (m.home_score === null || m.away_score === null) continue;
    const isHome = m.home === team;
    const goalsFor = isHome ? m.home_score : m.away_score;
    const goalsAgainst = isHome ? m.away_score : m.home_score;
    if (goalsFor > goalsAgainst) results.push("W");
    else if (goalsFor === goalsAgainst) results.push("D");
    else results.push("L");
  }
  return results.slice(-limit);
}

export const STREAK_DOT_CLASSES: Record<StreakResult, string> = {
  W: "bg-emerald-bright",
  D: "bg-graphite-500",
  L: "bg-red-400",
};
