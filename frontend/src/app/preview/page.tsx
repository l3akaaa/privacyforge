"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

export default function PreviewPage() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const s = typeof window !== "undefined" ? getSession() : {};

  useEffect(() => {
    if (!s.projectId || !s.fileId) {
      setErr("No project.");
      setLoading(false);
      return;
    }
    api
      .transform(s.projectId, s.fileId)
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <p>Applying your policy…</p>;
  if (err)
    return (
      <p className="text-red-700">
        {err} <Link href="/policy">Back to policy →</Link>
      </p>
    );

  const before = data.preview_before;
  const after = data.preview_after;
  const isTable = Array.isArray(before);
  const cols = isTable && before[0] ? Object.keys(before[0]) : [];

  function changed(row: number, col: string) {
    return String(before[row]?.[col]) !== String(after[row]?.[col]);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Before / after</h1>
      <p className="text-slate-600">
        {data.change_count} value(s) changed. Changed cells are highlighted.
      </p>

      <Card title="Comparison (first rows)">
        {isTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b text-slate-500">
                  <th className="py-2">#</th>
                  {cols.map((c) => (
                    <th key={c} className="px-2">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {before.map((_: any, r: number) => (
                  <tr key={r} className="border-b align-top">
                    <td className="py-1 text-slate-400">{r}</td>
                    {cols.map((c) => (
                      <td key={c} className="px-2">
                        {changed(r, c) ? (
                          <div>
                            <span className="block text-slate-400 line-through">
                              {String(before[r][c])}
                            </span>
                            <span className="block rounded bg-green-50 font-medium text-green-800">
                              {String(after[r][c])}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-700">{String(after[r][c])}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <h3 className="mb-1 font-semibold text-slate-500">Before</h3>
              <pre className="whitespace-pre-wrap">{String(before)}</pre>
            </div>
            <div>
              <h3 className="mb-1 font-semibold text-slate-500">After</h3>
              <pre className="whitespace-pre-wrap">{String(after)}</pre>
            </div>
          </div>
        )}
      </Card>

      <Card title="Actions applied">
        <ul className="text-sm text-slate-700">
          {Object.entries(data.operators_used).map(([k, v]) => (
            <li key={k}>
              {k}: <strong>{v as string}</strong>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex justify-end">
        <Link
          href="/verify"
          className="rounded bg-blue-700 px-4 py-2 text-white no-underline"
        >
          Next: run the safety check →
        </Link>
      </div>
    </div>
  );
}
