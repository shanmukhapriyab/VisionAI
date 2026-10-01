import { useEffect, useRef, useState } from "react";
import { BOX_COLORS, drawDetections } from "../lib/draw.js";
import { CameraIcon } from "./Icons.jsx";

export default function CameraView({ videoRef, phase, result, notice, showLabels, stats }) {
  const canvasRef = useRef(null);
  const [aspect, setAspect] = useState(16 / 9);
  const detsRef = useRef([]);
  detsRef.current = result?.detections || [];

  const redraw = () => canvasRef.current && drawDetections(canvasRef.current, detsRef.current, BOX_COLORS, { labels: showLabels });

  useEffect(redraw, [result, showLabels, aspect, phase]);
  useEffect(() => {
    const ro = new ResizeObserver(redraw);
    ro.observe(canvasRef.current);
    return () => ro.disconnect();
  });

  return (
    <div className="camera" style={{ aspectRatio: aspect }}>
      <video
        ref={videoRef}
        muted
        playsInline
        autoPlay
        aria-label="Live camera feed"
        onLoadedMetadata={(e) => e.target.videoWidth && setAspect(e.target.videoWidth / e.target.videoHeight)}
        className={phase === "running" ? "on" : ""}
      />
      <canvas ref={canvasRef} className="overlay" aria-hidden="true" />
      {phase !== "running" && (
        <div className="camera-empty">
          <CameraIcon width={44} height={44} />
          <p>{phase === "starting" ? "Starting camera and checking the AI model…" : "Camera is off. Press Start detection."}</p>
        </div>
      )}
      {notice && <div className="camera-notice" role="status">{notice}</div>}
      {phase === "running" && (
        <div className="camera-hud" aria-hidden="true">
          <span>{stats.fps ? `${stats.fps.toFixed(1)} FPS` : "… FPS"}</span>
        </div>
      )}
    </div>
  );
}
