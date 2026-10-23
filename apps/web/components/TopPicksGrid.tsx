"use client";

import { motion } from "framer-motion";

import type { HighlightMatch } from "@/lib/types";

import CountUp from "./CountUp";
import CrestImage from "./CrestImage";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export default function TopPicksGrid({
  title,
  highlights,
  statKey,
  accentClass = "text-emerald-bright",
}: {
  title: string;
  highlights: HighlightMatch[];
  statKey: "favorite" | "over_2_5" | "btts";
  accentClass?: string;
}) {
  if (highlights.length === 0) {
    return (
      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">
          {title}
        </h3>
        <p className="rounded-xl border border-graphite-800 bg-graphite-900 px-4 py-6 text-center text-sm text-graphite-500">
          Sin datos suficientes ahora mismo para calcular esto.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-graphite-500">{title}</h3>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      >
        {highlights.map((h) => {
          const prediction = h.prediction!;
          const pct =
            statKey === "favorite"
              ? Math.max(prediction.home_win_pct, prediction.away_win_pct)
              : statKey === "over_2_5"
                ? prediction.over_2_5_pct
                : prediction.btts_yes_pct;
          const favoriteTeam =
            statKey === "favorite"
              ? prediction.home_win_pct >= prediction.away_win_pct
                ? h.match.home
                : h.match.away
              : null;

          return (
            <motion.div
              key={h.match.id}
              variants={item}
              whileHover={{ y: -2, boxShadow: "0 0 0 1px rgba(16,185,129,0.35)" }}
              className="rounded-xl border border-graphite-800 bg-graphite-900 p-3"
            >
              <div className="flex items-center gap-1.5 text-[11px] text-graphite-500">
                <CrestImage src={h.match.home_crest} alt="" className="h-4 w-4 object-contain" />
                <span className="truncate">{h.match.home}</span>
                <span>-</span>
                <span className="truncate">{h.match.away}</span>
                <CrestImage src={h.match.away_crest} alt="" className="h-4 w-4 object-contain" />
              </div>
              <p className={`mt-1.5 font-mono text-xl font-bold ${accentClass}`}>
                <CountUp value={pct} decimals={0} suffix="%" />
              </p>
              <p className="truncate text-[11px] text-graphite-500">
                {favoriteTeam ? `Gana ${favoriteTeam}` : h.match.competition_name}
              </p>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
