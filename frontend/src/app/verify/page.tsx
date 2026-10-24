"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

export default function VerifyPage() {
  const [quasi, setQuasi] = useState<string>("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = typeof window !== "undefined" ? getSession() : {};

  async function run() {
    if (!s.projectId || !s.fileId) {
      setErr("No project.");
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const qi = quasi.split(",").map((x) => x.trim()).filter(Boolean);
      setData(await api.verify(s.projectId, s.fileId, qi));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const report = data?.risk_report;
  const quality = data?.quality_report;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Verification report</h1>
      <p className="text-slate-600">
        An independent second scan of the transformed output. This is not a
        guarantee of safety.
      </p>

      <Card title="Quasi-identifier check (optional)">
        <label className="block text-sm" htmlFor="qi">
          Columns that could identify someone in combination (comma-separated,
          e.g. age, zip):
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id="qi"
            value={quasi}
            onChange={(e) => setQuasi(e.target.value)}
            className="flex-1 rounded border border-slate-300 px-3 py-2"
          />
          <button onClick={run} className="rounded border border-slate-300 px-4">
            Re-run
          </button>
        </div>
      </Card>

      {err && <p className="text-red-700">{err}</p>}
      {loading && <p>Running the second scan…</p>}

      {data && (
        <>
          <Card title="Export gate">
            {data.gate === "pass" ? (
              <p className="text-green-700">
                Passed. No value-level directly-identifying data remained in the
                output. Review items below may still need your judgment.
              </p>
            ) : (
              <div>
                <p className="font-medium text-red-700">
                  Blocked. Export is prevented until these are resolved:
                </p>
                <ul className="mt-1 list-disc pl-5 text-sm text-red-700">
                  {data.reasons.map((r: string, i: number) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <Card title="Residual findings (second scan)">
            {report.residual_findings.length === 0 ? (
              <p className="text-sm text-slate-600">None found.</p>
            ) : (
              <ul className="text-sm">
                {report.residual_findings.map((f: any, i: number) => (
                  <li key={i}>
                    {f.entity_type} ({f.category}) in {f.field ?? "text"}
                    {f.row != null ? ` row ${f.row}` : " (column-level hint)"}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-slate-500">
              Unreviewed: {report.unreviewed_count}
            </p>
          </Card>

          {report.risky_combinations?.length > 0 && (
            <Card title="Risky attribute combinations">
              <ul className="text-sm text-amber-800">
                {report.risky_combinations.map((c: any, i: number) => (
                  <li key={i}>{c.detail}</li>
                ))}
              </ul>
            </Card>
          )}

          {quality && (
            <Card title="Data-quality comparison">
              <ul className="text-sm text-slate-700">
                <li>
                  Rows: {quality.rows_before} → {quality.rows_after}
                </li>
                <li>
                  Columns: {quality.columns_before} → {quality.columns_after}
                </li>
                <li>Changed fields: {quality.changed_fields.join(", ") || "none"}</li>
              </ul>
            </Card>
          )}

          <Card title="Limitations">
            <ul className="list-disc pl-5 text-sm text-slate-600">
              {report.limitations.map((l: string, i: number) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </Card>

          <div className="flex justify-end">
            <Link
              href="/export"
              className="rounded bg-blue-700 px-4 py-2 text-white no-underline"
            >
              Next: export →
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
