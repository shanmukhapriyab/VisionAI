import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, detectFrame, getHealth } from "../lib/api.js";
import { AlertGate } from "../lib/speech.js";

const MAX_FPS = 8;               // upper bound; real speed is limited by CPU inference time
const CAPTURE_WIDTH = 640;
const JPEG_QUALITY = 0.7;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function cameraError(e) {
  if (!navigator.mediaDevices?.getUserMedia) {
    return {
      kind: "camera", code: "INSECURE_CONTEXT", title: "Camera is not available in this browser context",
      detail: "Open VisionGuard from http://localhost:5173 or http://127.0.0.1:5173 (browsers block the camera on other plain-HTTP addresses).",
    };
  }
  const map = {
    NotAllowedError: ["Camera permission was denied", "Allow camera access in the address-bar permission icon, then press Start again."],
    SecurityError: ["Camera permission was denied", "Allow camera access in the address-bar permission icon, then press Start again."],
    NotFoundError: ["No camera found", "Connect a camera and press Start again."],
    NotReadableError: ["The camera is busy", "Close other apps that use the camera (Teams, Zoom, other tabs) and try again."],
    OverconstrainedError: ["The selected camera is unavailable", "Choose another camera in Settings."],
  };
  const [title, detail] = map[e?.name] || ["The camera could not be started", e?.message || "Unknown camera error."];
  return { kind: "camera", code: e?.name || "CAMERA_ERROR", title, detail };
}

function backendError(e) {
  const titles = {
    BACKEND_UNREACHABLE: "Cannot reach the backend",
    MODEL_LOADING: "The AI model is still loading",
    ULTRALYTICS_MISSING: "The YOLO library is not installed",
    MODEL_DOWNLOAD_FAILED: "The YOLO model could not be downloaded",
    MODEL_LOAD_FAILED: "The YOLO model failed to load",
    INFERENCE_FAILED: "Detection failed on the backend",
  };
  return {
    kind: "backend", code: e.code, title: titles[e.code] || "Detection error",
    detail: e.message,
  };
}

export function useDetection({ settings, speaker, announce }) {
  const videoRef = useRef(null);
  const [phase, setPhase] = useState("idle");           // idle | starting | running
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState({ fps: 0, roundTripMs: 0, inferenceMs: 0 });
  const [cameras, setCameras] = useState([]);

  const run = useRef({ active: false, abort: null, stream: null, session: "", gate: new AlertGate() });
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const refreshCameras = useCallback(async () => {
    try {
      const devs = await navigator.mediaDevices.enumerateDevices();
      setCameras(devs.filter((d) => d.kind === "videoinput").map((d, i) => ({ id: d.deviceId, label: d.label || `Camera ${i + 1}` })));
    } catch { /* ignore */ }
  }, []);

  const speakAlert = useCallback((d, now) => {
    const s = settingsRef.current;
    if (!s.voiceEnabled) return;
    const ok = speaker.speak(d.message, {
      rate: s.speechRate, volume: s.volume, voiceURI: s.voiceURI,
      interrupt: d.danger.level === "DANGER",
    });
    if (ok) run.current.gate.markSpoken(d, now);
  }, [speaker]);

  const say = useCallback((text) => {          // status messages (not hazard alerts)
    const s = settingsRef.current;
    announce(text);
    if (s.voiceEnabled) speaker.speak(text, { rate: s.speechRate, volume: s.volume, voiceURI: s.voiceURI, interrupt: true });
  }, [announce, speaker]);

  const stop = useCallback((silent = false) => {
    const r = run.current;
    r.active = false;
    r.abort?.abort();
    r.stream?.getTracks().forEach((t) => t.stop());
    r.stream = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    speaker.cancel();
    setPhase("idle");
    setResult(null);
    setNotice(null);
    setStats({ fps: 0, roundTripMs: 0, inferenceMs: 0 });
    if (!silent) say("Detection stopped.");
  }, [say, speaker]);

  const loop = useCallback(async () => {
    const r = run.current;
    const canvas = document.createElement("canvas");
    const times = [];
    let failStreak = 0;

    while (r.active) {
      const started = performance.now();
      const video = videoRef.current;
      if (!video || video.readyState < 2 || !video.videoWidth) { await sleep(100); continue; }

      const scale = Math.min(1, CAPTURE_WIDTH / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", JPEG_QUALITY));
      if (!blob || !r.active) continue;

      try {
        r.abort = new AbortController();
        const res = await detectFrame(blob, r.session, settingsRef.current.confidence, r.abort.signal);
        if (!r.active) break;
        if (failStreak > 0) { setError(null); say("Detection restored."); }
        failStreak = 0;
        setNotice(null);
        const now = performance.now();
        times.push(now);
        if (times.length > 10) times.shift();
        const fps = times.length > 1 ? ((times.length - 1) * 1000) / (times[times.length - 1] - times[0]) : 0;
        setStats({ fps, roundTripMs: now - started, inferenceMs: res.timing.inference_ms });
        setResult({ ...res, at: now });

        const pick = r.gate.pick(res.detections, {
          now, cooldownSec: settingsRef.current.cooldownSec, minLevel: settingsRef.current.minSpeakLevel,
        });
        if (pick) speakAlert(pick, now);
      } catch (e) {
        if (e.name === "AbortError" || !r.active) break;
        const err = e instanceof ApiError ? e : new ApiError("UNKNOWN", String(e.message || e));
        if (err.code === "MODEL_LOADING") {
          setNotice("The AI model is loading. Detection will begin automatically.");
          await sleep(1500);
          continue;
        }
        failStreak += 1;
        setResult(null);                      // never leave stale boxes on screen
        setError(backendError(err));
        if (failStreak === 1) say(`Detection unavailable. ${backendError(err).title}.`);
        await sleep(Math.min(5000, 700 * failStreak));
        continue;
      }
      const elapsed = performance.now() - started;
      const minInterval = 1000 / MAX_FPS;
      if (elapsed < minInterval) await sleep(minInterval - elapsed);
    }
  }, [say, speakAlert]);

  const start = useCallback(async () => {
    const r = run.current;
    if (r.active) return;
    setError(null);
    setNotice(null);
    setPhase("starting");
    try {
      const health = await getHealth();
      if (health.status === "error") {
        throw new ApiError(health.model?.error?.code || "MODEL_ERROR", health.model?.error?.message || "The model failed to load.");
      }
    } catch (e) {
      const be = backendError(e instanceof ApiError ? e : new ApiError("BACKEND_UNREACHABLE", String(e)));
      setError(be);
      setPhase("idle");
      say(`Could not start. ${be.title}.`);
      return;
    }

    let stream;
    try {
      const wanted = settingsRef.current.cameraId;
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: wanted
          ? { deviceId: { exact: wanted }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
    } catch (e) {
      const ce = cameraError(e);
      setError(ce);
      setPhase("idle");
      say(`Could not start. ${ce.title}.`);
      return;
    }
    stream.getVideoTracks()[0]?.addEventListener("ended", () => {
      if (!r.active) return;
      stop(true);
      setError({ kind: "camera", code: "CAMERA_LOST", title: "The camera was disconnected", detail: "Reconnect it and press Start again." });
      say("Camera disconnected. Detection stopped.");
    });
    r.stream = stream;
    refreshCameras();
    const video = videoRef.current;
    video.srcObject = stream;
    try { await video.play(); } catch { /* autoplay is allowed for muted streams */ }

    r.session = crypto.randomUUID?.() || String(Date.now());
    r.gate.reset();
    r.active = true;
    setPhase("running");
    say("Detection started.");
    loop();
  }, [loop, refreshCameras, say, stop]);

  const stopRef = useRef(stop);
  stopRef.current = stop;
  useEffect(() => () => stopRef.current(true), []);   // stop camera + loop on unmount only

  return { videoRef, phase, error, notice, result, stats, cameras, start, stop, dismissError: () => setError(null), sessionId: () => run.current.session };
}
