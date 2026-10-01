import { useEffect, useState } from "react";

const Row = ({ label, hint, children, id }) => (
  <div className="row">
    <label htmlFor={id}>{label}{hint && <small>{hint}</small>}</label>
    {children}
  </div>
);

export default function SettingsPanel({ settings, update, reset, speaker, cameras }) {
  const [voices, setVoices] = useState([]);
  useEffect(() => {
    if (!speaker.supported) return;
    const load = () => setVoices(speaker.getVoices());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, [speaker]);

  const testVoice = () =>
    speaker.speak("Person ahead. Chair on your left. Warning. Vehicle approaching from your right.", {
      rate: settings.speechRate, volume: settings.volume, voiceURI: settings.voiceURI, interrupt: true,
    });

  const slider = (id, key, min, max, step, fmt) => (
    <div className="slider">
      <input id={id} type="range" min={min} max={max} step={step} value={settings[key]}
        onChange={(e) => update({ [key]: Number(e.target.value) })} />
      <output htmlFor={id}>{fmt(settings[key])}</output>
    </div>
  );

  return (
    <div className="settings">
      <fieldset>
        <legend>Voice</legend>
        {!speaker.supported && <p className="muted">This browser does not support speech synthesis. Alerts will be shown on screen only.</p>}
        <Row id="s-voice" label="Voice alerts">
          <input id="s-voice" type="checkbox" className="switch" role="switch" checked={settings.voiceEnabled}
            onChange={(e) => update({ voiceEnabled: e.target.checked })} />
        </Row>
        <Row id="s-rate" label="Speech speed">{slider("s-rate", "speechRate", 0.5, 2, 0.1, (v) => `${v.toFixed(1)}×`)}</Row>
        <Row id="s-vol" label="Volume">{slider("s-vol", "volume", 0.1, 1, 0.1, (v) => `${Math.round(v * 100)}%`)}</Row>
        <Row id="s-voicesel" label="Voice">
          <select id="s-voicesel" value={settings.voiceURI} onChange={(e) => update({ voiceURI: e.target.value })}>
            <option value="">Browser default</option>
            {voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
          </select>
        </Row>
        <Row id="s-min" label="Speak alerts from" hint="Quieter levels are still shown on screen">
          <select id="s-min" value={settings.minSpeakLevel} onChange={(e) => update({ minSpeakLevel: e.target.value })}>
            <option value="SAFE">Safe (everything)</option>
            <option value="CAUTION">Caution and above</option>
            <option value="WARNING">Warning and above</option>
            <option value="DANGER">Danger only</option>
          </select>
        </Row>
        <Row id="s-cool" label="Repeat delay" hint="Danger alerts repeat sooner">{slider("s-cool", "cooldownSec", 2, 20, 1, (v) => `${v} s`)}</Row>
        <button className="btn btn-small" onClick={testVoice} disabled={!speaker.supported}>Test voice</button>
      </fieldset>

      <fieldset>
        <legend>Detection</legend>
        <Row id="s-conf" label="Minimum confidence" hint="Higher = fewer false alarms, may miss objects">{slider("s-conf", "confidence", 0.25, 0.8, 0.05, (v) => `${Math.round(v * 100)}%`)}</Row>
        <Row id="s-lab" label="Show labels on boxes">
          <input id="s-lab" type="checkbox" className="switch" role="switch" checked={settings.showLabels} onChange={(e) => update({ showLabels: e.target.checked })} />
        </Row>
        <Row id="s-cam" label="Camera" hint="Applies next time you press Start">
          <select id="s-cam" value={settings.cameraId} onChange={(e) => update({ cameraId: e.target.value })}>
            <option value="">Automatic (rear camera if available)</option>
            {cameras.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </Row>
      </fieldset>

      <fieldset>
        <legend>Display and emergency</legend>
        <Row id="s-theme" label="Theme">
          <select id="s-theme" value={settings.theme} onChange={(e) => update({ theme: e.target.value })}>
            <option value="auto">Match my system</option>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </Row>
        <Row id="s-size" label="Text size">
          <select id="s-size" value={settings.textScale} onChange={(e) => update({ textScale: Number(e.target.value) })}>
            <option value={100}>Standard</option>
            <option value={125}>Large</option>
            <option value={150}>Extra large</option>
          </select>
        </Row>
        <Row id="s-tel" label="Emergency phone number" hint="Optional. Shown as a call link after pressing Emergency">
          <input id="s-tel" type="tel" inputMode="tel" placeholder="e.g. 112" value={settings.emergencyNumber}
            onChange={(e) => update({ emergencyNumber: e.target.value })} />
        </Row>
        <button className="btn btn-small" onClick={reset}>Restore default settings</button>
      </fieldset>
    </div>
  );
}
