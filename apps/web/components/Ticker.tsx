import type { HighlightMatch } from "@/lib/types";

import CrestImage from "./CrestImage";

function TickerItem({ highlight }: { highlight: HighlightMatch }) {
  const { match } = highlight;
  const hasScore = match.home_score !== null && match.away_score !== null;
  return (
    <div className="flex shrink-0 items-center gap-2 border-r border-graphite-800 px-4 py-2 text-sm">
      <span className="text-[10px] font-semibold uppercase text-graphite-500">
        {match.competition_name}
      </span>
      <CrestImage src={match.home_crest} alt="" className="h-4 w-4 object-contain" />
      <span className="text-graphite-200">{match.home ?? match.title}</span>
      {hasScore && (
        <span className="font-mono font-bold text-emerald-bright">
          {match.home_score}-{match.away_score}
        </span>
      )}
      {match.away && (
        <>
          <span className="text-graphite-200">{match.away}</span>
          <CrestImage src={match.away_crest} alt="" className="h-4 w-4 object-contain" />
        </>
      )}
    </div>
  );
}

export default function Ticker({ highlights }: { highlights: HighlightMatch[] }) {
  if (highlights.length === 0) return null;
  // Duplicated once for a seamless CSS-driven loop.
  const looped = [...highlights, ...highlights];

  return (
    <div className="overflow-hidden rounded-xl border border-graphite-800 bg-graphite-900">
      <div className="flex w-max animate-[ticker_35s_linear_infinite] hover:[animation-play-state:paused]">
        {looped.map((h, i) => (
          <TickerItem key={`${h.match.id}-${i}`} highlight={h} />
        ))}
      </div>
    </div>
  );
}
