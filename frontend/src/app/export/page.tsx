"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

function toCsv(columns: string[], rows: any[]): string {
  const esc = (v: any) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = columns.map(esc).join(",");
  const body = rows.map((r) => columns.map((c) => esc(r[c])).join(",")).join("\n");
  return `${head}\n${body}`;
}

function download(name: string, text: string, type = "text/plain") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ExportPage() {
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string[] | null>(null);
  const s = typeof window !== "undefined" ? getSession() : {};

  async function doExport(override: boolean) {
    if (!s.projectId || !s.fileId) {
      setErr("No project.");
      return;
    }
    setErr(null);
    setBlocked(null);
    try {
      const r = await api.exportData(s.projectId, s.fileId, override);
      setResult(r);
    } catch (e: any) {
      if (e.status === 409) {
        setBlocked(e.detail?.reasons || ["Blocked by the privacy gate."]);
      } else {
        setErr(e.message);
      }
    }
  }

  function downloadData() {
    const ex = result.export;
    if (ex.columns) {
      download("deidentified.csv", toCsv(ex.columns, ex.rows), "text/csv");
    } else {
      download("deidentified.txt", ex.text);
    }
  }

  function downloadReport() {
    download(
      "audit_report.json",
      JSON.stringify(result.audit, null, 2),
      "application/json",
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Export</h1>
      <p className="text-slate-600">
        Download the processed dataset and an audit report. Export is blocked if
        the safety gate fails.
      </p>

      {!result && !blocked && (
        <Card title="Create export">
          <button
            onClick={() => doExport(false)}
            className="rounded bg-blue-700 px-4 py-2 text-white"
          >
            Export now
          </button>
        </Card>
      )}

      {blocked && (
        <Card title="Export blocked by the safety gate">
          <ul className="list-disc pl-5 text-sm text-red-700">
            {blocked.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-slate-600">
            Go back and adjust your policy to resolve these, then re-run
            verification. An authorized override exists but is recorded in the
            audit report and should be used only with documented justification.
          </p>
          <button
            onClick={() => doExport(true)}
            className="mt-3 rounded border border-red-300 px-4 py-2 text-sm text-red-700"
          >
            Override and export anyway (recorded)
          </button>
        </Card>
      )}

      {result && (
        <Card title="Export ready">
          {result.override_used && (
            <p className="mb-2 text-sm text-red-700">
              Note: the safety gate was overridden. This is recorded in the audit
              report.
            </p>
          )}
          <div className="flex gap-3">
            <button
              onClick={downloadData}
              className="rounded bg-blue-700 px-4 py-2 text-white"
            >
              Download dataset
            </button>
            <button
              onClick={downloadReport}
              className="rounded border border-slate-300 px-4 py-2"
            >
              Download audit report
            </button>
          </div>
        </Card>
      )}

      {err && <p className="text-red-700">{err}</p>}
    </div>
  );
}
