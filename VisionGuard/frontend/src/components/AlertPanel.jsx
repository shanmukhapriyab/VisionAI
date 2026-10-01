import { LevelIcon } from "./Icons.jsx";

const POSITIONS = [["left", "Left"], ["center", "Center"], ["right", "Right"]];
const WORD = { SAFE: "Safe", CAUTION: "Caution", WARNING: "Warning", DANGER: "Danger" };

export default function AlertPanel({ phase, result }) {
  const running = phase === "running";
  const dets = result?.detections || [];
  const top = dets[0];
  const level = !running ? "IDLE" : top ? top.danger.level : "SAFE";

  let message = "Detection is off.";
  if (running && !result) message = "Waiting for the first result…";
  else if (running && top) message = top.message;
  else if (running) message = "No known objects in view.";

  const lane = (pos) => dets.find((d) => d.position === pos);

  return (
    <section className="alert" data-level={level} aria-labelledby="alert-h">
      <h2 id="alert-h" className="alert-badge">
        {level !== "IDLE" && <LevelIcon level={level} size={30} />}
        <span>{level === "IDLE" ? "Off" : WORD[level]}</span>
      </h2>
      <p className="alert-message">{message}</p>
      {running && top && top.danger.reasons.length > 0 && (
        <p className="alert-why">{top.danger.reasons.join(" · ")}</p>
      )}

      <div className="lanes" role="group" aria-label="What is on your left, ahead and right">
        {POSITIONS.map(([pos, title]) => {
          const d = running ? lane(pos) : null;
          return (
            <div key={pos} className="lane" data-level={d ? d.danger.level : "NONE"}>
              <span className="lane-title">{title}</span>
              {d ? (
                <>
                  <span className="lane-obj"><LevelIcon level={d.danger.level} size={18} /> {d.name}</span>
                  <span className="lane-dist">{d.distance_m.toFixed(1)} m{d.approaching ? " · approaching" : ""}</span>
                </>
              ) : (
                <span className="lane-none">Nothing detected</span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
