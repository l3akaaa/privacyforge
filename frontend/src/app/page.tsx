"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getSession } from "@/lib/session";
import { Card } from "@/components/ui";

export default function Dashboard() {
  const [health, setHealth] = useState<{ version: string; nlp_available: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [session, setSession] = useState<ReturnType<typeof getSession>>({});

  useEffect(() => {
    setSession(getSession());
    api
      .health()
      .then((h) => setHealth(h))
      .catch(() => setErr("Backend not reachable. Start it: uvicorn privacyforge.api:app"));
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
        {session.projectId ? (
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
          <p className="text-sm text-slate-600">
            No active project.{" "}
            <Link href="/upload">Start by uploading a dataset →</Link>
          </p>
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
