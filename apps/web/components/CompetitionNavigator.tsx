"use client";

import { motion } from "framer-motion";
import { useMemo, useState } from "react";

import type { Competition } from "@/lib/types";

import CrestImage from "./CrestImage";

type FilterKey = "all" | "top5" | "uefa" | "spain" | "other";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "top5", label: "🔥 Top 5 Ligas" },
  { key: "uefa", label: "🇪🇺 UEFA Europa" },
  { key: "spain", label: "🇪🇸 España" },
  { key: "other", label: "🌍 Otras Ligas" },
];

const TOP5_SLUGS = new Set(["laliga", "premier-league", "serie-a", "ligue-1", "bundesliga"]);
const UEFA_SLUGS = new Set(["champions-league", "europa-league", "conference-league"]);

function matchesFilter(competition: Competition, filter: FilterKey): boolean {
  switch (filter) {
    case "all":
      return true;
    case "top5":
      return TOP5_SLUGS.has(competition.slug);
    case "uefa":
      return UEFA_SLUGS.has(competition.slug);
    case "spain":
      return competition.country === "España";
    case "other":
      return !TOP5_SLUGS.has(competition.slug) && !UEFA_SLUGS.has(competition.slug) && competition.country !== "España";
  }
}

export default function CompetitionNavigator({
  competitions,
  selected,
  onSelect,
}: {
  competitions: Competition[];
  selected: string;
  onSelect: (slug: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return competitions.filter((c) => {
      if (!matchesFilter(c, filter)) return false;
      if (!q) return true;
      return c.name.toLowerCase().includes(q) || (c.country ?? "").toLowerCase().includes(q);
    });
  }, [competitions, query, filter]);

  return (
    <div className="mb-6 space-y-3">
      <div className="relative">
        <svg
          aria-hidden
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-graphite-500"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar competición o país..."
          className="w-full rounded-xl border border-graphite-800 bg-graphite-900 py-2.5 pl-10 pr-3 text-sm text-graphite-100 placeholder:text-graphite-600 focus:border-emerald/50 focus:outline-none focus:ring-1 focus:ring-emerald/30"
        />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.key
                ? "bg-emerald/15 text-emerald-bright ring-1 ring-emerald/40"
                : "bg-graphite-900 text-graphite-400 ring-1 ring-graphite-800 hover:text-graphite-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <p className="py-4 text-center text-sm text-graphite-500">
          Sin competiciones que coincidan con la búsqueda.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {visible.map((competition) => {
            const active = competition.slug === selected;
            return (
              <motion.button
                key={competition.slug}
                type="button"
                onClick={() => onSelect(competition.slug)}
                whileHover={{ y: -2 }}
                className={`relative flex items-center gap-2.5 overflow-hidden rounded-xl border px-3 py-2.5 text-left backdrop-blur-sm transition-colors ${
                  active
                    ? "border-emerald/50 bg-emerald/10 shadow-glow"
                    : "border-graphite-800 bg-graphite-900/70 hover:border-graphite-700"
                }`}
              >
                {competition.badge_url ? (
                  <CrestImage
                    src={competition.badge_url}
                    alt=""
                    className="h-8 w-8 shrink-0 object-contain"
                  />
                ) : (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-graphite-800 text-xs font-bold text-graphite-400">
                    {competition.name.slice(0, 1)}
                  </div>
                )}
                <div className="min-w-0">
                  <p
                    className={`truncate text-xs font-semibold ${
                      active ? "text-emerald-bright" : "text-graphite-100"
                    }`}
                  >
                    {competition.name}
                  </p>
                  {competition.country && (
                    <p className="truncate text-[10px] text-graphite-500">{competition.country}</p>
                  )}
                </div>
              </motion.button>
            );
          })}
        </div>
      )}
    </div>
  );
}
