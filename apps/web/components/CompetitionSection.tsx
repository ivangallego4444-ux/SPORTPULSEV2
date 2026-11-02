"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import {
  fetchMatches,
  fetchQuickPicks,
  fetchStandings,
  getCachedJson,
  matchesPath,
  standingsPath,
} from "@/lib/api";
import type { Competition, Match, MatchesResponse, QuickPicksResponse, StandingRow, StandingsResponse } from "@/lib/types";

import EmptyState from "./EmptyState";
import LeagueHeroHeader from "./LeagueHeroHeader";
import MatchCard from "./MatchCard";
import MatchDetailModal from "./MatchDetailModal";
import { SkeletonGrid } from "./SkeletonCard";
import StandingsTable from "./StandingsTable";

type LoadState = "loading" | "ready" | "error";

export default function CompetitionSection({ slug }: { slug: string }) {
  // Stale-while-revalidate: a tab already visited this session renders
  // immediately from the client cache (see lib/clientCache.ts) instead of
  // flashing a skeleton again, while the effect below still fires a real
  // background refetch to keep it current.
  const cachedMatches = getCachedJson<MatchesResponse>(matchesPath(slug));
  const cachedStandings = getCachedJson<StandingsResponse>(standingsPath(slug));

  const [state, setState] = useState<LoadState>(cachedMatches ? "ready" : "loading");
  const [competition, setCompetition] = useState<Competition | null>(cachedMatches?.competition ?? null);
  const [matches, setMatches] = useState<Match[]>(cachedMatches?.matches ?? []);
  const [standings, setStandings] = useState<StandingRow[] | null>(cachedStandings?.standings ?? null);
  const [quickPicks, setQuickPicks] = useState<QuickPicksResponse>({});
  const [error, setError] = useState<string | null>(null);
  const [detailMatch, setDetailMatch] = useState<Match | null>(null);

  useEffect(() => {
    let cancelled = false;
    const cached = getCachedJson<MatchesResponse>(matchesPath(slug));
    if (!cached) {
      setState("loading");
    }
    setDetailMatch(null);

    Promise.all([fetchMatches(slug), fetchStandings(slug), fetchQuickPicks(slug).catch(() => ({}))])
      .then(([matchesRes, standingsRes, picksRes]) => {
        if (cancelled) return;
        setCompetition(matchesRes.competition);
        setMatches(matchesRes.matches);
        setStandings(standingsRes.standings);
        setQuickPicks(picksRes);
        setState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (!cached) {
          setError(err instanceof Error ? err.message : "Error desconocido");
          setState("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (state === "loading") {
    return (
      <div className="space-y-6">
        <div className="skeleton h-6 w-48 animate-shimmer rounded" />
        <SkeletonGrid count={4} />
      </div>
    );
  }

  if (state === "error" || !competition) {
    return (
      <EmptyState
        tone="error"
        title="No se ha podido conectar con la API"
        description={error ?? "Comprueba que apps/api esté en marcha y que NEXT_PUBLIC_API_URL apunte a su puerto real."}
      />
    );
  }

  // Real bug found live: OpenFootball gives a real match date but no real
  // kick-off time for anything beyond its own stale snapshot — those
  // fixtures carry a midnight-UTC placeholder (see apps/api/app/main.py's
  // _merge_matches_by_identity), not the real evening kick-off. Comparing
  // that placeholder against the exact current instant (`Date.now()`)
  // meant every match scheduled for *today* silently vanished from
  // "próximos partidos" the moment it ticked past midnight UTC — hours
  // before the real match had actually been played — jumping straight to
  // next week's round instead. Comparing by UTC calendar date instead
  // (same granularity apps/api's own _demote_stale_scheduled_matches
  // already uses to decide what's stale) keeps a match "upcoming" for its
  // whole real-world day, placeholder time or not.
  const startOfTodayUTC = Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    new Date().getUTCDate()
  );
  const upcomingSorted = matches
    .filter((m) => (m.status === "scheduled" || m.status === "live") && m.kickoff !== null)
    .filter((m) => new Date(m.kickoff as string).getTime() >= startOfTodayUTC)
    .sort((a, b) => new Date(a.kickoff as string).getTime() - new Date(b.kickoff as string).getTime());

  // "La próxima jornada completa": every upcoming match within 4 days of
  // the earliest one, covering a full weekend round (or a single
  // mid-week Champions League matchday) rather than a fixed calendar
  // window that could cut a jornada in half.
  const JORNADA_WINDOW_MS = 4 * 24 * 60 * 60 * 1000;
  const earliestUpcoming = upcomingSorted[0]?.kickoff
    ? new Date(upcomingSorted[0].kickoff as string).getTime()
    : null;
  const upcoming =
    earliestUpcoming === null
      ? []
      : upcomingSorted
          .filter((m) => new Date(m.kickoff as string).getTime() <= earliestUpcoming + JORNADA_WINDOW_MS)
          .slice(0, 20);

  // "Las últimas 2 jornadas": every finished match within 10 days of the
  // most recent one. Real bug found live: a match whose kickoff has
  // already passed but whose real result hasn't reached either free
  // source yet is correctly marked "unknown" by the API (never a
  // fabricated score — see apps/api's _demote_stale_scheduled_matches),
  // but this section used to only look at status === "finished", so
  // that match simply vanished from the page instead of showing as
  // pending — a real match the user watched (or saw the result of
  // elsewhere) looked like it had never been played. Including
  // "unknown" here too surfaces it with its "Resultado pendiente"
  // badge (see MatchCard) and lets it flip to a real score in place
  // the moment a source answers, instead of disappearing.
  const finishedSorted = matches
    .filter((m) => (m.status === "finished" || m.status === "unknown") && m.kickoff !== null)
    .sort((a, b) => new Date(b.kickoff as string).getTime() - new Date(a.kickoff as string).getTime());
  const RECENT_WINDOW_MS = 10 * 24 * 60 * 60 * 1000;
  const latestFinished = finishedSorted[0]?.kickoff
    ? new Date(finishedSorted[0].kickoff as string).getTime()
    : null;
  const recent =
    latestFinished === null
      ? []
      : finishedSorted
          .filter((m) => latestFinished - new Date(m.kickoff as string).getTime() <= RECENT_WINDOW_MS)
          .slice(0, 20);

  return (
    <motion.section
      key={slug}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <LeagueHeroHeader competition={competition} matches={matches} />

      {competition.notes && (
        <p className="rounded-lg border border-electric/20 bg-electric/5 px-3 py-2 text-sm text-graphite-400">
          {competition.notes}
        </p>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
          Próximos partidos
        </h3>
        {upcoming.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <AnimatePresence>
              {upcoming.map((match, i) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  onOpenDetail={setDetailMatch}
                  index={i}
                  pick={quickPicks[match.id]}
                />
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <EmptyState title="Sin próximos partidos disponibles en esta fuente ahora mismo." />
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
          Resultados recientes
        </h3>
        {recent.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {recent.map((match, i) => (
              <MatchCard key={match.id} match={match} onOpenDetail={setDetailMatch} index={i} />
            ))}
          </div>
        ) : (
          <EmptyState title="Sin resultados recientes disponibles en esta fuente ahora mismo." />
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
          Clasificación
        </h3>
        {standings && standings.length > 0 ? (
          <StandingsTable rows={standings} competitionSlug={slug} matches={matches} />
        ) : competition.supports_standings ? (
          <EmptyState
            title="No se ha podido cargar la clasificación ahora mismo."
            description="La fuente gratuita limita las peticiones por minuto; vuelve a intentarlo en breve."
          />
        ) : (
          <EmptyState
            title="Clasificación no disponible para esta competición."
            description="La fuente de datos gratuita no proporciona esta información para este tipo de competición."
          />
        )}
      </div>

      <MatchDetailModal match={detailMatch} competitionSlug={slug} onClose={() => setDetailMatch(null)} />
    </motion.section>
  );
}
