"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setSession } from "@/lib/session";
import { Card } from "@/components/ui";

export default function UploadPage() {
  const router = useRouter();
  const [name, setName] = useState("My project");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  async function handleUpload() {
    if (!file) {
      setErr("Please choose a file first.");
      return;
    }
    setBusy(true);
    setErr(null);
    setWarnings([]);
    try {
      const proj = await api.createProject(name);
      const up = await api.uploadFile(proj.project_id, file);
      setSession({
        projectId: proj.project_id,
        projectName: proj.name,
        fileId: up.file_id,
        filename: file.name,
        schema: up.schema,
      });
      setWarnings(up.warnings || []);
      router.push("/review");
    } catch (e: any) {
      setErr(e.message || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Upload a dataset</h1>

      <Card title="Supported files and limits">
        <ul className="list-disc pl-5 text-sm text-slate-700">
          <li>Formats: plain text (.txt), CSV, Excel (.xlsx), JSON.</li>
          <li>Size limit: 25 MB by default.</li>
          <li>
            Excel: formulas and hidden sheets are not processed; only cell values
            are read. Unsafe workbooks are rejected.
          </li>
          <li>Use synthetic or test data, not real records.</li>
        </ul>
      </Card>

      <Card title="Choose a file">
        <label className="block text-sm font-medium" htmlFor="pname">
          Project name
        </label>
        <input
          id="pname"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mb-4 mt-1 w-full rounded border border-slate-300 px-3 py-2"
        />
        <label className="block text-sm font-medium" htmlFor="file">
          Dataset file
        </label>
        <input
          id="file"
          type="file"
          accept=".txt,.csv,.xlsx,.json"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="mt-1 block w-full text-sm"
        />
        {err && <p className="mt-3 text-sm text-red-700">{err}</p>}
        <button
          onClick={handleUpload}
          disabled={busy}
          className="mt-4 rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Uploading…" : "Upload and detect"}
        </button>
        {warnings.length > 0 && (
          <ul className="mt-3 list-disc pl-5 text-sm text-amber-800">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
