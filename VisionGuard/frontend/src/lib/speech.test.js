import { describe, expect, it } from "vitest";
import { AlertGate } from "./speech.js";

const det = (key, level) => ({ alert_key: key, danger: { level }, message: `${key} ${level}` });

describe("AlertGate", () => {
  it("speaks a new alert once, then stays quiet during the cooldown", () => {
    const g = new AlertGate();
    const d = det("person:center", "CAUTION");
    const first = g.pick([d], { now: 0, cooldownSec: 6 });
    expect(first).toBe(d);
    g.markSpoken(first, 0);
    expect(g.pick([d], { now: 3000, cooldownSec: 6 })).toBeNull();
    expect(g.pick([d], { now: 5999, cooldownSec: 6 })).toBeNull();
    expect(g.pick([d], { now: 6100, cooldownSec: 6 })).toBe(d);
  });

  it("escalation is announced immediately (after the minimum gap)", () => {
    const g = new AlertGate();
    g.markSpoken(det("car:right", "CAUTION"), 0);
    expect(g.pick([det("car:right", "CAUTION")], { now: 2000, cooldownSec: 6 })).toBeNull();
    const worse = det("car:right", "DANGER");
    expect(g.pick([worse], { now: 2000, cooldownSec: 6 })).toBe(worse);
  });

  it("danger repeats faster than caution", () => {
    const g = new AlertGate();
    const d = det("car:center", "DANGER");
    g.markSpoken(d, 0);
    expect(g.pick([d], { now: 2600, cooldownSec: 8 })).toBe(d);
    const c = det("chair:left", "CAUTION");
    g.markSpoken(c, 3000);
    expect(g.pick([c], { now: 5600, cooldownSec: 8 })).toBeNull();
  });

  it("ignores alerts below the minimum level", () => {
    const g = new AlertGate();
    expect(g.pick([det("bottle:left", "SAFE")], { now: 0, minLevel: "CAUTION" })).toBeNull();
    expect(g.pick([det("bottle:left", "SAFE")], { now: 0, minLevel: "SAFE" })).not.toBeNull();
  });

  it("keeps a minimum gap between different utterances", () => {
    const g = new AlertGate();
    g.markSpoken(det("person:center", "CAUTION"), 1000);
    expect(g.pick([det("chair:left", "CAUTION")], { now: 1500 })).toBeNull();
    expect(g.pick([det("chair:left", "CAUTION")], { now: 2300 })).not.toBeNull();
  });

  it("skips a blocked top alert and speaks the next eligible one", () => {
    const g = new AlertGate();
    const top = det("person:center", "WARNING");
    const next = det("dog:left", "CAUTION");
    g.markSpoken(top, 0);
    expect(g.pick([top, next], { now: 2000, cooldownSec: 6 })).toBe(next);
  });
});
