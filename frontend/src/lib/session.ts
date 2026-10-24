// Minimal client-side session state shared across pages via sessionStorage.
// Keeps the current project id, file id, and schema so each page can resume.

export interface Session {
  projectId?: string;
  projectName?: string;
  fileId?: string;
  filename?: string;
  schema?: any;
}

const KEY = "privacyforge_session";

export function getSession(): Session {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

export function setSession(patch: Partial<Session>) {
  const next = { ...getSession(), ...patch };
  sessionStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export function clearSession() {
  sessionStorage.removeItem(KEY);
}
