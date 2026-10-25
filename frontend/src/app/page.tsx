"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession, clearSession } from "@/lib/session";
import { Card } from "@/components/ui";

export default function Dashboard() {
  const [health, setHealth] = useState<{ version: string; nlp_available: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [session, setSession] = useState<ReturnType<typeof getSession>>({});
  const [checking, setChecking] = useState(true);
  const [staleCleared, setStaleCleared] = useState(false);

  useEffect(() => {
    const s = getSession();
    setSession(s);
    api
      .health()
      .then((h) => setHealth(h))
      .catch(() => setErr("Backend not reachable. Start it: uvicorn privacyforge.api:app"));

    // If the browser remembers a project, confirm the backend still has it.
    // A backend restart can drop it; without this check the page dead-ends on
    // "Continue" and never shows the upload link.
    if (s.projectId) {
      api
        .getProject(s.projectId)
        .then(() => setChecking(false))
        .catch(() => {
          clearSession();
          setSession({});
          setStaleCleared(true);
          setChecking(false);
        });
    } else {
      setChecking(false);
    }
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-slate-600">
          De-identify a dataset in seven steps. Nothing leaves your machine.
        </p>
      </div>

      <Card title="System status">
        {err ? (
          <p className="text-red-700">{err}</p>
        ) : health ? (
          <ul className="space-y-1 text-sm">
            <li>Backend version: {health.version}</li>
            <li>
              NLP layer (names, places):{" "}
              {health.nlp_available ? (
                <span className="text-green-700">enabled</span>
              ) : (
                <span className="text-amber-700">
                  not installed (deterministic + column detection still run)
                </span>
              )}
            </li>
          </ul>
        ) : (
          <p className="text-slate-500">Checking…</p>
        )}
      </Card>

      <Card title="Current project">
        {checking ? (
          <p className="text-sm text-slate-500">Checking…</p>
        ) : session.projectId ? (
          <div className="text-sm">
            <p>
              <strong>{session.projectName}</strong> ({session.projectId})
            </p>
            {session.filename && <p>File: {session.filename}</p>}
            <Link href="/review" className="mt-2 inline-block">
              Continue to detection review →
            </Link>
          </div>
        ) : (
          <div className="text-sm text-slate-600">
            {staleCleared && (
              <p className="mb-1 text-amber-700">
                Your previous project was cleared (the backend restarted and no
                longer has it). Start a new one below.
              </p>
            )}
            <p>
              No active project.{" "}
              <Link href="/upload">Start by uploading a dataset →</Link>
            </p>
          </div>
        )}
      </Card>

      <Card title="How it works">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
          <li>Upload a CSV, Excel, JSON, or text file.</li>
          <li>The tool finds likely sensitive information and explains why.</li>
          <li>You review, correct, and add anything missed.</li>
          <li>You choose what happens to each kind of data.</li>
          <li>See the before and after, side by side.</li>
          <li>A second scan checks for leftover risk.</li>
          <li>Download the result and a plain report — if it passes the safety gate.</li>
        </ol>
      </Card>
    </div>
  );
}
