"use client";
import type { Category } from "@/lib/api";

const CAT_LABEL: Record<Category, string> = {
  pii: "Directly identifying (PII)",
  sensitive: "Sensitive / confidential",
  quasi: "Quasi-identifier",
};

const CAT_CLASS: Record<Category, string> = {
  pii: "bg-red-100 text-red-800 border-red-300",
  sensitive: "bg-amber-100 text-amber-900 border-amber-300",
  quasi: "bg-blue-100 text-blue-800 border-blue-300",
};

export function CategoryBadge({ category }: { category: Category }) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs ${CAT_CLASS[category]}`}
      title={CAT_LABEL[category]}
    >
      {CAT_LABEL[category]}
    </span>
  );
}

// Show confidence as a qualitative band, never as an exact probability (R2.8).
export function ConfidenceBand({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-slate-400">n/a</span>;
  const band = score >= 0.8 ? "High" : score >= 0.5 ? "Medium" : "Low";
  const cls =
    band === "High"
      ? "text-green-700"
      : band === "Medium"
        ? "text-amber-700"
        : "text-slate-500";
  return (
    <span className={`text-xs ${cls}`} title="Qualitative band, not an exact probability">
      {band} confidence
    </span>
  );
}

export function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}
