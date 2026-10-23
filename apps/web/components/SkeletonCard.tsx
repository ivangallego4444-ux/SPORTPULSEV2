export default function SkeletonCard() {
  return (
    <div className="rounded-xl border border-graphite-800 bg-graphite-900 p-4">
      <div className="flex items-center justify-between">
        <div className="skeleton h-3 w-24 animate-shimmer rounded" />
        <div className="skeleton h-4 w-16 animate-shimmer rounded-full" />
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="skeleton h-4 w-28 animate-shimmer rounded" />
        <div className="skeleton h-6 w-12 animate-shimmer rounded" />
        <div className="skeleton h-4 w-28 animate-shimmer rounded" />
      </div>
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
