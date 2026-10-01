// Thin client for the VisionGuard FastAPI backend.
const BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(code, message, status = 0) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new ApiError(
      "BACKEND_UNREACHABLE",
      "Cannot reach the VisionGuard backend. Make sure start_backend.bat is running (http://127.0.0.1:8000)."
    );
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const err = body?.error || body?.detail || {};
    if (res.status === 502 || res.status === 504 || (res.status === 500 && !body)) {
      throw new ApiError("BACKEND_UNREACHABLE", "The backend is not responding. Is start_backend.bat running?", res.status);
    }
    throw new ApiError(err.code || "HTTP_ERROR", err.message || `Server returned ${res.status}`, res.status);
  }
  return body;
}

export const getHealth = () => request("/api/health");

export const detectFrame = (blob, sessionId, conf, signal) =>
  request(`/api/detect?session_id=${encodeURIComponent(sessionId)}&conf=${conf}`, {
    method: "POST",
    headers: { "Content-Type": "image/jpeg" },
    body: blob,
    signal,
  });

export const getHistory = ({ limit = 50, level = "" } = {}) =>
  request(`/api/history?limit=${limit}${level ? `&level=${level}` : ""}`);
export const getHistoryStats = () => request("/api/history/stats");
export const clearHistory = () => request("/api/history", { method: "DELETE" });

export const postEmergency = (payload) =>
  request("/api/emergency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
