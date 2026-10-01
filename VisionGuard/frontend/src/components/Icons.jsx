// Small inline SVG icons. Danger-level icons use different SHAPES so they can be told apart without colour.
const base = { width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2.2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true, focusable: false };
const I = (children) => (props) => <svg {...base} {...props}>{children}</svg>;

export const PlayIcon = I(<path d="M7 4.5v15l12-7.5z" fill="currentColor" />);
export const StopIcon = I(<rect x="5.5" y="5.5" width="13" height="13" rx="2" fill="currentColor" />);
export const VoiceOnIcon = I(<><path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor" /><path d="M15.5 9a4.5 4.5 0 0 1 0 6M18 6.5a8 8 0 0 1 0 11" /></>);
export const VoiceOffIcon = I(<><path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z" fill="currentColor" /><path d="m16 9.5 5 5m0-5-5 5" /></>);
export const SirenIcon = I(<><path d="M6 18v-5a6 6 0 0 1 12 0v5" /><path d="M4 20h16M12 3v2M3.5 7l1.5 1M20.5 7 19 8" /></>);
export const SunIcon = I(<><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" /></>);
export const MoonIcon = I(<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z" />);
export const CameraIcon = I(<><path d="M4 8h3l1.5-2.5h7L17 8h3v11H4z" /><circle cx="12" cy="13.5" r="3.5" /></>);

const filled = { fill: "currentColor", stroke: "none" };
export function LevelIcon({ level, size = 22 }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", "aria-hidden": true, focusable: false };
  switch (level) {
    case "DANGER":   // octagon
      return <svg {...p}><path d="M8.2 2h7.6L22 8.2v7.6L15.8 22H8.2L2 15.8V8.2z" {...filled} /><path d="M12 6.5v7M12 16.2v1.6" stroke="var(--icon-ink)" strokeWidth="2.6" strokeLinecap="round" /></svg>;
    case "WARNING":  // diamond
      return <svg {...p}><path d="M12 1.5 22.5 12 12 22.5 1.5 12z" {...filled} /><path d="M12 7v6M12 15.8v1.5" stroke="var(--icon-ink)" strokeWidth="2.6" strokeLinecap="round" /></svg>;
    case "CAUTION":  // triangle
      return <svg {...p}><path d="M12 2.5 22.5 21h-21z" {...filled} strokeLinejoin="round" /><path d="M12 9.5v5M12 17.2v1.2" stroke="var(--icon-ink)" strokeWidth="2.4" strokeLinecap="round" /></svg>;
    default:         // circle with tick
      return <svg {...p}><circle cx="12" cy="12" r="10" {...filled} /><path d="m7.5 12.3 3 3 6-6.3" fill="none" stroke="var(--icon-ink)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
  }
}
