"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

import { searchTeams } from "@/lib/api";
import { useDebounce } from "@/lib/useDebounce";
import type { TeamSummary } from "@/lib/types";

import CrestImage from "./CrestImage";

export default function TeamSearch({ onSelect }: { onSelect: (team: TeamSummary) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TeamSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.trim().length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    searchTeams(debouncedQuery)
      .then((teams) => {
        if (!cancelled) setResults(teams);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Busca un equipo real (ej. Barcelona, Arsenal, Bayern)…"
        className="w-full rounded-xl border border-graphite-700 bg-graphite-900 px-4 py-3 text-graphite-100 placeholder:text-graphite-500 focus:border-emerald/50 focus:outline-none focus:ring-2 focus:ring-emerald/20"
      />

      <AnimatePresence>
        {open && query.trim().length >= 2 && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="absolute z-10 mt-1 max-h-80 w-full overflow-y-auto rounded-xl border border-graphite-700 bg-graphite-900 shadow-card"
          >
            {loading && <p className="px-4 py-3 text-sm text-graphite-500">Buscando…</p>}
            {!loading && results.length === 0 && (
              <p className="px-4 py-3 text-sm text-graphite-500">
                Sin resultados entre los equipos ya cargados. Prueba a abrir primero su liga en la
                pestaña Fútbol.
              </p>
            )}
            {!loading &&
              results.map((team) => (
                <button
                  key={`${team.competition_slug}-${team.team_id}`}
                  type="button"
                  onMouseDown={() => {
                    onSelect(team);
                    setQuery(team.team_name);
                    setOpen(false);
                  }}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-graphite-800"
                >
                  <CrestImage src={team.crest_url} alt="" className="h-6 w-6 object-contain" />
                  <span className="flex-1">
                    <span className="block text-sm font-medium text-graphite-100">{team.team_name}</span>
                    <span className="block text-xs text-graphite-500">{team.competition_name}</span>
                  </span>
                </button>
              ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
