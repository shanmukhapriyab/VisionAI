import { LevelIcon } from "./Icons.jsx";

export default function DetectionList({ detections, running }) {
  return (
    <section className="panel" aria-labelledby="det-h">
      <h2 id="det-h">In view <span className="count">{running ? detections.length : 0}</span></h2>
      {detections.length === 0 ? (
        <p className="muted">{running ? "No supported objects detected right now." : "Start detection to see objects here."}</p>
      ) : (
        <ul className="det-list">
          {detections.slice(0, 8).map((d) => (
            <li key={d.track_id} data-level={d.danger.level}>
              <span className="det-lvl"><LevelIcon level={d.danger.level} size={20} /><span className="sr-only">{d.danger.level}</span></span>
              <span className="det-name">
                {d.name}
                {d.moving && <em className="tag">{d.approaching ? "approaching" : "moving"}</em>}
              </span>
              <span className="det-meta">
                {Math.round(d.confidence * 100)}% · {d.distance_reliable ? "" : "≈ "}{d.distance_m.toFixed(1)} m · {d.position}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="fineprint">Distances are rough estimates from object size, not measurements.</p>
    </section>
  );
}
