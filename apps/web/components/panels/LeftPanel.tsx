"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import type { MouseEvent } from "react";

import { useHighlights } from "@/lib/HighlightsContext";
import { formatLatency } from "@/lib/formatLatency";

import CountUp from "../CountUp";
import NeuralCore3D from "./NeuralCore3D";

function StatRow({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-neon-cyan/10 py-2 text-sm last:border-0">
      <span className="text-graphite-500">{label}</span>
      <span className="data-stream font-mono font-semibold text-neon-cyan">
        <CountUp value={value} suffix={suffix} />
      </span>
    </div>
  );
}

function StreamBars() {
  return (
    <div className="mt-2 flex h-4 items-end justify-center gap-0.5">
      {Array.from({ length: 16 }).map((_, i) => (
        <div
          key={i}
          className="w-0.5 rounded-full bg-neon-cyan/70"
          style={{
            height: `${30 + ((i * 37) % 70)}%`,
            animation: `data-flicker ${1 + (i % 5) * 0.3}s ease-in-out infinite`,
            animationDelay: `${i * 0.05}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function LeftPanel() {
  const { data, loading, latencyMs } = useHighlights();

  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const translateX = useSpring(useTransform(x, [0, 1], [-10, 10]), { stiffness: 150, damping: 20 });
  const translateY = useSpring(useTransform(y, [0, 1], [-10, 10]), { stiffness: 150, damping: 20 });
  const tiltX = useSpring(useTransform(y, [0, 1], [10, -10]), { stiffness: 150, damping: 20 });
  const tiltY = useSpring(useTransform(x, [0, 1], [-10, 10]), { stiffness: 150, damping: 20 });

  function onMouseMove(event: MouseEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX - rect.left) / rect.width);
    y.set((event.clientY - rect.top) / rect.height);
  }

  function onMouseLeave() {
    x.set(0.5);
    y.set(0.5);
  }

  const telemetry = data?.telemetry;

  return (
    <motion.aside
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="gradient-border sticky top-20 h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-neon-cyan/20 bg-obsidian/80 p-5 shadow-[0_0_40px_-10px_rgba(0,255,136,0.25)] backdrop-blur-sm"
    >
      <p className="bg-gradient-to-r from-neon-emerald to-neon-cyan bg-clip-text text-xs font-semibold uppercase tracking-widest text-transparent">
        Motor Neuronal · Core Poisson
      </p>

      <motion.div
        style={{ x: translateX, y: translateY, rotateX: tiltX, rotateY: tiltY, transformPerspective: 1200 }}
      >
        <NeuralCore3D />
      </motion.div>

      <div className="mt-2 flex items-center justify-center gap-1.5 text-xs text-graphite-500">
        <span className={`pulse-dot h-2 w-2 rounded-full ${latencyMs !== null ? "bg-neon-emerald" : "bg-graphite-600"}`} />
        {latencyMs !== null ? `API en vivo · ${formatLatency(latencyMs)}` : "Conectando…"}
      </div>
      <StreamBars />

      <div className="mt-6">
        <p className="mb-1 text-[11px] uppercase tracking-wide text-graphite-500">
          Telemetría en vivo
        </p>
        {loading && !telemetry ? (
          <div className="skeleton h-32 animate-shimmer rounded-lg" />
        ) : telemetry ? (
          <div>
            <StatRow label="Ligas conectadas" value={telemetry.leagues_connected} />
            <StatRow label="Partidos cargados" value={telemetry.matches_loaded} />
            <StatRow label="Predicciones calculadas" value={telemetry.predictions_computed} />
            {telemetry.model_accuracy_pct !== null ? (
              <StatRow label="Acierto histórico del modelo" value={telemetry.model_accuracy_pct} suffix="%" />
            ) : (
              <p className="pt-2 text-xs text-graphite-600">
                Acierto histórico: muestra insuficiente todavía.
              </p>
            )}
            {telemetry.model_accuracy_sample > 0 && (
              <p className="mt-1 text-[10px] text-graphite-600">
                Backtesting real sobre {telemetry.model_accuracy_sample} partidos ya jugados
                (cada uno predicho solo con los partidos anteriores a él — nunca con su propio
                resultado).
              </p>
            )}
          </div>
        ) : null}
      </div>

      {data && data.unavailable.length > 0 && (
        <p className="mt-4 rounded-lg bg-amber-500/10 px-2.5 py-2 text-[11px] text-amber-300">
          {data.unavailable.length} liga(s) sin sincronizar ahora mismo por el límite de la fuente
          gratuita.
        </p>
      )}
    </motion.aside>
  );
}
