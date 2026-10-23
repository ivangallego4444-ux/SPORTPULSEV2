interface EmptyStateProps {
  title: string;
  description?: string;
  tone?: "info" | "error";
}

export default function EmptyState({ title, description, tone = "info" }: EmptyStateProps) {
  const toneClasses =
    tone === "error"
      ? "border-red-900/50 bg-red-950/40 text-red-300"
      : "border-graphite-800 bg-graphite-900 text-graphite-400";

  return (
    <div className={`rounded-xl border px-4 py-6 text-center ${toneClasses}`}>
      <p className={`font-medium ${tone === "error" ? "text-red-200" : "text-graphite-200"}`}>
        {title}
      </p>
      {description && <p className="mt-1 text-sm opacity-80">{description}</p>}
    </div>
  );
}
