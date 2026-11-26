import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

const TABS = [
  { id: "briefing", label: "🌅 Briefing" },
  { id: "alerts", label: "🔔 Alerts" },
  { id: "archive", label: "🗂️ Archiv" },
  { id: "status", label: "📊 Status" },
  { id: "settings", label: "⚙️ Einstellungen" },
];

const SOURCE_META = {
  "zoll-auktion": { icon: "🏛️", label: "Zoll" },
  "google-news": { icon: "📰", label: "News" },
  "hackernews": { icon: "💬", label: "HN" },
  "arxiv": { icon: "📄", label: "Paper" },
  "github-trending": { icon: "🐙", label: "GitHub" },
  "show-hn": { icon: "🚀", label: "Show HN" },
  "awesome-selfhosted": { icon: "⭐", label: "Awesome" },
  "r/selfhosted": { icon: "💙", label: "Reddit" },
  "ebay": { icon: "🛒", label: "eBay" },
  "price-watch": { icon: "💰", label: "Preis" },
  "mydealz": { icon: "🔥", label: "Deal" },
  "tankerkoenig": { icon: "⛽", label: "Sprit" },
  "weekly_review": { icon: "📅", label: "Woche" },
  "zvg-news": { icon: "🏠", label: "ZVG" },
  "gruendung": { icon: "🏢", label: "Gründung" },
  "firma-news": { icon: "📈", label: "Firma" },
};

function SourceBadge({ source }) {
  const meta = SOURCE_META[source] || { icon: "📌", label: source };
  return <span className="src-badge">{meta.icon} {meta.label}</span>;
}

function ScoreBadge({ score }) {
  const cls = score >= 85 ? "top" : score >= 70 ? "good" : score >= 50 ? "ok" : "low";
  return <span className={`badge ${cls}`}>{score}</span>;
}

// ============ CHARTS ============

function Sparkline({ points, width = 180, height = 44 }) {
  if (!points || points.length < 2) return null;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / (points.length - 1);
  const path = points
    .map((p, i) => `${(i * step).toFixed(1)},${(height - 4 - ((p.value - min) / range) * (height - 8)).toFixed(1)}`)
    .join(" ");
  const isUp = values[values.length - 1] >= values[0];
  const stroke = isUp ? "#2fbf71" : "#e05b5b";
  const lastX = (points.length - 1) * step;
  const lastY = height - 4 - ((values[values.length - 1] - min) / range) * (height - 8);
  return (
    <svg width={width} height={height} className="sparkline">
      <polyline points={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="3" fill={stroke} />
    </svg>
  );
}

function MarketChart({ marketData }) {
  if (!marketData || marketData.length === 0) return null;
  const maxAbs = Math.max(...marketData.map((d) => Math.abs(d.pct)), 1);
  return (
    <div className="market-chart">
      {marketData.map((m, i) => {
        const pctWidth = (Math.abs(m.pct) / maxAbs) * 50;
        const isUp = m.pct >= 0;
        return (
          <div className="market-row" key={i}>
            <div className="market-info">
              <span className="market-label">{m.label}</span>
              <span className="market-value">{m.value}</span>
            </div>
            <div className="market-track">
              <div className="market-zero" />
              <div
                className={`market-bar ${isUp ? "up" : "down"}`}
                style={{
                  width: `${pctWidth}%`,
                  left: isUp ? "50%" : `${50 - pctWidth}%`,
                }}
              />
            </div>
            <span className={`market-pct ${isUp ? "pos" : "neg"}`}>
              {isUp ? "▲" : "▼"} {Math.abs(m.pct).toFixed(2)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ============ VIEWS ============

function StatsHeader({ stats, date, generated }) {
  if (!stats) return null;
  return (
    <div className="stats-bar">
      <div className="stat">
        <span className="stat-num">{stats.total_items}</span>
        <span className="stat-label">Items</span>
      </div>
      <div className="stat">
        <span className="stat-num">{stats.section_count}</span>
        <span className="stat-label">Sektionen</span>
      </div>
      {stats.alert_count > 0 && (
        <div className="stat hot">
          <span className="stat-num">{stats.alert_count}</span>
          <span className="stat-label">🔔 Alerts</span>
        </div>
      )}
      <div className="stat date">
        <span className="stat-label">{date} · {generated?.slice(11, 16)}</span>
      </div>
    </div>
  );
}

function TopStories({ stories }) {
  if (!stories || stories.length === 0) return null;
  return (
    <div className="top-stories">
      <h2 className="section-head">⭐ Top-Stories heute</h2>
      {stories.map((s, i) => (
        <div className={`top-story rank-${i + 1}`} key={i}>
          <div className="rank">{i + 1}</div>
          <div className="content">
            <div className="head">
              <ScoreBadge score={s.score} />
              <SourceBadge source={s.source} />
              {s.url ? (
                <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
              ) : (
                <span>{s.title}</span>
              )}
            </div>
            {s.summary && <div className="story-summary">{s.summary}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

function SectionCard({ section, isMarket }) {
  const hasContent =
    section.lines?.length || section.commentary || section.items?.length;
  if (!hasContent) return null;

  return (
    <div className={`card section ${isMarket ? "market-section" : ""}`}>
      <h2 className="section-head">{section.title}</h2>

      {isMarket && section.lines?.length > 0 && (
        <div className="lines">
          {section.lines.map((l, i) => (
            <div className="line" key={i}>{l}</div>
          ))}
        </div>
      )}

      {!isMarket && section.lines?.length > 0 && (
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
                <SourceBadge source={it.source} />
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

function BriefingView({ data, error, marketHistory, isRunning }) {
  if (isRunning && !data) {
    return (
      <div className="card empty generating">
        <div className="gen-spinner" />
        <h3>🌅 Briefing wird erstellt …</h3>
        <p className="muted">Sammle News, Auktionen, Märkte und Deals.<br/>Das dauert ca. 2–3 Minuten.</p>
      </div>
    );
  }
  if (error && !isRunning) return <div className="card empty">📄 {error}</div>;
  if (!data) return <div className="card empty">⏳ Lade Briefing …</div>;

  const marketSection = data.sections?.find((s) => s.key === "markets");
  const hasMarketChart = data.market_chart?.length > 0;

  return (
    <>
      <StatsHeader stats={data.stats} date={data.date} generated={data.generated_at} />
      <TopStories stories={data.top_stories} />

      {hasMarketChart && (
        <div className="card chart-card">
          <h2 className="section-head">
            📊 Märkte
            {marketHistory?.DAX?.length > 1 && (
              <span className="sparkline-wrap">
                <small>DAX 14 Tage:</small>
                <Sparkline points={marketHistory.DAX} />
              </span>
            )}
          </h2>
          <MarketChart marketData={data.market_chart} />
          {marketSection?.commentary && (
            <p className="commentary">{marketSection.commentary}</p>
          )}
        </div>
      )}

      {data.sections?.map((s) => {
        if (s.key === "markets" && hasMarketChart) return null;
        return <SectionCard key={s.key} section={s} />;
      })}
    </>
  );
}

// ============ MAIN APP ============

export default function App() {
  const [tab, setTab] = useState("briefing");
  const [latest, setLatest] = useState(null);
  const [latestError, setLatestError] = useState(null);
  const [marketHistory, setMarketHistory] = useState({});
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
  const [llmInfo, setLlmInfo] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [alertTerm, setAlertTerm] = useState("");
  const [alertSource, setAlertSource] = useState("*");
  const [watches, setWatches] = useState([]);
  const [watchQuery, setWatchQuery] = useState("");
  const [watchThreshold, setWatchThreshold] = useState("");
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
      // Wenn ein Lauf läuft, runState setzen -> Polling startet
      if (st.runner?.running) {
        setRunState(st.runner);
      }
    } catch { /* offline */ }
  }, []);

  const loadLatest = useCallback(async () => {
    try {
      setLatest(await api.latest());
      setLatestError(null);
      // Sparkline-Daten laden (DAX)
      try {
        const mh = await api.marketHistory("DAX");
        setMarketHistory({ DAX: mh.history });
      } catch { /* noch keine Historie */ }
    } catch (e) {
      setLatest(null);
      setLatestError(e.message);
    }
  }, []);

  useEffect(() => {
    loadLatest();
    refreshCore();
  }, [loadLatest, refreshCore]);

  useEffect(() => {
    if (runState?.running) {
      pollRef.current = setInterval(async () => {
        try {
          const s = await api.runStatus();
          setRunState(s);
          if (!s.running) {
            await loadLatest();
            await refreshCore();
            showToast(s.error ? "Lauf fehlgeschlagen – siehe Status-Tab" : "Briefing aktualisiert ✓");
          }
        } catch { /* weiter */ }
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
      showToast("config.yaml gespeichert ✓");
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
      const [c, e, f, llm] = await Promise.all([
        api.config(), api.env(), api.feedback(),
        fetch("/api/llm").then((r) => r.json()),
      ]);
      setConfigText(c.yaml);
      setEnvText(e.env);
      setFeedback(f);
      setLlmInfo(llm);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const loadAlerts = async () => {
    try {
      const [a, w] = await Promise.all([api.alerts(), api.priceWatch()]);
      setAlerts(a.alerts || []);
      setWatches(w.watches || []);
    } catch (err) {
      showToast(err.message, true);
    }
  };

  useEffect(() => {
    if (tab === "settings") loadSettings();
    if (tab === "alerts") loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const addAlert = async () => {
    if (!alertTerm.trim()) return;
    try {
      const res = await api.addAlert(alertTerm.trim(), alertSource);
      setAlerts(res.alerts || []);
      setAlertTerm("");
      showToast(`Alert "${alertTerm}" gespeichert ✓`);
    } catch (e) {
      showToast(e.message, true);
    }
  };

  const removeAlert = async (id) => {
    try {
      const res = await api.deleteAlert(id);
      setAlerts(res.alerts || []);
    } catch (e) {
      showToast(e.message, true);
    }
  };

  const addWatch = async () => {
    if (!watchQuery.trim()) return;
    try {
      const res = await api.addPriceWatch(watchQuery.trim(), parseFloat(watchThreshold) || 0);
      setWatches(res.watches || []);
      setWatchQuery("");
      setWatchThreshold("");
      showToast(`Preis-Tracker "${watchQuery}" gespeichert ✓`);
    } catch (e) {
      showToast(e.message, true);
    }
  };

  const removeWatch = async (id) => {
    try {
      const res = await api.deletePriceWatch(id);
      setWatches(res.watches || []);
    } catch (e) {
      showToast(e.message, true);
    }
  };

  return (
    <div className="app">
      <header>
        <div>
          <h1>🌅 Morning Briefing</h1>
          <div className="sub">Creglingen &amp; 50 km · Welt · Tech · KI</div>
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
          <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {tab === "briefing" && (
          <BriefingView
            data={latest}
            error={latestError}
            marketHistory={marketHistory}
            isRunning={runState?.running}
          />
        )}

        {tab === "alerts" && (
          <>
            <div className="card">
              <h2 className="section-head">🔔 Keyword-Alerts</h2>
              <p className="muted">
                Benachrichtigung (Telegram + Briefing), wenn ein Begriff in einer
                Quelle auftaucht. "*" = alle Quellen.
              </p>
              <div className="fb-form">
                <input
                  value={alertTerm}
                  placeholder="z. B. Zwangsversteigerung, Server…"
                  onChange={(e) => setAlertTerm(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addAlert()}
                />
                <select value={alertSource} onChange={(e) => setAlertSource(e.target.value)}>
                  <option value="*">Alle</option>
                  <option value="local_news">Lokal</option>
                  <option value="zoll-auktion">Zoll</option>
                  <option value="google-news">News</option>
                  <option value="ebay">eBay</option>
                  <option value="github-trending">GitHub</option>
                  <option value="hackernews">HN</option>
                </select>
                <button className="primary" onClick={addAlert}>＋</button>
              </div>
              {alerts.length > 0 ? (
                <div className="chips">
                  {alerts.map((a) => (
                    <span key={a.id} className="chip good">
                      🔍 {a.term} <small>({a.source_filter})</small>
                      <button className="chip-del" onClick={() => removeAlert(a.id)}>✕</button>
                    </span>
                  ))}
                </div>
              ) : (
                <div className="muted">Noch keine Alerts.</div>
              )}
            </div>
            <div className="card">
              <h2 className="section-head">💰 Preis-Tracker (eBay)</h2>
              <p className="muted">Beobachtet eBay-Suchen. Unterschreitet der niedrigste
              Preis dein Limit → Alert. (Benötigt eBay-Token.)</p>
              <div className="fb-form">
                <input
                  value={watchQuery}
                  placeholder="z. B. homelab server"
                  onChange={(e) => setWatchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addWatch()}
                />
                <input
                  type="number" value={watchThreshold} placeholder="Limit €"
                  style={{ maxWidth: 100 }}
                  onChange={(e) => setWatchThreshold(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addWatch()}
                />
                <button className="primary" onClick={addWatch}>＋</button>
              </div>
              {watches.length > 0 ? (
                <table className="watch-table">
                  <thead><tr><th>Suche</th><th>Limit</th><th>Letzter</th><th>Titel</th><th></th></tr></thead>
                  <tbody>
                    {watches.map((w) => (
                      <tr key={w.id}>
                        <td>{w.query}</td>
                        <td>{w.threshold > 0 ? `${w.threshold} €` : "–"}</td>
                        <td>{w.last_price !== null ? (
                          <a href={w.last_url} target="_blank" rel="noreferrer">
                            {w.last_price.toFixed(2)} €
                          </a>
                        ) : "–"}</td>
                        <td className="muted">{w.last_title?.slice(0, 35) || "–"}</td>
                        <td><button className="chip-del" onClick={() => removeWatch(w.id)}>✕</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="muted">Noch keine Watches.</div>
              )}
            </div>
          </>
        )}

        {tab === "archive" && (
          <div className="archive">
            <div className="card">
              <h2 className="section-head">🗂️ Briefings</h2>
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
                <h2>{selectedDate}</h2>
                {selectedData?.sections?.map((s) => (
                  <SectionCard key={s.key} section={s} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "status" && (
          <div className="card">
            <h2 className="section-head">📊 Status</h2>
            {status ? (
              <>
                <div className="kv">
                  <span>Laufzeiten</span>
                  <strong>{(status.run_times || []).join(" · ")}</strong>
                  <span>Region</span><strong>{status.region}</strong>
                  <span>Telegram</span>
                  <strong>{status.telegram_configured ? "✅" : "⚠️ nicht gesetzt"}</strong>
                  <span>Gemini KI</span>
                  <strong>{status.gemini_configured ? "✅" : "⚠️ nicht gesetzt"}</strong>
                  <span>Letztes Briefing</span><strong>{status.latest_briefing ?? "–"}</strong>
                </div>
                <h3>Quellen</h3>
                <div className="chips">
                  {Object.entries(status.latest_sources).map(([k, v]) => (
                    <span key={k} className={`chip ${v === "ok" ? "good" : v.includes("Treffer") ? "hot" : "bad"}`}>
                      {v === "ok" ? "✓" : v.includes("fehler") ? "✗" : "🔔"} {k}: {v}
                    </span>
                  ))}
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
                    <h3>Log</h3>
                    <pre className="log">{status.runner.log.split("\n").slice(-80).join("\n")}</pre>
                  </>
                )}
              </>
            ) : (
              <div className="muted">⏳ Lade …</div>
            )}
          </div>
        )}

        {tab === "settings" && (
          <>
            {llmInfo && (
              <div className="card">
                <h2 className="section-head">🤖 KI-Provider</h2>
                <div className="kv">
                  <span>Aktiver Provider</span>
                  <strong>{llmInfo.provider}</strong>
                  <span>Gemini</span>
                  <strong>{llmInfo.gemini ? "✅" : "–"}</strong>
                  <span>OpenRouter</span>
                  <strong>{llmInfo.openrouter ? "✅" : "–"}</strong>
                  <span>Ollama</span>
                  <strong>{llmInfo.ollama ? "✅" : "–"}</strong>
                  {llmInfo.openrouter_model && (
                    <>
                      <span>OpenRouter Modell</span>
                      <strong>{llmInfo.openrouter_model}</strong>
                    </>
                  )}
                  {llmInfo.ollama_model && (
                    <>
                      <span>Ollama Modell</span>
                      <strong>{llmInfo.ollama_model}</strong>
                    </>
                  )}
                </div>
                <p className="muted" style={{ marginTop: 10 }}>
                  Provider wechseln: <code>LLM_PROVIDER=gemini|openrouter|ollama</code> in
                  den Zugangsdaten unten setzen, speichern, dann Service neustarten.
                </p>
              </div>
            )}
            <div className="card">
              <h2 className="section-head">⚙️ config.yaml</h2>
              <textarea value={configText} onChange={(e) => setConfigText(e.target.value)} rows={18} />
              <button className="primary" disabled={busy} onClick={saveConfig}>💾 Speichern</button>
            </div>
            <div className="card">
              <h2 className="section-head">🔑 Zugangsdaten (.env)</h2>
              <p className="muted">Gesetzte Werte erscheinen als ***. Erlaubt:
              TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY, EBAY_BEARER_TOKEN,
              LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_MODEL, OLLAMA_BASE_URL,
              OLLAMA_MODEL, TANKERKOENIG_API_KEY.</p>
              <textarea value={envText} onChange={(e) => setEnvText(e.target.value)} rows={6} />
              <button className="primary" disabled={busy} onClick={saveEnv}>💾 Speichern</button>
            </div>
            <div className="card">
              <h2 className="section-head">🧠 KI-Feedback</h2>
              <div className="fb-form">
                <select value={fbKind} onChange={(e) => setFbKind(e.target.value)}>
                  <option value="positive">👍</option>
                  <option value="negative">👎</option>
                </select>
                <input value={fbText} placeholder="Vorliebe/Ablehnung"
                  onChange={(e) => setFbText(e.target.value)} />
                <button className="primary" onClick={saveFeedback}>＋</button>
              </div>
              <div className="chips" style={{ marginTop: 8 }}>
                {feedback.positive?.map((t, i) => <span key={i} className="chip good">+ {t}</span>)}
                {feedback.negative?.map((t, i) => <span key={i} className="chip off">− {t}</span>)}
              </div>
            </div>
          </>
        )}
      </main>

      {toast && <div className={`toast ${toast.err ? "err" : ""}`}>{toast.msg}</div>}
    </div>
  );
}
