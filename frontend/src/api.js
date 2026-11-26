async function handle(res) {
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.detail || json.error || res.statusText);
  return json;
}

export const api = {
  latest: () => fetch("/api/briefing/latest").then(handle),
  briefings: () => fetch("/api/briefings").then(handle),
  briefing: (date) => fetch(`/api/briefings/${date}`).then(handle),
  run: () => fetch("/api/run", { method: "POST" }).then(handle),
  runStatus: () => fetch("/api/run").then(handle),
  status: () => fetch("/api/status").then(handle),
  feedback: () => fetch("/api/feedback").then(handle),
  addFeedback: (kind, text) =>
    fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, text }),
    }).then(handle),
  alerts: () => fetch("/api/alerts").then(handle),
  addAlert: (term, source_filter) =>
    fetch("/api/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term, source_filter }),
    }).then(handle),
  deleteAlert: (id) => fetch(`/api/alerts/${id}`, { method: "DELETE" }).then(handle),
  priceWatch: () => fetch("/api/price-watch").then(handle),
  addPriceWatch: (query, threshold) =>
    fetch("/api/price-watch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, threshold }),
    }).then(handle),
  deletePriceWatch: (id) =>
    fetch(`/api/price-watch/${id}`, { method: "DELETE" }).then(handle),
  marketHistory: (label, days = 14) =>
    fetch(`/api/market-history/${encodeURIComponent(label)}?days=${days}`).then(handle),
  config: () => fetch("/api/config").then(handle),
  saveConfig: (yaml) =>
    fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml }),
    }).then(handle),
  env: () => fetch("/api/env").then(handle),
  saveEnv: (env) =>
    fetch("/api/env", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ env }),
    }).then(handle),
};
