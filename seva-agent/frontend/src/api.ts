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
  status: string;
  triage: Triage;
  trace: TraceStep[];
  model: string | null;
  created_at: string;
  decisions?: { decision: string; final_message: string; message_edited: boolean; decided_at: string; note: string | null }[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  cases: () => req<CaseSummary[]>("/api/cases"),
  getCase: (id: string) => req<CaseFile>(`/api/cases/${id}`),
  getTriage: (id: string) => req<TriageRecord>(`/api/cases/${id}/triage`),
  analyze: (id: string) => req<TriageRecord>(`/api/cases/${id}/analyze`, { method: "POST" }),
  decide: (id: string, decision: Decision, message: string, note?: string) =>
    req<{ status: string }>(`/api/cases/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, message, note }),
    }),
};
