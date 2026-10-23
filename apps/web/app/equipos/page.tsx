"use client";

import { useState } from "react";

import EmptyState from "@/components/EmptyState";
import TeamHistoryView from "@/components/TeamHistoryView";
import TeamSearch from "@/components/TeamSearch";
import type { TeamSummary } from "@/lib/types";

export default function EquiposPage() {
  const [selected, setSelected] = useState<TeamSummary | null>(null);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-extrabold text-graphite-50">Explorador de equipos</h1>
      <p className="mb-5 text-sm text-graphite-400">
        Historial real por equipo — últimos 10, 20, 30 partidos o toda la temporada ya cargada,
        filtrable por local/visitante, con medias y porcentajes reales. Solo encuentra equipos de
        competiciones que ya se han abierto al menos una vez en la pestaña Fútbol.
      </p>

      <TeamSearch onSelect={setSelected} />

      <div className="mt-6">
        {selected ? (
          <TeamHistoryView key={`${selected.competition_slug}-${selected.team_id}`} team={selected} />
        ) : (
          <EmptyState title="Busca un equipo para ver su historial real." />
        )}
      </div>
    </div>
  );
}
