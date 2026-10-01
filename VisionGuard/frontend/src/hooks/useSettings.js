import { useCallback, useEffect, useState } from "react";

const KEY = "visionguard.settings.v1";

export const DEFAULT_SETTINGS = {
  voiceEnabled: true,
  speechRate: 1.0,
  volume: 1.0,
  voiceURI: "",
  cooldownSec: 6,
  minSpeakLevel: "CAUTION",
  confidence: 0.4,
  showLabels: true,
  cameraId: "",
  theme: "auto",          // auto | dark | light
  textScale: 100,         // 100 | 125 | 150
  emergencyNumber: "",
};

function load() {
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function useSettings() {
  const [settings, setSettings] = useState(load);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(settings));
    } catch {
      /* storage may be blocked; settings then last for this session only */
    }
    const root = document.documentElement;
    if (settings.theme === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", settings.theme);
    root.style.fontSize = `${settings.textScale}%`;
  }, [settings]);

  const update = useCallback((patch) => setSettings((s) => ({ ...s, ...patch })), []);
  const reset = useCallback(() => setSettings({ ...DEFAULT_SETTINGS }), []);
  return { settings, update, reset };
}
