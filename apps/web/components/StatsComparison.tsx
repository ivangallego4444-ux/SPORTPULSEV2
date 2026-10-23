"use client";

import { motion } from "framer-motion";

import type { MatchStats } from "@/lib/types";

export default function StatsComparison({ stats }: { stats: MatchStats }) {
  return (
    <div className="space-y-3">
      {stats.lines.map((line) => {
        const total = line.home_value + line.away_value || 1;
        const homePct = (line.home_value / total) * 100;
        return (
          <div key={line.label}>
            <div className="flex justify-between text-xs text-graphite-400">
              <span className="font-mono">{line.home_value}</span>
              <span>{line.label}</span>
              <span className="font-mono">{line.away_value}</span>
            </div>
            <div className="mt-1 flex h-1.5 overflow-hidden rounded-full bg-graphite-800">
              <motion.div
                className="h-full bg-emerald"
                initial={{ width: 0 }}
                animate={{ width: `${homePct}%` }}
                transition={{ duration: 0.5 }}
              />
              <motion.div
                className="h-full bg-electric"
                initial={{ width: 0 }}
                animate={{ width: `${100 - homePct}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
