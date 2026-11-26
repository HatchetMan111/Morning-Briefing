import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

const TABS = [
  { id: "briefing", label: "🌅 Briefing" },
  { id: "archive", label: "🗂️ Archiv" },
  { id: "status", label: "📊 Status" },
  { id: "settings", label: "⚙️ Einstellungen" },
];

function ScoreBadge({ score }) {
  const cls = score >= 70 ? "good" : score >= 50 ? "ok" : "low";
  return <span className={`badge ${cls}`}>{score}</span>;
}

function SectionCard({ section }) {
  const hasContent =
    section.lines?.length || section.commentary || section.items?.length;
  if (!hasContent) return null;
  return (
    <div className="card section">
      <h2>{section.title}</h2>
      {section.lines?.length > 0 && (
        <div className="lines">
          {section.lines.map((l, i) => (
            <div className="line" key={i}>{l}</div>
          ))}
        </div>
      )}
      {section.commentary && <p className="commentary">{section.commentary}</p>}
      {section.items?.length > 0 && (
        <ul className="items">
          {section.items.map((it, i) => (
            <li key={i}>
              <div className="item-head">
                <ScoreBadge score={it.score} />
                {it.url ? (
                  <a href={it.url} target="_blank" rel="noreferrer">{it.title}</a>
                ) : (
                  <span>{it.title}</span>
                )}
              </div>
              {it.summary && <div className="item-summary">{it.summary}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BriefingView({ data, error }) {
  if (error) return <div className="card empty">📄 {error}</div>;
  if (!data) return <div className="card empty">⏳ Lade Briefing …</div>;
  return (
    <>
      <div className="card meta">
        <div>
          <strong>{data.date}</strong>
          <span className="muted"> · erzeugt {data.generated_at}</span>
        </div>
      </div>
      {data.sections?.map((s) => (
        <SectionCard key={s.key} section={s} />
      ))}
    </>
  );
}

export default function App() {
  const [tab, setTab] = useState("briefing");
  const [latest, setLatest] = useState(null);
  const [latestError, setLatestError] = useState(null);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedData, setSelectedData] = useState(null);
  const [status, setStatus] = useState(null);
  const [runState, setRunState] = useState(null);
  const [feedback, setFeedback] = useState({ positive: [], negative: [] });
  const [fbText, setFbText] = useState("");
  const [fbKind, setFbKind] = useState("positive");
  const [configText, setConfigText] = useState("");
  const [envText, setEnvText] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const pollRef = useRef(null);
  const showToast = useCallback((msg, err = false) => {
    setToast({ msg, err });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const refreshCore = useCallback(async () => {
    try {
      const [b, st] = await Promise.all([api.briefings(), api.status()]);
      setDates(b.briefings);
      setStatus(st);
    } catch (e) {
      /* Server nicht erreichbar */
    }
  }, []);

  const loadLatest = useCallback(async () => {
    try {
      setLatest(await api.latest());
      setLatestError(null);
    } catch (e) {
      setLatest(null);
      setLatestError(e.message);
    }
  }, []);

  useEffect(() => {
    loadLatest();
    refreshCore();
  }, [loadLatest, refreshCore]);

  // Lauf-Status pollen, während ein Briefing läuft
  useEffect(() => {
    if (runState?.running) {
      pollRef.current = setInterval(async () => {
        try {
          const s = await api.runStatus();
          setRunState(s);
          if (!s.running) {
            await loadLatest();
            await refreshCore();
            showToast(s.error ? `Lauf fehlgeschlagen – siehe Status-Tab` : `Briefing aktualisiert ✓`);
          }
        } catch { /* weiterpollen */ }
      }, 3000);
    }
    return () => pollRef.current && clearInterval(pollRef.current);
  }, [runState?.running, loadLatest, refreshCore, showToast]);

  const startRun = async () => {
    try {
      await api.run();
      setRunState(await api.runStatus());
      showToast("Briefing-Lauf gestartet …");
    } catch (e) {
      showToast(e.message, true);
    }
  };

  const openDate = async (d) => {
    setSelectedDate(d);
    setSelectedData(await api.briefing(d));
  };

  const saveFeedback = async () => {
    if (!fbText.trim()) return;
    try {
      setFeedback(await api.addFeedback(fbKind, fbText.trim()));
      setFbText("");
      showToast("Feedback gespeichert ✓");
    } catch (e) {
      showToast(e.message, true);
    }
  };

  const saveConfig = async () => {
    setBusy(true);
    try {
      await api.saveConfig(configText);
      showToast("config.yaml gespeichert (Backup: config.yaml.bak) ✓");
      await refreshCore();
    } catch (e) {
      showToast(e.message, true);
    }
    setBusy(false);
  };

  const saveEnv = async () => {
    setBusy(true);
    try {
      const res = await api.saveEnv(envText);
      showToast(`Gespeichert ✓ – ${res.hint}`);
    } catch (e) {
      showToast(e.message, true);
    }
    setBusy(false);
  };

  const loadSettings = async () => {
    try {
      const [c, e, f] = await Promise.all([api.config(), api.env(), api.feedback()]);
      setConfigText(c.yaml);
      setEnvText(e.env);
      setFeedback(f);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  useEffect(() => {
    if (tab === "settings") loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <div className="app">
      <header>
        <div>
          <h1>🌅 Morning Briefing</h1>
          <div className="sub">
            Creglingen &amp; 50 km · Weltwirtschaft · Tech · KI
          </div>
        </div>
        <div className="actions">
          <span className={`dot ${status?.runner?.running ? "run" : "idle"}`} />
          <button className="primary" onClick={startRun} disabled={runState?.running}>
            {runState?.running ? "⏳ läuft …" : "▶ Jetzt starten"}
          </button>
        </div>
      </header>

      <nav>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === "briefing" && <BriefingView data={latest} error={latestError} />}

        {tab === "archive" && (
          <div className="archive">
            <div className="card">
              <h2>🗂️ Verfügbare Briefings</h2>
              {dates.length === 0 && <div className="muted">Noch keine gespeichert.</div>}
              <ul className="date-list">
                {dates.map((d) => (
                  <li key={d}>
                    <button className={selectedDate === d ? "active" : ""} onClick={() => openDate(d)}>
                      {d}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
            {selectedDate && (
              <div className="archive-detail">
                <h2>Briefing vom {selectedDate}</h2>
                {selectedData?.sections?.map((s) => (
                  <SectionCard key={s.key} section={s} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "status" && (
          <div className="card">
            <h2>📊 Status</h2>
            {status ? (
              <>
                <div className="kv">
                  <span>Geplante Laufzeit</span><strong>{status.run_time}</strong>
                  <span>Region</span><strong>{status.region}</strong>
                  <span>Telegram</span>
                  <strong>{status.telegram_configured ? "✅ konfiguriert" : "⚠️ nicht gesetzt"}</strong>
                  <span>Gemini KI</span>
                  <strong>{status.gemini_configured ? "✅ konfiguriert" : "⚠️ nicht gesetzt"}</strong>
                  <span>Letztes Briefing</span><strong>{status.latest_briefing ?? "–"}</strong>
                  <span>Läufe insgesamt</span><strong>{status.runner.runs_total}</strong>
                </div>
                <h3>Quellen (letzter Lauf)</h3>
                <div className="chips">
                  {Object.entries(status.latest_sources).map(([k, v]) => (
                    <span key={k} className={`chip ${v === "ok" ? "good" : "bad"}`}>
                      {v === "ok" ? "✓" : "✗"} {k}
                    </span>
                  ))}
                  {Object.keys(status.latest_sources).length === 0 && (
                    <span className="muted">Noch keine Laufdaten.</span>
                  )}
                </div>
                <h3>Module</h3>
                <div className="chips">
                  {Object.entries(status.modules).map(([k, on]) => (
                    <span key={k} className={`chip ${on ? "good" : "off"}`}>
                      {on ? "●" : "○"} {k}
                    </span>
                  ))}
                </div>
                {status.runner.log && (
                  <>
                    <h3>Log (letzte 80 Zeilen)</h3>
                    <pre className="log">
                      {status.runner.log.split("\n").slice(-80).join("\n")}
                    </pre>
                  </>
                )}
              </>
            ) : (
              <div className="muted">⏳ Lade Status …</div>
            )}
          </div>
        )}

        {tab === "settings" && (
          <>
            <div className="card">
              <h2>⚙️ config.yaml</h2>
              <p className="muted">
                Orte, Uhrzeit, Module, Filter. Nach dem Speichern greift die
                Uhrzeit sofort; Module beim nächsten Lauf.
              </p>
              <textarea value={configText} onChange={(e) => setConfigText(e.target.value)} rows={18} />
              <button className="primary" disabled={busy} onClick={saveConfig}>
                💾 Speichern
              </button>
            </div>
            <div className="card">
              <h2>🔑 Zugangsdaten (.env)</h2>
              <p className="muted">
                Format: KEY=WERT (eine Zeile pro Schlüssel). Gesetzte Werte
                werden als *** angezeigt – zum Ändern neuen Wert eintragen.
                Erlaubt: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY, EBAY_BEARER_TOKEN.
              </p>
              <textarea value={envText} onChange={(e) => setEnvText(e.target.value)} rows={6} />
              <button className="primary" disabled={busy} onClick={saveEnv}>
                💾 Speichern
              </button>
            </div>
            <div className="card">
              <h2>🧠 KI-Feedback</h2>
              <p className="muted">
                Vorlieben fließen direkt in die KI-Bewertung zukünftiger Läufe.
              </p>
              <div className="fb-form">
                <select value={fbKind} onChange={(e) => setFbKind(e.target.value)}>
                  <option value="positive">👍 mag ich</option>
                  <option value="negative">👎 nicht relevant</option>
                </select>
                <input
                  value={fbText}
                  placeholder="z. B. Mehr Homelab-Hardware-Auktionen"
                  onChange={(e) => setFbText(e.target.value)}
                />
                <button className="primary" onClick={saveFeedback}>Hinzufügen</button>
              </div>
              {feedback.positive.length > 0 && (
                <div className="chips">
                  {feedback.positive.map((t, i) => <span key={i} className="chip good">+ {t}</span>)}
                </div>
              )}
              {feedback.negative.length > 0 && (
                <div className="chips">
                  {feedback.negative.map((t, i) => <span key={i} className="chip off">− {t}</span>)}
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {toast && <div className={`toast ${toast.err ? "err" : ""}`}>{toast.msg}</div>}
    </div>
  );
}
