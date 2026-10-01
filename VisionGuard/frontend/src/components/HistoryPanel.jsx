import { useCallback, useEffect, useState } from "react";
import { clearHistory, getHistory, getHistoryStats } from "../lib/api.js";
import { LevelIcon } from "./Icons.jsx";

export default function HistoryPanel({ active, running }) {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [level, setLevel] = useState("");
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(async () => {
    try {
      const [h, s] = await Promise.all([getHistory({ limit: 60, level }), getHistoryStats()]);
      setItems(h.items);
      setStats(s);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, [level]);

  useEffect(() => {
    if (!active) return;
    load();
    if (!running) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [active, running, load]);

  const doClear = async () => {
    try { await clearHistory(); setConfirming(false); load(); } catch (e) { setError(e.message); }
  };

  return (
    <div className="history">
      <div className="history-bar">
        <label>Show{" "}
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">All levels</option>
            <option>DANGER</option><option>WARNING</option><option>CAUTION</option><option>SAFE</option>
          </select>
        </label>
        <button className="btn btn-small" onClick={load}>Refresh</button>
        {confirming ? (
          <>
            <button className="btn btn-small btn-danger" onClick={doClear}>Yes, delete all history</button>
            <button className="btn btn-small" onClick={() => setConfirming(false)}>Cancel</button>
          </>
        ) : (
          <button className="btn btn-small" onClick={() => setConfirming(true)} disabled={!items.length}>Clear history</button>
        )}
      </div>
      {stats && (
        <p className="muted">
          {stats.total} stored · Danger {stats.by_level.DANGER} · Warning {stats.by_level.WARNING} · Caution {stats.by_level.CAUTION} · Safe {stats.by_level.SAFE}
        </p>
      )}
      {error && <p className="inline-error" role="alert">History unavailable: {error}</p>}
      {!error && items.length === 0 && <p className="muted">Nothing stored yet. Detections are saved here while detection is running.</p>}
      {items.length > 0 && (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Detection history table">
          <table>
            <thead><tr><th>Time</th><th>Level</th><th>Object</th><th>Confidence</th><th>Distance</th><th>Side</th><th>Spoken text</th></tr></thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} data-level={r.danger}>
                  <td>{new Date(r.created_at).toLocaleTimeString()}</td>
                  <td><span className="lvl-cell"><LevelIcon level={r.danger} size={16} />{r.danger}</span></td>
                  <td>{r.label}</td>
                  <td>{Math.round(r.confidence * 100)}%</td>
                  <td>{r.distance_m.toFixed(1)} m</td>
                  <td>{r.position}</td>
                  <td>{r.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
