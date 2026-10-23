"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { fetchAnalysis } from "@/lib/api";
import type { Match, MatchAnalysis } from "@/lib/types";

import CornersCard from "./CornersCard";
import CrestImage from "./CrestImage";
import EmptyState from "./EmptyState";
import GoalsAndHandicapCard from "./GoalsAndHandicapCard";
import HeadToHeadCompare from "./HeadToHeadCompare";
import KeyFactorsCard from "./KeyFactorsCard";
import MomentumChart from "./MomentumChart";
import PredictionPanel from "./PredictionPanel";
import RecommendedPickCard from "./RecommendedPickCard";
import StatsComparison from "./StatsComparison";

export default function MatchDetailModal({
  match,
  competitionSlug,
  onClose,
}: {
  match: Match | null;
  competitionSlug: string;
  onClose: () => void;
}) {
  const [analysis, setAnalysis] = useState<MatchAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!match) return;
    let cancelled = false;
    setLoading(true);
    setAnalysis(null);
    setError(null);

    fetchAnalysis(competitionSlug, match.id)
      .then((data) => {
        if (!cancelled) setAnalysis(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [match, competitionSlug]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <AnimatePresence>
      {match && (
        <motion.div
          className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-graphite-800 bg-graphite-900 p-5 shadow-card"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                {match.sport === "tenis" && match.home_crest && match.away_crest ? (
                  <div className="flex shrink-0 items-center gap-1">
                    <CrestImage
                      src={match.home_crest}
                      alt=""
                      className="h-16 w-16 rounded-full object-cover ring-2 ring-emerald/50"
                    />
                    <span className="px-1 text-xs font-bold text-graphite-500">VS</span>
                    <CrestImage
                      src={match.away_crest}
                      alt=""
                      className="h-16 w-16 rounded-full object-cover ring-2 ring-electric/50"
                    />
                  </div>
                ) : (
                  match.home_crest && (
                    <div className="flex -space-x-2">
                      <CrestImage src={match.home_crest} alt="" className="h-8 w-8 object-contain" />
                      <CrestImage src={match.away_crest} alt="" className="h-8 w-8 object-contain" />
                    </div>
                  )
                )}
                <div>
                  <h3 className="text-lg font-bold text-graphite-100">
                    {match.home && match.away ? `${match.home} vs ${match.away}` : match.title}
                  </h3>
                  <p className="text-sm text-graphite-500">{match.competition_name}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="shrink-0 rounded-full p-1.5 text-graphite-400 hover:bg-graphite-800 hover:text-graphite-100"
              >
                ✕
              </button>
            </div>

            <div className="mt-5 space-y-6">
              {loading && (
                <div className="space-y-3">
                  <div className="skeleton h-24 animate-shimmer rounded-lg" />
                  <div className="skeleton h-16 animate-shimmer rounded-lg" />
                </div>
              )}

              {!loading && error && (
                <EmptyState
                  tone="error"
                  title="No se ha podido cargar el análisis"
                  description={error}
                />
              )}

              {!loading && !error && analysis && match.home && match.away && (
                <>
                  {analysis.prediction && (
                    <section>
                      <RecommendedPickCard prediction={analysis.prediction} />
                    </section>
                  )}

                  <section>
                    <h4 className="mb-2 text-sm font-semibold text-graphite-200">
                      Ganador y marcadores
                    </h4>
                    <PredictionPanel
                      prediction={analysis.prediction}
                      note={analysis.note}
                      homeTeam={match.home}
                      awayTeam={match.away}
                    />
                  </section>

                  {analysis.prediction && (
                    <section>
                      <h4 className="mb-2 text-sm font-semibold text-graphite-200">
                        Goles y hándicap
                      </h4>
                      <GoalsAndHandicapCard prediction={analysis.prediction} />
                    </section>
                  )}

                  {analysis.prediction && (
                    <section>
                      <CornersCard
                        prediction={analysis.prediction}
                        homeLabel={match.home}
                        awayLabel={match.away}
                      />
                    </section>
                  )}

                  <section>
                    <h4 className="mb-2 text-sm font-semibold text-graphite-200">
                      Comparativa cara a cara
                    </h4>
                    {analysis.prediction ? (
                      <HeadToHeadCompare
                        homeLabel={match.home}
                        awayLabel={match.away}
                        homeForm={analysis.home_form}
                        awayForm={analysis.away_form}
                        headToHead={analysis.head_to_head}
                        prediction={analysis.prediction}
                      />
                    ) : (
                      <p className="text-sm text-graphite-500">
                        Sin predicción disponible para construir la comparativa.
                      </p>
                    )}
                    <div className="mt-3">
                      <MomentumChart
                        homeLabel={match.home}
                        awayLabel={match.away}
                        homeForm={analysis.home_form}
                        awayForm={analysis.away_form}
                      />
                    </div>
                  </section>

                  {analysis.prediction && (
                    <section>
                      <KeyFactorsCard
                        prediction={analysis.prediction}
                        homeLabel={match.home}
                        awayLabel={match.away}
                      />
                    </section>
                  )}

                  {analysis.stats && (
                    <section>
                      <h4 className="mb-2 text-sm font-semibold text-graphite-200">
                        Estadísticas reales del partido
                      </h4>
                      <StatsComparison stats={analysis.stats} />
                      <p className="mt-2 text-[11px] text-graphite-600">
                        Solo tiros — la fuente gratuita no da córners ni tarjetas medidos.
                      </p>
                    </section>
                  )}
                </>
              )}

              {!loading && !error && analysis && (!match.home || !match.away) && (
                <EmptyState
                  title="Sin análisis estructurado para este partido"
                  description={analysis.note ?? undefined}
                />
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
