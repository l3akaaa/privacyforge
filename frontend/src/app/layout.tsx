import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PrivacyForge",
  description: "Privacy-first data de-identification",
};

const STEPS = [
  ["/", "Dashboard"],
  ["/upload", "Upload"],
  ["/review", "Detection Review"],
  ["/policy", "Policy Editor"],
  ["/preview", "Before / After"],
  ["/verify", "Verification"],
  ["/export", "Export"],
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="sr-only focus:not-sr-only">
          Skip to content
        </a>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
            <span className="text-lg font-bold">PrivacyForge</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              local-by-default
            </span>
          </div>
          <nav
            aria-label="Workflow steps"
            className="mx-auto flex max-w-6xl flex-wrap gap-1 px-4 pb-2 text-sm"
          >
            {STEPS.map(([href, label], i) => (
              <Link
                key={href}
                href={href}
                className="rounded px-3 py-1 text-slate-700 no-underline hover:bg-slate-100"
              >
                <span className="mr-1 text-slate-400">{i + 1}.</span>
                {label}
              </Link>
            ))}
          </nav>
        </header>
        <div
          role="note"
          className="bg-amber-50 px-4 py-2 text-center text-xs text-amber-900"
        >
          PrivacyForge does not guarantee perfect de-identification and does not
          certify legal compliance. Tokenization is pseudonymization, not
          anonymization. Always review the verification report before trusting an
          export.
        </div>
        <main id="main" className="mx-auto max-w-6xl px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
