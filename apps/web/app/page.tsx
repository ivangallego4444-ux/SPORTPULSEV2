"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { useHighlights } from "@/lib/HighlightsContext";

import EmptyState from "@/components/EmptyState";
import FeaturedMatch from "@/components/FeaturedMatch";
import MiniStandings from "@/components/MiniStandings";
import { SkeletonGrid } from "@/components/SkeletonCard";
import Ticker from "@/components/Ticker";
import TopPicksGrid from "@/components/TopPicksGrid";

const COMPETITION_NAMES: Record<string, string> = {
  laliga: "LaLiga",
  "premier-league": "Premier League",
  bundesliga: "1. Bundesliga",
  "serie-a": "Serie A",
  "champions-league": "UEFA Champions League",
};

const SPORT_LINKS = [
  { href: "/futbol", title: "Fútbol", description: "8 competiciones reales, con predicción." },
  { href: "/baloncesto", title: "Baloncesto", description: "NBA en vivo." },
  { href: "/tenis", title: "Tenis", description: "ATP y WTA Tour." },
  { href: "/equipos", title: "Explorador de equipos", description: "Busca cualquier equipo real." },
];

export default function HomePage() {
  const { data, error } = useHighlights();

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-graphite-50 to-graphite-300 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent sm:text-4xl"
      >
        SportPulse
      </motion.h1>
      <p className="mt-2 max-w-2xl text-sm text-graphite-400 sm:text-base">
        Datos reales por deporte, sin coste. Predicciones calculadas con un modelo estadístico sobre
        resultados reales — nunca cuotas inventadas. Cuando una competición no tiene datos disponibles,
        se indica explícitamente.
      </p>

      {error && (
        <div className="mt-6">
          <EmptyState tone="error" title="No se ha podido conectar con la API" description={error} />
        </div>
      )}

      {!error && !data && (
        <div className="mt-6 space-y-6">
          <div className="skeleton h-48 animate-shimmer rounded-3xl" />
          <SkeletonGrid count={4} />
        </div>
      )}

      {data && (
        <div className="mt-6 space-y-8">
          {data.unavailable.length > 0 && (
            <EmptyState
              title="Algunas ligas no se han podido cargar ahora mismo."
              description={`La fuente gratuita limita las peticiones por minuto (${data.unavailable.join(", ")}). Esta sección se actualiza sola cuando el límite se libera — prueba a recargar en unos segundos.`}
            />
          )}

          {data.ticker.length > 0 && <Ticker highlights={data.ticker} />}

          <FeaturedMatch highlight={data.featured} />

          <TopPicksGrid
            title="Favoritos más claros"
            highlights={data.top_by_favorite}
            statKey="favorite"
            accentClass="text-emerald-bright"
          />
          <TopPicksGrid
            title="Mayor probabilidad de +2.5 goles"
            highlights={data.top_over_2_5}
            statKey="over_2_5"
            accentClass="text-electric-bright"
          />
          <TopPicksGrid
            title="Mayor probabilidad de que ambos marquen"
            highlights={data.top_btts}
            statKey="btts"
            accentClass="text-amber-400"
          />

          {Object.keys(data.mini_standings).length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
                Clasificaciones
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(data.mini_standings).map(([slug, rows]) => (
                  <MiniStandings key={slug} competitionName={COMPETITION_NAMES[slug] ?? slug} rows={rows} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-10 grid gap-4 sm:grid-cols-4">
        {SPORT_LINKS.map((card, i) => (
          <motion.div
            key={card.href}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            whileHover={{ y: -4 }}
          >
            <Link
              href={card.href}
              className="block h-full rounded-2xl border border-graphite-800 bg-graphite-900 p-4 shadow-card transition-colors hover:border-emerald/40"
            >
              <h2 className="font-semibold text-graphite-50">{card.title}</h2>
              <p className="mt-1 text-sm text-graphite-400">{card.description}</p>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
