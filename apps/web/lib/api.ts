import { getCached, setCached } from "./clientCache";
import type {
  Competition,
  HomeHighlights,
  LiveResponse,
  MatchAnalysis,
  MatchesResponse,
  QuickPicksResponse,
  SportInfo,
  StandingsResponse,
  TeamHistory,
  TeamSummary,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8020";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${path} respondió ${response.status}`);
  }
  const data = (await response.json()) as T;
  setCached(path, data);
  return data;
}

// Stale-while-revalidate: a component can call this to get an already-
// visited path's data synchronously (no skeleton) while this kicks a
// real background refetch to keep the cache fresh for next time — see
// lib/clientCache.ts. Only a read-through cache for GETs already backed
// by the snapshot-based API (see apps/api/app/main.py), never a
// substitute for real data.
export function getCachedJson<T>(path: string): T | undefined {
  return getCached<T>(path);
}

export function fetchSports(): Promise<SportInfo[]> {
  return getJson<SportInfo[]>("/api/sports");
}

export function fetchCompetitions(sport: string): Promise<Competition[]> {
  return getJson<Competition[]>(`/api/sports/${sport}/competitions`);
}

export function matchesPath(competitionSlug: string): string {
  return `/api/competitions/${competitionSlug}/matches`;
}

export function standingsPath(competitionSlug: string): string {
  return `/api/competitions/${competitionSlug}/standings`;
}

export function quickPicksPath(competitionSlug: string): string {
  return `/api/competitions/${competitionSlug}/quick-picks`;
}

export function fetchMatches(competitionSlug: string): Promise<MatchesResponse> {
  return getJson<MatchesResponse>(matchesPath(competitionSlug));
}

export function fetchStandings(competitionSlug: string): Promise<StandingsResponse> {
  return getJson<StandingsResponse>(standingsPath(competitionSlug));
}

export function fetchQuickPicks(competitionSlug: string): Promise<QuickPicksResponse> {
  return getJson<QuickPicksResponse>(quickPicksPath(competitionSlug));
}

export function fetchAnalysis(competitionSlug: string, matchId: string): Promise<MatchAnalysis> {
  return getJson<MatchAnalysis>(`/api/competitions/${competitionSlug}/matches/${matchId}/analysis`);
}

export function fetchHomeHighlights(): Promise<HomeHighlights> {
  return getJson<HomeHighlights>("/api/home/highlights");
}

export function fetchLive(sport: string): Promise<LiveResponse> {
  return getJson<LiveResponse>(`/api/sports/${sport}/live`);
}

export function searchTeams(query: string): Promise<TeamSummary[]> {
  return getJson<TeamSummary[]>(`/api/teams/search?q=${encodeURIComponent(query)}`);
}

export function fetchTeamHistory(
  competitionSlug: string,
  teamId: string,
  venue: "all" | "home" | "away",
  limit: number | null
): Promise<TeamHistory> {
  const params = new URLSearchParams({ venue });
  if (limit !== null) params.set("limit", String(limit));
  return getJson<TeamHistory>(`/api/teams/${competitionSlug}/${teamId}/history?${params}`);
}
