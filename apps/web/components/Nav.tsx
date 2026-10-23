"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Inicio" },
  { href: "/futbol", label: "Fútbol" },
  { href: "/baloncesto", label: "Baloncesto" },
  { href: "/tenis", label: "Tenis" },
  { href: "/equipos", label: "Equipos" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-graphite-800 bg-graphite-950/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-5xl items-center gap-1 overflow-x-auto px-4 py-3 sm:gap-2">
        <span className="mr-3 shrink-0 bg-gradient-to-r from-emerald-bright to-electric-bright bg-clip-text font-extrabold tracking-tight text-transparent">
          SportPulse
        </span>
        {LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="relative shrink-0 rounded-full px-3 py-1.5 text-sm font-medium text-graphite-300 transition-colors hover:text-graphite-100"
            >
              {active && (
                <motion.span
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-full bg-emerald/15 ring-1 ring-emerald/40"
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                />
              )}
              <span className={`relative ${active ? "text-emerald-bright" : ""}`}>
                {link.label}
              </span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
