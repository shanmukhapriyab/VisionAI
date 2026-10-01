// Draws bounding boxes on the overlay canvas. Colour + line style + label text all encode the level,
// so the meaning never depends on colour alone.
const STYLE = {
  SAFE: { dash: [], width: 2, fill: 0 },
  CAUTION: { dash: [10, 5], width: 3, fill: 0.05 },
  WARNING: { dash: [4, 3], width: 4, fill: 0.1 },
  DANGER: { dash: [], width: 6, fill: 0.2 },
};

export function drawDetections(canvas, detections, colors, opts = {}) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (!detections?.length) return;

  const fontPx = Math.max(13, Math.min(18, w / 46));
  ctx.font = `700 ${fontPx}px "Atkinson Hyperlegible", system-ui, sans-serif`;
  ctx.textBaseline = "middle";

  // draw least dangerous first so dangerous boxes end up on top
  [...detections].reverse().forEach((d) => {
    const c = colors[d.danger.level];
    const st = STYLE[d.danger.level];
    const x = d.box.x1 * w, y = d.box.y1 * h;
    const bw = (d.box.x2 - d.box.x1) * w, bh = (d.box.y2 - d.box.y1) * h;

    ctx.lineWidth = st.width;
    ctx.strokeStyle = c.bg;
    ctx.setLineDash(st.dash);
    if (st.fill) {
      ctx.globalAlpha = st.fill;
      ctx.fillStyle = c.bg;
      ctx.fillRect(x, y, bw, bh);
      ctx.globalAlpha = 1;
    }
    ctx.strokeRect(x, y, bw, bh);
    ctx.setLineDash([]);

    if (opts.labels === false) return;
    const dist = `${d.distance_m.toFixed(1)} m`;
    const text = `${d.name} ${Math.round(d.confidence * 100)}% · ${dist} · ${d.position.toUpperCase()}`;
    const pad = 6;
    const tw = ctx.measureText(text).width + pad * 2;
    const th = fontPx + 10;
    let ly = y - th;
    if (ly < 0) ly = y;
    const lx = Math.min(Math.max(0, x), Math.max(0, w - tw));
    ctx.fillStyle = c.bg;
    ctx.fillRect(lx, ly, tw, th);
    ctx.fillStyle = c.ink;
    ctx.fillText(text, lx + pad, ly + th / 2 + 1);
  });
}

// Box colours are fixed (bright, on a dark label) so they stay legible on top of any camera image.
export const BOX_COLORS = {
  SAFE: { bg: "#3ddc97", ink: "#04140d" },
  CAUTION: { bg: "#ffd23f", ink: "#1a1400" },
  WARNING: { bg: "#ff9f43", ink: "#1c0e00" },
  DANGER: { bg: "#ff5470", ink: "#1f0008" },
};
