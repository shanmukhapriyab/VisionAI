import { PlayIcon, SirenIcon, StopIcon, VoiceOffIcon, VoiceOnIcon } from "./Icons.jsx";

export default function ControlBar({ phase, onStart, onStop, voiceEnabled, onToggleVoice, onEmergency, voiceSupported }) {
  const running = phase === "running";
  const starting = phase === "starting";
  return (
    <div className="controls" role="group" aria-label="Detection controls">
      <button
        className={`btn btn-main ${running ? "is-stop" : ""}`}
        onClick={running ? onStop : onStart}
        disabled={starting}
        aria-keyshortcuts="Space"
      >
        {running ? <StopIcon /> : <PlayIcon />}
        {starting ? "Starting…" : running ? "Stop detection" : "Start detection"}
      </button>
      <button
        className="btn"
        onClick={onToggleVoice}
        aria-pressed={voiceEnabled}
        disabled={!voiceSupported}
        aria-keyshortcuts="V"
        title={voiceSupported ? "" : "This browser has no speech synthesis"}
      >
        {voiceEnabled && voiceSupported ? <VoiceOnIcon /> : <VoiceOffIcon />}
        Voice {voiceEnabled && voiceSupported ? "on" : "off"}
      </button>
      <button className="btn btn-emergency" onClick={onEmergency}>
        <SirenIcon /> Emergency
      </button>
    </div>
  );
}
