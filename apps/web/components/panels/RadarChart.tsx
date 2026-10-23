"use client";

import { motion } from "framer-motion";

import type { MatchPrediction } from "@/lib/types";

const AXES = ["Ataque", "Victoria", "Solidez"] as const;
const SIZE = 140;
const CENTER = SIZE / 2;
const MAX_RADIUS = 56;

function axisPoint(index: number, value: number): [number, number] {
  // value in 0..100, index picks the axis angle (3 axes, 120° apart, starting at top).
  const angle = (Math.PI * 2 * index) / AXES.length - Math.PI / 2;
  const radius = (Math.max(0, Math.min(value, 100)) / 100) * MAX_RADIUS;
  return [CENTER + radius * Math.cos(angle), CENTER + radius * Math.sin(angle)];
}

function polygonPoints(values: number[]): string {
  return values.map((v, i) => axisPoint(i, v).join(",")).join(" ");
}

/** A real 3-axis radar comparing home vs away on values derived straight
 * from the Poisson prediction already computed (expected goals, win
 * probability, defensive solidity = inverse of the opponent's expected
 * goals) — no separate data source, no fabricated axis. */
export default function RadarChart({
  prediction,
  homeLabel,
  awayLabel,
}: {
  prediction: MatchPrediction;
  homeLabel: string;
  awayLabel: string;
}) {
  const maxGoals = Math.max(prediction.expected_goals_home, prediction.expected_goals_away, 1);
  const homeValues = [
    (prediction.expected_goals_home / maxGoals) * 100,
    prediction.home_win_pct,
    100 - (prediction.expected_goals_away / maxGoals) * 100,
  ];
  const awayValues = [
    (prediction.expected_goals_away / maxGoals) * 100,
    prediction.away_win_pct,
    100 - (prediction.expected_goals_home / maxGoals) * 100,
  ];

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-36 w-36">
        {[0.33, 0.66, 1].map((scale) => (
          <polygon
            key={scale}
            points={polygonPoints([100 * scale, 100 * scale, 100 * scale])}
            fill="none"
            stroke="rgba(0,240,255,0.15)"
            strokeWidth={1}
          />
        ))}
        {AXES.map((_, i) => {
          const [x, y] = axisPoint(i, 100);
          return (
            <line key={i} x1={CENTER} y1={CENTER} x2={x} y2={y} stroke="rgba(0,240,255,0.15)" strokeWidth={1} />
          );
        })}

        <motion.polygon
          points={polygonPoints(awayValues)}
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{ transformOrigin: `${CENTER}px ${CENTER}px` }}
          fill="rgba(0,240,255,0.18)"
          stroke="#00f0ff"
          strokeWidth={1.5}
        />
        <motion.polygon
          points={polygonPoints(homeValues)}
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
          style={{ transformOrigin: `${CENTER}px ${CENTER}px` }}
          fill="rgba(0,255,136,0.18)"
          stroke="#00ff88"
          strokeWidth={1.5}
        />

        {AXES.map((label, i) => {
          const [x, y] = axisPoint(i, 118);
          return (
            <text
              key={label}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-graphite-500"
              fontSize={9}
            >
              {label}
            </text>
          );
        })}
      </svg>
      <div className="mt-1 flex gap-4 text-[10px]">
        <span className="flex items-center gap-1 text-neon-emerald">
          <span className="h-1.5 w-1.5 rounded-full bg-neon-emerald" /> {homeLabel}
        </span>
        <span className="flex items-center gap-1 text-neon-cyan">
          <span className="h-1.5 w-1.5 rounded-full bg-neon-cyan" /> {awayLabel}
        </span>
      </div>
    </div>
  );
}
