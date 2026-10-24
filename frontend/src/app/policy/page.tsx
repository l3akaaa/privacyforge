"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

const OPERATORS = ["redact", "mask", "tokenize", "synthetic", "generalize", "retain"];

export default function PolicyPage() {
  const [presets, setPresets] = useState<Record<string, any>>({});
  const [policy, setPolicy] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = typeof window !== "undefined" ? getSession() : {};

  useEffect(() => {
    api.presets().then(setPresets).catch(() => {});
    if (s.projectId) api.getPolicy(s.projectId).then((r) => setPolicy(r.policy)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyPreset(name: string) {
    if (!s.projectId) return;
    const r = await api.setPolicy(s.projectId, { preset_name: name });
    setPolicy(r.policy);
    setSaved(true);
  }

  async function save() {
    if (!s.projectId || !policy) return;
    try {
      const r = await api.setPolicy(s.projectId, { policy });
      setPolicy(r.policy);
      setSaved(true);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  function updateRule(idx: number, patch: any) {
    const rules = [...policy.rules];
    rules[idx] = { ...rules[idx], ...patch };
    setPolicy({ ...policy, rules });
  }

  function addRule() {
    setPolicy({
      ...policy,
      rules: [
        ...policy.rules,
        { match_type: "column", match_value: "", operator: "redact", params: {} },
      ],
    });
  }

  if (!s.projectId)
    return (
      <p className="text-red-700">
        No project. <Link href="/upload">Upload first →</Link>
      </p>
    );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Privacy policy editor</h1>
      <p className="text-slate-600">
        Decide what happens to each kind of data. Start from a preset, then adjust.
      </p>

      <Card title="Presets (starting points, not compliance certifications)">
        <div className="flex flex-wrap gap-2">
          {Object.keys(presets).map((name) => (
            <button
              key={name}
              onClick={() => applyPreset(name)}
              className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100"
            >
              {name.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        {policy?.disclaimer && (
          <p className="mt-3 text-xs text-amber-800">{policy.disclaimer}</p>
        )}
      </Card>

      {policy && (
        <Card title="Rules">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2">Match by</th>
                <th>Value</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {policy.rules.map((r: any, i: number) => (
                <tr key={i} className="border-b">
                  <td className="py-2">
                    <select
                      value={r.match_type}
                      aria-label="Match by"
                      onChange={(e) => updateRule(i, { match_type: e.target.value })}
                      className="rounded border border-slate-300 px-2 py-1"
                    >
                      <option value="column">column</option>
                      <option value="entity">entity type</option>
                      <option value="category">category</option>
                    </select>
                  </td>
                  <td>
                    <input
                      value={r.match_value}
                      aria-label="Match value"
                      onChange={(e) => updateRule(i, { match_value: e.target.value })}
                      className="w-40 rounded border border-slate-300 px-2 py-1"
                    />
                  </td>
                  <td>
                    <select
                      value={r.operator}
                      aria-label="Action"
                      onChange={(e) => updateRule(i, { operator: e.target.value })}
                      className="rounded border border-slate-300 px-2 py-1"
                    >
                      {OPERATORS.map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex items-center gap-3">
            <button onClick={addRule} className="text-sm text-blue-700">
              + Add rule
            </button>
            <span className="text-xs text-slate-500">
              Default action: {policy.default_operator}
            </span>
          </div>
        </Card>
      )}

      {err && <p className="text-red-700">{err}</p>}
      <div className="flex items-center justify-end gap-3">
        {saved && <span className="text-sm text-green-700">Saved.</span>}
        <button onClick={save} className="rounded border border-slate-300 px-4 py-2">
          Save policy
        </button>
        <Link
          href="/preview"
          className="rounded bg-blue-700 px-4 py-2 text-white no-underline"
        >
          Next: see before / after →
        </Link>
      </div>
    </div>
  );
}
