"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Finding } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card, CategoryBadge, ConfidenceBand } from "@/components/ui";

export default function ReviewPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [removed, setRemoved] = useState<Set<number>>(new Set());
  const s = typeof window !== "undefined" ? getSession() : {};

  useEffect(() => {
    if (!s.projectId || !s.fileId) {
      setErr("No project. Upload a file first.");
      setLoading(false);
      return;
    }
    api
      .detect(s.projectId, s.fileId)
      .then((r) => {
        setFindings(r.findings);
        setSummary(r.summary);
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <p>Scanning for sensitive information…</p>;
  if (err)
    return (
      <p className="text-red-700">
        {err} <Link href="/upload">Go to upload →</Link>
      </p>
    );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Detection review</h1>
      <p className="text-slate-600">
        These are candidates, not certainties. Confidence is shown as a band, not
        an exact probability. Uncheck anything that is a false positive.
      </p>

      {summary && (
        <Card title="Summary">
          <div className="flex flex-wrap gap-4 text-sm">
            <span>Total findings: {summary.total}</span>
            <span>Need review: {summary.review_needed}</span>
            {Object.entries(summary.by_category).map(([k, v]) => (
              <span key={k}>
                {k}: {v as number}
              </span>
            ))}
          </div>
        </Card>
      )}

      <Card title="Findings">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="py-2">Keep</th>
              <th>Type</th>
              <th>Category</th>
              <th>Where</th>
              <th>Preview</th>
              <th>Confidence</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f, i) => (
              <tr
                key={i}
                className={`border-b ${removed.has(i) ? "opacity-40" : ""}`}
              >
                <td className="py-2">
                  <input
                    type="checkbox"
                    checked={!removed.has(i)}
                    aria-label={`Keep ${f.entity_type} finding`}
                    onChange={(e) => {
                      const next = new Set(removed);
                      e.target.checked ? next.delete(i) : next.add(i);
                      setRemoved(next);
                    }}
                  />
                </td>
                <td className="font-medium">{f.entity_type}</td>
                <td>
                  <CategoryBadge category={f.category} />
                </td>
                <td className="text-slate-600">
                  {f.field ?? "text"}
                  {f.row != null ? ` · row ${f.row}` : ""}
                </td>
                <td className="font-mono text-xs">{f.value_preview}</td>
                <td>
                  <ConfidenceBand score={f.score} />
                  {f.review_needed && (
                    <span className="ml-1 text-xs text-amber-700">· review</span>
                  )}
                </td>
                <td className="text-xs text-slate-500">{f.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {findings.length === 0 && (
          <p className="text-sm text-slate-500">No findings detected.</p>
        )}
      </Card>

      <div className="flex justify-end">
        <Link
          href="/policy"
          className="rounded bg-blue-700 px-4 py-2 text-white no-underline"
        >
          Next: choose what to do →
        </Link>
      </div>
    </div>
  );
}
