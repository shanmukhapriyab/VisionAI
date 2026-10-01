// Voice alerts: cooldown/priority logic (AlertGate) + a thin wrapper over the browser's Text-to-Speech.

export const LEVELS = ["SAFE", "CAUTION", "WARNING", "DANGER"];
export const rank = (level) => LEVELS.indexOf(level);

/**
 * Decides WHICH detection (if any) should be spoken right now, so alerts never repeat continuously.
 *  - the same object+side is repeated only after a cooldown (shorter for more dangerous levels)
 *  - a higher danger level than last time is announced immediately ("escalation")
 *  - alerts below `minLevel` are never spoken
 *  - a minimum gap between utterances keeps speech intelligible
 */
export class AlertGate {
  constructor() {
    this.seen = new Map();
    this.lastAt = -Infinity;
  }

  cooldownMs(level, baseSec) {
    const base = baseSec * 1000;
    if (level === "DANGER") return Math.min(base, 2500);
    if (level === "WARNING") return Math.min(base, 4000);
    if (level === "SAFE") return base * 2;
    return base;
  }

  /** detections must already be sorted most-dangerous-first (the backend does this). */
  pick(detections, { now, cooldownSec = 6, minLevel = "CAUTION" }) {
    this.#prune(now);
    const minRank = rank(minLevel);
    for (const d of detections) {
      const r = rank(d.danger.level);
      if (r < minRank) continue;
      const rec = this.seen.get(d.alert_key);
      const escalated = rec && r > rec.rank;
      const due = !rec || now - rec.at >= this.cooldownMs(d.danger.level, cooldownSec);
      if (!due && !escalated) continue;
      const gap = now - this.lastAt;
      if (gap < (r >= 3 ? 600 : 1200)) continue;
      return d;
    }
    return null;
  }

  markSpoken(d, now) {
    this.seen.set(d.alert_key, { at: now, rank: rank(d.danger.level) });
    this.lastAt = now;
  }

  reset() {
    this.seen.clear();
    this.lastAt = -Infinity;
  }

  #prune(now) {
    for (const [k, v] of this.seen) if (now - v.at > 60000) this.seen.delete(k);
  }
}

export class Speaker {
  constructor() {
    this.supported = typeof window !== "undefined" && "speechSynthesis" in window;
    this.busy = false;
    this._timer = null;
  }

  getVoices() {
    return this.supported ? window.speechSynthesis.getVoices() : [];
  }

  /** Returns true if the text was actually handed to the speech engine. */
  speak(text, { rate = 1, volume = 1, voiceURI = "", interrupt = false } = {}) {
    if (!this.supported || !text) return false;
    const synth = window.speechSynthesis;
    if (this.busy || synth.speaking) {
      if (!interrupt) return false;
      synth.cancel();
    }
    const u = new SpeechSynthesisUtterance(text);
    u.rate = rate;
    u.volume = volume;
    const voice = voiceURI && this.getVoices().find((v) => v.voiceURI === voiceURI);
    if (voice) {
      u.voice = voice;
      u.lang = voice.lang;
    }
    const done = () => {
      this.busy = false;
      clearTimeout(this._timer);
    };
    u.onend = done;
    u.onerror = done;
    this.busy = true;
    // Some browsers occasionally never fire onend; release the lock after a generous estimate.
    clearTimeout(this._timer);
    this._timer = setTimeout(done, (text.length * 90) / Math.max(rate, 0.3) + 2000);
    synth.speak(u);
    return true;
  }

  cancel() {
    if (this.supported) window.speechSynthesis.cancel();
    this.busy = false;
  }
}
