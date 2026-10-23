"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { useHighlights } from "@/lib/HighlightsContext";
import { formatLatency } from "@/lib/formatLatency";

import CountUp from "./CountUp";

const QUICK_LINKS = [
  { href: "/futbol", label: "Fútbol" },
  { href: "/baloncesto", label: "Baloncesto" },
  { href: "/tenis", label: "Tenis" },
  { href: "/equipos", label: "Equipos" },
];

export default function PlatformFooter() {
  const { data, latencyMs, lastUpdated, loading, refresh } = useHighlights();
  const telemetry = data?.telemetry;

  return (
    <footer className="relative mt-16 overflow-hidden border-t border-graphite-800">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-emerald/10 via-electric/5 to-transparent"
      />
      <div className="relative mx-auto max-w-6xl px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="gradient-border rounded-3xl border border-graphite-800 bg-graphite-900/70 p-6 backdrop-blur-md sm:p-8"
        >
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="rounded-full bg-gradient-to-r from-emerald via-electric to-purple-500 p-[1.5px]">
              <div className="rounded-full bg-graphite-950 px-5 py-1.5">
                <span className="bg-gradient-to-r from-emerald-bright via-electric-bright to-purple-400 bg-clip-text text-xs font-extrabold tracking-widest text-transparent">
                  SPORTPULSE PRO · ANALYTICS ENGINE
                </span>
              </div>
            </div>
            <p className="max-w-xl text-sm text-graphite-400">
              Motor de predicción construido sobre fuentes 100% gratuitas y verificadas, sin cuotas
              de apuestas ni datos inventados — cada número de esta página se calcula sobre
              resultados reales.
            </p>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Ligas conectadas", value: telemetry?.leagues_connected ?? 0 },
              { label: "Partidos cargados", value: telemetry?.matches_loaded ?? 0 },
              { label: "Predicciones calculadas", value: telemetry?.predictions_computed ?? 0 },
              {
                label: "Acierto histórico",
                value: telemetry?.model_accuracy_pct ?? 0,
                suffix: telemetry?.model_accuracy_pct !== null && telemetry?.model_accuracy_pct !== undefined ? "%" : "",
              },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="font-mono text-2xl font-extrabold text-graphite-50">
                  <CountUp value={stat.value} suffix={stat.suffix ?? ""} />
                </p>
                <p className="mt-1 text-[11px] text-graphite-500">{stat.label}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-4 border-t border-graphite-800 pt-5 text-xs">
            <div className="flex items-center gap-1.5 text-graphite-400">
              <span className={`pulse-dot h-2 w-2 rounded-full ${latencyMs !== null ? "bg-emerald-bright" : "bg-graphite-600"}`} />
              {latencyMs !== null ? `Servidor en vivo · ${formatLatency(latencyMs)}` : "Conectando…"}
            </div>
            {lastUpdated && (
              <span className="text-graphite-600">
                Última sincronización: {lastUpdated.toLocaleTimeString("es-ES")}
              </span>
            )}
            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              className="rounded-full bg-emerald/15 px-3 py-1 font-medium text-emerald-bright ring-1 ring-emerald/40 transition-colors hover:bg-emerald/25 disabled:opacity-50"
            >
              {loading ? "Sincronizando…" : "Sincronizar"}
            </button>
          </div>

          <nav className="mt-5 flex flex-wrap justify-center gap-2">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-full bg-graphite-800 px-3 py-1 text-xs text-graphite-300 transition-colors hover:bg-graphite-700 hover:text-graphite-100"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </motion.div>

        <p className="mt-6 text-center text-[11px] text-graphite-700">
          SportPulse — proyecto independiente, 0 €/mes, sin cuentas de pago. Datos de OpenLigaDB
          (ODbL), TheSportsDB (clave pública gratuita) y OpenFootball (dominio público).
        </p>
      </div>
    </footer>
  );
}
