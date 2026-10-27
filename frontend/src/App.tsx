import { useCallback, useEffect, useState } from "react";
import { api, session, type CaseFile, type Decision, type Lang, type Overview, type TriageRecord } from "./api";
import { LANG_LABEL, STRINGS } from "./i18n";
import { DOC, FIELD, MORE, SCHEME, VALUE, flagText, label } from "./i18n2";

const FONT: Record<Lang, string> = {
  en: "'Noto Sans', system-ui, sans-serif",
  hi: "'Noto Sans Devanagari', 'Noto Sans', sans-serif",
  kn: "'Noto Sans Kannada', 'Noto Sans', sans-serif",
};

const useText = (ui: Lang) => ({ ...STRINGS[ui], ...MORE[ui] }) as Record<string, string>;

function LangSwitch({ ui, setUi }: { ui: Lang; setUi: (l: Lang) => void }) {
  return (
    <div className="langs" role="group" aria-label="Interface language">
      {(Object.keys(LANG_LABEL) as Lang[]).map((l) => (
        <button key={l} className={l === ui ? "on" : ""} onClick={() => setUi(l)}>
          {LANG_LABEL[l]}
        </button>
      ))}
    </div>
  );
}

function Login({ ui, setUi, onDone }: { ui: Lang; setUi: (l: Lang) => void; onDone: () => void }) {
  const t = useText(ui);
  const [user, setUser] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      session.set((await api.login(user.trim(), pw)).token);
      onDone();
    } catch {
      setErr(t.wrongLogin);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app" style={{ fontFamily: FONT[ui] }}>
      <div className="login">
        <LangSwitch ui={ui} setUi={setUi} />
        <h1>{t.title}</h1>
        <p className="banner">{t.humanDecides}</p>
        <form onSubmit={submit} className="card">
          <label>
            {t.username}
            <input value={user} onChange={(e) => setUser(e.target.value)} autoComplete="username" autoCapitalize="none" required />
          </label>
          <label>
            {t.password}
            <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" required />
          </label>
          {err && <p className="error" role="alert">{err}</p>}
          <button className="primary" disabled={busy}>{t.signIn}</button>
          <p className="meta">{t.loginHint}</p>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [ui, setUi] = useState<Lang>("en");
  const [signedIn, setSignedIn] = useState(!!session.get());
  useEffect(() => {
    const out = () => setSignedIn(false);
    window.addEventListener("seva-signed-out", out);
    return () => window.removeEventListener("seva-signed-out", out);
  }, []);
  if (!signedIn) return <Login ui={ui} setUi={setUi} onDone={() => setSignedIn(true)} />;
  return <Desk ui={ui} setUi={setUi} onSignOut={() => { session.clear(); setSignedIn(false); }} />;
}

function Desk({ ui, setUi, onSignOut }: { ui: Lang; setUi: (l: Lang) => void; onSignOut: () => void }) {
  const t = useText(ui);
  const [ov, setOv] = useState<Overview | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => api.overview(ui).then(setOv).catch((e) => setError(e.message)), [ui]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const tile = (n: number, text: string, cls = "") => (
    <div className={`tile ${cls}`}>
      <b>{n}</b>
      <span>{text}</span>
    </div>
  );

  return (
    <div className="app" style={{ fontFamily: FONT[ui] }}>
      <header>
        <h1>{t.title}</h1>
        <p className="banner">{t.humanDecides}</p>
        <LangSwitch ui={ui} setUi={setUi} />
        <button className="link" onClick={onSignOut}>{t.signOut}</button>
      </header>
      {error && (
        <div className="error" role="alert">
          {error} <button onClick={() => setError(null)}>×</button>
        </div>
      )}
      {ov && (
        <div className="tiles">
          {tile(ov.counts.open, t.tileOpen)}
          {tile(ov.counts.attention, t.tileAttention, "hot")}
          {tile(ov.counts.ready, t.tileReady, "good")}
          {tile(ov.counts.decided, t.tileDecided)}
        </div>
      )}
      <main className={selected ? "has-sel" : ""}>
        <nav aria-label={t.cases}>
          <h2>
            {t.cases} <span className="sortnote">· {t.sorted}</span>
          </h2>
          <ul>
            {(ov?.cases ?? []).map((c) => (
              <li key={c.id}>
                <button className={c.id === selected ? "case sel" : "case"} onClick={() => setSelected(c.id)}>
                  <span className="row">
                    <span className="id">{c.id}</span>
                    <span className={`lvl ${c.level}`}>{t[`level_${c.level}`]}</span>
                  </span>
                  <span className="name">{c.applicant_name}</span>
                  <span className="meta">
                    {label(SCHEME, ui, c.scheme_id)} · {c.language.toUpperCase()} · {t.waitingDays.replace("{n}", String(c.waiting_days))}
                  </span>
                  <span className="why">
                    {c.flags.length === 0 ? t.noIssues : c.flags.slice(0, 2).map((f) => flagText(ui, f)).join(" · ")}
                    {c.flags.length > 2 && ` +${c.flags.length - 2}`}
                  </span>
                  <span className="row">
                    <span className={`chip ${c.status}`}>{t[`status_${c.status}`] ?? c.status}</span>
                    {c.agent ? (
                      <span className={`badge sm ${c.agent.action}`}>
                        {t.agentSays}: {t[`act_${c.agent.action}`]}
                      </span>
                    ) : (
                      <span className="meta">{t.notChecked}</span>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <section className="detail">
          {selected ? (
            <CaseView key={selected} id={selected} ui={ui} flags={ov?.cases.find((c) => c.id === selected)?.flags ?? []}
              onBack={() => setSelected(null)} onChanged={refresh} onError={setError} />
          ) : (
            <p className="empty">{t.pickCase}</p>
          )}
        </section>
      </main>
    </div>
  );
}

function CaseView({ id, ui, flags, onBack, onChanged, onError }: {
  id: string; ui: Lang; flags: { code: string; detail: string }[]; onBack: () => void; onChanged: () => void; onError: (m: string) => void;
}) {
  const t = useText(ui);
  const [file, setFile] = useState<CaseFile | null>(null);
  const [rec, setRec] = useState<TriageRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    api.getCase(id).then(setFile).catch((e) => onError(e.message));
  }, [id, onError]);

  // the analysis is stored per interface language; switching language shows the one that exists or asks for a new one
  useEffect(() => {
    api
      .getTriage(id, ui)
      .then((r) => {
        setRec(r);
        setMsg(r.triage.message_to_applicant);
      })
      .catch(() => setRec(null)); // 404 = not analysed yet
  }, [id, ui]);

  const analyze = async () => {
    setBusy(true);
    setDone(null);
    try {
      const r = await api.analyze(id, ui);
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
      await api.decide(id, d, msg, rec?.lang ?? ui);
      setDone(t.decided);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  };

  if (!file) return <p className="empty">…</p>;
  const lang = file.applicant.language;
  const stale = rec && rec.lang !== ui; // shown in another language than the interface

  return (
    <div>
      <button className="link back" onClick={onBack}>{t.backToList}</button>
      <div className="card">
        <h2>
          {file.id} · {file.applicant.name}
        </h2>
        <p className="meta">
          {label(SCHEME, ui, file.scheme_id)} · {file.applicant.village} · {file.submitted_on}
        </p>
        {flags.length > 0 && (
          <>
            <h3>{t.whyRank}</h3>
            <ul className="flags">
              {flags.map((f, i) => (
                <li key={i}>{flagText(ui, f)}</li>
              ))}
            </ul>
          </>
        )}
        <h3>{t.note}</h3>
        <p lang={lang} style={{ fontFamily: FONT[lang] }} className="quote">
          {file.applicant_note}
        </p>
        <h3>{t.fields}</h3>
        <dl>
          {Object.entries(file.fields).map(([k, v]) => (
            <div key={k}>
              <dt>{label(FIELD, ui, k)}</dt>
              <dd>{VALUE[ui][String(v)] ?? String(v)}</dd>
            </div>
          ))}
        </dl>
        <h3>{t.documents}</h3>
        <ul className="docs">
          {file.documents.map((d) => (
            <li key={d.type} className={d.present ? "" : "absent"}>
              {label(DOC, ui, d.type)} {d.name_on_doc && <em>({d.name_on_doc})</em>}
              {d.expires_on && <span className="meta"> · {d.expires_on}</span>}
              {!d.present && <span className="meta"> · ✗</span>}
            </li>
          ))}
        </ul>
        <button className="primary" disabled={busy} onClick={analyze}>
          {busy ? t.analyzing : rec ? t.reanalyze : t.analyze}
        </button>
        {stale && <span className="meta"> · {LANG_LABEL[rec!.lang as Lang]}</span>}
      </div>

      {rec && (
        <div className="card">
          <div className="rec">
            <span className={`badge ${rec.triage.recommended_action}`}>
              {t.recommended}: {t[`act_${rec.triage.recommended_action}`]}
            </span>
            <span className="meta">
              {t.confidence}: {t[`conf_${rec.triage.confidence}`]}
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
