export type Lang = "en" | "hi" | "kn";
export type Action = "approve" | "request_more_info" | "escalate" | "reject";
export type Decision = "approve" | "reject" | "request_more_info";

export interface CaseSummary {
  id: string;
  scheme_id: string;
  applicant_name: string;
  language: Lang;
  submitted_on: string;
  status: string;
}

export interface Flag { code: string; detail: string }

export interface OverviewCase extends CaseSummary {
  score: number;
  level: "high" | "medium" | "low";
  flags: Flag[];
  waiting_days: number;
  needs_fix: boolean;
  agent: { action: Action; confidence: "low" | "medium" | "high" } | null;
}

export interface Overview {
  counts: { total: number; open: number; attention: number; ready: number; decided: number };
  cases: OverviewCase[];
}

export interface CaseDoc {
  type: string;
  present: boolean;
  name_on_doc: string | null;
  expires_on: string | null;
}

export interface CaseFile {
  id: string;
  scheme_id: string;
  applicant: { name: string; language: Lang; village: string };
  applicant_note: string;
  incident_date: string | null;
  submitted_on: string;
  fields: Record<string, string | number>;
  documents: CaseDoc[];
}

export interface Triage {
  summary: string;
  missing_items: { item: string; why: string }[];
  risks: { issue: string; evidence: string }[];
  recommended_action: Action;
  reason: string;
  message_to_applicant: string;
  confidence: "low" | "medium" | "high";
}

export interface TraceStep {
  step: number;
  tool: string;
  source: "mcp" | "local" | "none";
  input: Record<string, unknown>;
  output: string;
  is_error: boolean;
}

export interface TriageRecord {
  case_id: string;
  lang: Lang;
  status: string;
  triage: Triage;
  trace: TraceStep[];
  model: string | null;
  created_at: string;
  decisions?: { decision: string; final_message: string; message_edited: boolean; decided_at: string; note: string | null }[];
}

const TOKEN_KEY = "seva-token";
export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = session.get();
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (res.status === 401 && token) {
    session.clear();
    window.dispatchEvent(new Event("seva-signed-out"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    req<{ token: string; user: string }>("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  overview: (lang: Lang) => req<Overview>(`/api/overview?lang=${lang}`),
  getCase: (id: string) => req<CaseFile>(`/api/cases/${id}`),
  getTriage: (id: string, lang: Lang) => req<TriageRecord>(`/api/cases/${id}/triage?lang=${lang}`),
  analyze: (id: string, lang: Lang) => req<TriageRecord>(`/api/cases/${id}/analyze?lang=${lang}`, { method: "POST" }),
  decide: (id: string, decision: Decision, message: string, lang: Lang, note?: string) =>
    req<{ status: string }>(`/api/cases/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, message, note, lang }),
    }),
};
