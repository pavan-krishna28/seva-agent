import { useCallback, useEffect, useState } from "react";
import { api, type CaseFile, type CaseSummary, type Decision, type Lang, type TriageRecord } from "./api";
import { LANG_LABEL, STRINGS } from "./i18n";

const FONT: Record<Lang, string> = {
  en: "'Noto Sans', system-ui, sans-serif",
  hi: "'Noto Sans Devanagari', 'Noto Sans', sans-serif",
  kn: "'Noto Sans Kannada', 'Noto Sans', sans-serif",
};

export default function App() {
  const [ui, setUi] = useState<Lang>("en");
  const t = STRINGS[ui];
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => api.cases().then(setCases).catch((e) => setError(e.message)), []);
  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="app" style={{ fontFamily: FONT[ui] }}>
      <header>
        <h1>{t.title}</h1>
        <p className="banner">{t.humanDecides}</p>
        <div className="langs" role="group" aria-label="Interface language">
          {(Object.keys(LANG_LABEL) as Lang[]).map((l) => (
            <button key={l} className={l === ui ? "on" : ""} onClick={() => setUi(l)}>
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
      </header>
      {error && (
        <div className="error" role="alert">
          {error} <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      <main>
        <nav aria-label={t.cases}>
          <h2>{t.cases}</h2>
          <ul>
            {cases.map((c) => (
              <li key={c.id}>
                <button className={c.id === selected ? "case sel" : "case"} onClick={() => setSelected(c.id)}>
                  <span className="id">{c.id}</span>
                  <span className="name">{c.applicant_name}</span>
                  <span className="meta">
                    {c.scheme_id.replace(/_/g, " ")} · {c.language.toUpperCase()}
                  </span>
                  <span className={`chip ${c.status}`}>{t[`status_${c.status}`] ?? c.status}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <section className="detail">
          {selected ? (
            <CaseView key={selected} id={selected} ui={ui} onChanged={refresh} onError={setError} />
          ) : (
            <p className="empty">{t.pickCase}</p>
          )}
        </section>
      </main>
    </div>
  );
}

function CaseView({ id, ui, onChanged, onError }: { id: string; ui: Lang; onChanged: () => void; onError: (m: string) => void }) {
  const t = STRINGS[ui];
  const [file, setFile] = useState<CaseFile | null>(null);
  const [rec, setRec] = useState<TriageRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    api.getCase(id).then(setFile).catch((e) => onError(e.message));
    api
      .getTriage(id)
      .then((r) => {
        setRec(r);
        setMsg(r.triage.message_to_applicant);
      })
      .catch(() => setRec(null)); // 404 = not analysed yet
  }, [id, onError]);

  const analyze = async () => {
    setBusy(true);
    setDone(null);
    try {
      const r = await api.analyze(id);
      setRec(r);
      setMsg(r.triage.message_to_applicant);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const decide = async (d: Decision) => {
    try {
      await api.decide(id, d, msg);
      setDone(t.decided);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  };

  if (!file) return <p className="empty">…</p>;
  const lang = file.applicant.language;

  return (
    <div>
      <div className="card">
        <h2>
          {file.id} · {file.applicant.name}
        </h2>
        <p className="meta">
          {file.scheme_id.replace(/_/g, " ")} · {file.applicant.village} · {file.submitted_on}
        </p>
        <h3>{t.note}</h3>
        <p lang={lang} style={{ fontFamily: FONT[lang] }} className="quote">
          {file.applicant_note}
        </p>
        <h3>{t.fields}</h3>
        <dl>
          {Object.entries(file.fields).map(([k, v]) => (
            <div key={k}>
              <dt>{k.replace(/_/g, " ")}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
        <h3>{t.documents}</h3>
        <ul className="docs">
          {file.documents.map((d) => (
            <li key={d.type}>
              {d.type.replace(/_/g, " ")} {d.name_on_doc && <em>({d.name_on_doc})</em>}
              {d.expires_on && <span className="meta"> · exp {d.expires_on}</span>}
            </li>
          ))}
        </ul>
        <button className="primary" disabled={busy} onClick={analyze}>
          {busy ? t.analyzing : rec ? t.reanalyze : t.analyze}
        </button>
      </div>

      {rec && (
        <div className="card">
          <div className="rec">
            <span className={`badge ${rec.triage.recommended_action}`}>
              {t.recommended}: {t[`act_${rec.triage.recommended_action}`]}
            </span>
            <span className="meta">
              {t.confidence}: {rec.triage.confidence}
            </span>
          </div>
          <h3>{t.summary}</h3>
          <p>{rec.triage.summary}</p>
          <p className="meta">{rec.triage.reason}</p>

          <h3>{t.missing}</h3>
          {rec.triage.missing_items.length === 0 ? (
            <p className="meta">{t.noneMissing}</p>
          ) : (
            <ul>
              {rec.triage.missing_items.map((m, i) => (
                <li key={i}>
                  <strong>{m.item}</strong> — {m.why}
                </li>
              ))}
            </ul>
          )}

          <h3>{t.risks}</h3>
          {rec.triage.risks.length === 0 ? (
            <p className="meta">{t.noneRisks}</p>
          ) : (
            <ul>
              {rec.triage.risks.map((r, i) => (
                <li key={i}>
                  <strong>{r.issue}</strong> <span className="meta">({r.evidence})</span>
                </li>
              ))}
            </ul>
          )}

          <h3>{t.message}</h3>
          <p className="meta">{t.messageHint}</p>
          <textarea lang={lang} style={{ fontFamily: FONT[lang] }} value={msg} onChange={(e) => setMsg(e.target.value)} rows={4} />
          <div className="actions">
            <button className="ok" onClick={() => decide("approve")}>
              {t.approve}
            </button>
            <button className="warn" onClick={() => decide("request_more_info")}>
              {t.requestInfo}
            </button>
            <button className="bad" onClick={() => decide("reject")}>
              {t.reject}
            </button>
          </div>
          {done && <p className="done">✓ {done}</p>}

          <details>
            <summary>
              {t.trace} ({rec.trace.length})
            </summary>
            <ol className="trace">
              {rec.trace.map((s, i) => (
                <li key={i} className={s.is_error ? "err" : ""}>
                  <code>
                    {s.tool}({Object.values(s.input).length ? Object.entries(s.input).map(([k, v]) => `${k}=${typeof v === "string" ? v : "…"}`).join(", ") : ""})
                  </code>
                  <span className="tag">{s.source === "mcp" ? "MCP" : s.source}</span>
                  <pre>{s.output}</pre>
                </li>
              ))}
            </ol>
            <p className="meta">model: {rec.model}</p>
          </details>
        </div>
      )}
    </div>
  );
}
