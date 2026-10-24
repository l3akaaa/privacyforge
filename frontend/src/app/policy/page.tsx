"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

const OPERATORS = ["redact", "mask", "tokenize", "synthetic", "generalize", "retain"];

const OPERATOR_HELP: Record<string, string> = {
  redact: "Remove it and leave a label like [REDACTED_EMAIL].",
  mask: "Hide most of it, e.g. 12****.",
  tokenize: "Swap for a secure code (TOK_...). Same value always gets the same code.",
  synthetic: "Replace with a realistic fake value.",
  generalize: "Make it less exact, e.g. age 19 to 18-24, a date to its year.",
  retain: "Keep it unchanged.",
};

const PRESET_HELP: Record<string, string> = {
  recommended:
    "Safe default. Tokenizes IDs, removes names/emails and sensitive values, blurs age and ZIP.",
  academic_research: "For research: tokenize IDs, remove emails, fake names, blur dates.",
  student_records: "For student records: tokenize IDs, remove names, emails, phones.",
  business_analytics: "For analytics: tokenize PII, remove sensitive, keep quasi-identifiers.",
  ai_prompt_protection: "For cleaning text before an AI: remove all PII and sensitive data.",
  software_testing: "For test data: replace PII with realistic fakes, tokenize IDs.",
};

export default function PolicyPage() {
  const [presets, setPresets] = useState<Record<string, any>>({});
  const [policy, setPolicy] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = typeof window !== "undefined" ? getSession() : {};

  useEffect(() => {
    api.presets().then(setPresets).catch(() => {});
    if (s.projectId)
      api
        .getPolicy(s.projectId)
        .then((r) => {
          // If the project has no rules yet, start from the safe recommended preset.
          if (!r.policy?.rules?.length) {
            api.setPolicy(s.projectId!, { preset_name: "recommended" })
              .then((rr) => setPolicy(rr.policy))
              .catch(() => setPolicy(r.policy));
          } else {
            setPolicy(r.policy);
          }
        })
        .catch(() => {});
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
        <p className="mb-3 text-sm text-slate-600">
          Not sure? The <strong>recommended</strong> preset is a safe default.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.keys(presets)
            .sort((a, b) => (a === "recommended" ? -1 : b === "recommended" ? 1 : 0))
            .map((name) => {
              const active = policy?.name === name;
              const isRec = name === "recommended";
              return (
                <button
                  key={name}
                  onClick={() => applyPreset(name)}
                  className={`rounded border p-3 text-left text-sm hover:bg-slate-50 ${
                    active ? "border-blue-500 ring-1 ring-blue-300" : "border-slate-300"
                  }`}
                >
                  <div className="font-medium capitalize">
                    {name.replace(/_/g, " ")}
                    {isRec && (
                      <span className="ml-2 rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800">
                        recommended
                      </span>
                    )}
                    {active && <span className="ml-2 text-xs text-blue-700">✓ selected</span>}
                  </div>
                  <div className="mt-1 text-xs text-slate-600">{PRESET_HELP[name]}</div>
                </button>
              );
            })}
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
          <div className="mt-4 border-t border-slate-100 pt-3">
            <p className="mb-1 text-xs font-semibold text-slate-500">
              What each action does
            </p>
            <ul className="grid gap-1 text-xs text-slate-600 sm:grid-cols-2">
              {OPERATORS.map((o) => (
                <li key={o}>
                  <span className="font-medium">{o}</span>: {OPERATOR_HELP[o]}
                </li>
              ))}
            </ul>
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
