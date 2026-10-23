"use client";

import { motion } from "framer-motion";

import { useHighlights } from "@/lib/HighlightsContext";

import EmptyState from "../EmptyState";
import PickCard3D from "./PickCard3D";
import RadarChart from "./RadarChart";
import TacticalComparison from "./TacticalComparison";

export default function RightPanel() {
  const { data, loading } = useHighlights();

  const picks = data
    ? [
        ...data.top_by_favorite.slice(0, 2).map((h) => ({ h, kind: "favorite" as const })),
        ...data.top_over_2_5.slice(0, 1).map((h) => ({ h, kind: "over_2_5" as const })),
        ...data.top_btts.slice(0, 1).map((h) => ({ h, kind: "btts" as const })),
      ]
    : [];

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="gradient-border sticky top-20 h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-neon-purple/20 bg-obsidian/80 p-5 shadow-[0_0_40px_-10px_rgba(168,85,247,0.25)] backdrop-blur-sm"
    >
      <p className="bg-gradient-to-r from-neon-purple to-neon-cyan bg-clip-text text-xs font-semibold uppercase tracking-widest text-transparent">
        Radar de Valor · Alertas PRO
      </p>

      {loading && !data && (
        <div className="mt-4 space-y-3">
          <div className="skeleton h-24 animate-shimmer rounded-xl" />
          <div className="skeleton h-24 animate-shimmer rounded-xl" />
        </div>
      )}

      {data && picks.length === 0 && (
        <div className="mt-4">
          <EmptyState title="Sin alertas PRO disponibles ahora mismo." />
        </div>
      )}

      <div className="mt-4 space-y-3" style={{ perspective: "1400px" }}>
        {picks.map(({ h, kind }) => (
          <PickCard3D key={`${kind}-${h.match.id}`} highlight={h} kind={kind} />
        ))}
      </div>

      {data?.featured?.prediction && (
        <div className="mt-5">
          <p className="mb-2 text-[11px] uppercase tracking-wide text-graphite-500">
            Simulador táctico — partido del día
          </p>
          <TacticalComparison highlight={data.featured} />
          <div className="mt-3 flex justify-center">
            <RadarChart
              prediction={data.featured.prediction}
              homeLabel={data.featured.match.home ?? ""}
              awayLabel={data.featured.match.away ?? ""}
            />
          </div>
        </div>
      )}

      <p className="mt-4 text-[10px] leading-relaxed text-graphite-600">
        Sin córners ni tarjetas: ninguna fuente gratuita y sin cuenta con licencia adecuada las da
        (ver README). Todo lo anterior es probabilidad estadística real, nunca una cuota de
        apuestas.
      </p>
    </motion.aside>
  );
}
