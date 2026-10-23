// Real competition-format rules (who qualifies for what), not computed
// from any match data — public, well-known facts about each competition's
// own structure. Kept intentionally simple: for a couple of leagues whose
// exact European slot count can shift year to year with UEFA's
// coefficient-based extra places, this only colors the *shape* every fan
// recognizes (top block / mid block / bottom block) rather than claiming
// certainty about an exact edge case this project hasn't verified live.

export type ZoneTone = "champions" | "europa" | "conference" | "promotion" | "playoff" | "relegation";

export interface ZoneBand {
  tone: ZoneTone;
  from: number;
  to: number;
}

export const ZONE_LABELS: Record<ZoneTone, string> = {
  champions: "Champions League",
  europa: "Europa League",
  conference: "Conference League",
  promotion: "Ascenso directo",
  playoff: "Playoff",
  relegation: "Descenso",
};

export const ZONE_DOT_CLASSES: Record<ZoneTone, string> = {
  champions: "bg-emerald-bright",
  europa: "bg-electric-bright",
  conference: "bg-neon-purple",
  promotion: "bg-emerald-bright",
  playoff: "bg-neon-gold",
  relegation: "bg-red-400",
};

const TOP5_EUROPEAN_ZONES: ZoneBand[] = [
  { tone: "champions", from: 1, to: 4 },
  { tone: "europa", from: 5, to: 5 },
  { tone: "conference", from: 6, to: 6 },
  { tone: "relegation", from: 18, to: 20 },
];

const SWISS_FORMAT_ZONES: ZoneBand[] = [
  { tone: "champions", from: 1, to: 8 }, // pasa directo a octavos
  { tone: "europa", from: 9, to: 24 }, // ronda de play-off
  { tone: "relegation", from: 25, to: 36 }, // eliminado
];

const COMPETITION_ZONES: Record<string, ZoneBand[]> = {
  laliga: TOP5_EUROPEAN_ZONES,
  "premier-league": TOP5_EUROPEAN_ZONES,
  "serie-a": TOP5_EUROPEAN_ZONES,
  "ligue-1": TOP5_EUROPEAN_ZONES,
  bundesliga: [
    { tone: "champions", from: 1, to: 4 },
    { tone: "europa", from: 5, to: 5 },
    { tone: "conference", from: 6, to: 6 },
    { tone: "playoff", from: 16, to: 16 },
    { tone: "relegation", from: 17, to: 18 },
  ],
  "champions-league": SWISS_FORMAT_ZONES,
  "europa-league": SWISS_FORMAT_ZONES,
  "conference-league": SWISS_FORMAT_ZONES,
  segunda: [
    { tone: "promotion", from: 1, to: 2 },
    { tone: "playoff", from: 3, to: 6 },
    { tone: "relegation", from: 19, to: 22 },
  ],
  championship: [
    { tone: "promotion", from: 1, to: 2 },
    { tone: "playoff", from: 3, to: 6 },
    { tone: "relegation", from: 22, to: 24 },
  ],
  "2-bundesliga": [
    { tone: "promotion", from: 1, to: 2 },
    { tone: "playoff", from: 3, to: 3 },
    { tone: "relegation", from: 16, to: 18 },
  ],
  "primeira-liga": [{ tone: "relegation", from: 16, to: 18 }],
  eredivisie: [{ tone: "relegation", from: 16, to: 18 }],
};

export function zoneForRank(competitionSlug: string, rank: number): ZoneBand | null {
  const bands = COMPETITION_ZONES[competitionSlug];
  if (!bands) return null;
  return bands.find((b) => rank >= b.from && rank <= b.to) ?? null;
}

export function zoneBarClass(tone: ZoneTone): string {
  switch (tone) {
    case "champions":
      return "bg-emerald-bright";
    case "europa":
      return "bg-electric-bright";
    case "conference":
      return "bg-neon-purple";
    case "promotion":
      return "bg-emerald-bright";
    case "playoff":
      return "bg-neon-gold";
    case "relegation":
      return "bg-red-400";
  }
}
