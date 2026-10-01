import { useCallback, useEffect, useMemo, useState } from "react";
import AlertPanel from "./components/AlertPanel.jsx";
import CameraView from "./components/CameraView.jsx";
import ControlBar from "./components/ControlBar.jsx";
import DetectionList from "./components/DetectionList.jsx";
import EmergencyModal from "./components/EmergencyModal.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import { MoonIcon, SunIcon } from "./components/Icons.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import { useDetection } from "./hooks/useDetection.js";
import { useSettings } from "./hooks/useSettings.js";
import { postEmergency } from "./lib/api.js";
import { Speaker } from "./lib/speech.js";

export default function App() {
  const { settings, update, reset } = useSettings();
  const speaker = useMemo(() => new Speaker(), []);
  const [liveMsg, setLiveMsg] = useState("");
  const announce = useCallback((t) => setLiveMsg(t), []);
  const [tab, setTab] = useState("settings");
  const [em, setEm] = useState({ open: false, result: null, error: null });

  const det = useDetection({ settings, speaker, announce });
  const { phase, result, stats, error } = det;
  const running = phase === "running";

  const toggleVoice = useCallback(() => {
    const next = !settings.voiceEnabled;
    update({ voiceEnabled: next });
    if (!next) speaker.cancel();
    announce(next ? "Voice alerts on." : "Voice alerts off.");
  }, [settings.voiceEnabled, update, speaker, announce]);

  const onEmergency = useCallback(async () => {
    setEm({ open: true, result: null, error: null });
    speaker.speak(
      "Emergency alert recorded. This is a prototype and does not contact anyone. Call your local emergency number.",
      { rate: settings.speechRate, volume: 1, voiceURI: settings.voiceURI, interrupt: true }
    );
    try {
      const r = await postEmergency({
        session_id: det.sessionId() || null,
        last_level: result?.summary?.level || null,
        last_message: result?.summary?.message || null,
      });
      setEm({ open: true, result: r, error: null });
    } catch (e) {
      setEm({ open: true, result: null, error: e.message });
    }
  }, [det, result, settings.speechRate, settings.voiceURI, speaker]);

  // Keyboard shortcuts: Space = start/stop, V = voice on/off (ignored while typing or on a control)
  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A", "SUMMARY"].includes(e.target.tagName) || e.target.closest("dialog")) return;
      if (e.code === "Space") {
        e.preventDefault();
        if (phase === "running") det.stop();
        else if (phase === "idle") det.start();
      } else if (e.key === "v" || e.key === "V") toggleVoice();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, det, toggleVoice]);

  const dark = document.documentElement.getAttribute("data-theme") === "dark" ||
    (settings.theme === "auto" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  return (
    <>
      <a className="skip" href="#main">Skip to controls</a>
      <header className="top">
        <div className="brand">
          <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><path d="M16 5 28 26H4z" fill="none" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" /><circle cx="16" cy="18.5" r="3" fill="currentColor" /></svg>
          <h1>VisionGuard</h1>
        </div>
        <dl className="stats" aria-label="Performance">
          <div><dt>FPS</dt><dd>{running && stats.fps ? stats.fps.toFixed(1) : "–"}</dd></div>
          <div><dt>Model</dt><dd>{running && stats.inferenceMs ? `${Math.round(stats.inferenceMs)} ms` : "–"}</dd></div>
          <div><dt>Delay</dt><dd>{running && stats.roundTripMs ? `${Math.round(stats.roundTripMs)} ms` : "–"}</dd></div>
        </dl>
        <button className="btn btn-icon" onClick={() => update({ theme: dark ? "light" : "dark" })}
          aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
          {dark ? <SunIcon /> : <MoonIcon />}
        </button>
      </header>

      <p className="disclaimer">
        <strong>Experimental prototype.</strong> Do not rely on VisionGuard as your only navigation or safety system.
        It can miss objects and its distances are estimates.
      </p>

      <main id="main" className="layout">
        <div className="col-main">
          <CameraView videoRef={det.videoRef} phase={phase} result={result} notice={det.notice}
            showLabels={settings.showLabels} stats={stats} />
          <ControlBar phase={phase} onStart={det.start} onStop={() => det.stop()} voiceEnabled={settings.voiceEnabled}
            onToggleVoice={toggleVoice} onEmergency={onEmergency} voiceSupported={speaker.supported} />
          <ErrorBanner error={error} onDismiss={det.dismissError} onRetry={phase === "idle" ? det.start : undefined} />
        </div>
        <div className="col-side">
          <AlertPanel phase={phase} result={result} />
          <DetectionList detections={result?.detections || []} running={running} />
        </div>
      </main>

      <section className="tabs-wrap" aria-label="Settings and history">
        <div className="tabs" role="tablist">
          {[["settings", "Settings"], ["history", "History"]].map(([id, label]) => (
            <button key={id} role="tab" id={`tab-${id}`} aria-selected={tab === id} aria-controls={`panel-${id}`}
              tabIndex={tab === id ? 0 : -1} onClick={() => setTab(id)}
              onKeyDown={(e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { setTab(tab === "settings" ? "history" : "settings"); } }}>
              {label}
            </button>
          ))}
        </div>
        <div role="tabpanel" id="panel-settings" aria-labelledby="tab-settings" hidden={tab !== "settings"}>
          <SettingsPanel settings={settings} update={update} reset={reset} speaker={speaker} cameras={det.cameras} />
        </div>
        <div role="tabpanel" id="panel-history" aria-labelledby="tab-history" hidden={tab !== "history"}>
          <HistoryPanel active={tab === "history"} running={running} />
        </div>
      </section>

      <footer className="foot">
        <p>Shortcuts: <kbd>Space</kbd> start / stop · <kbd>V</kbd> voice on / off. Detection runs on your computer; camera frames are not sent to the internet.</p>
      </footer>

      <div className="sr-only" role="status" aria-live="polite">{liveMsg}</div>
      <EmergencyModal open={em.open} onClose={() => setEm((s) => ({ ...s, open: false }))} result={em.result}
        error={em.error} phoneNumber={settings.emergencyNumber} lastMessage={result?.summary?.message} />
    </>
  );
}
