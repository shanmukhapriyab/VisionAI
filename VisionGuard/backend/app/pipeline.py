"""Frame -> detections -> distance/position/motion -> danger -> message."""
import time

from . import config
from .danger import assess_danger, prioritize
from .geometry import distance_label, estimate_distance, horizontal_position
from .messages import build_message
from .objects import get_spec
from .tracker import Tracker

SESSION_TTL_S = 120


class FramePipeline:
    def __init__(self, detector):
        self.detector = detector
        self._trackers: dict[str, Tracker] = {}
        self._last_used: dict[str, float] = {}

    def reset_session(self, session_id: str):
        self._trackers.pop(session_id, None)

    def _tracker(self, session_id: str, now: float) -> Tracker:
        for sid in [s for s, t in self._last_used.items() if now - t > SESSION_TTL_S]:
            self._trackers.pop(sid, None)
            self._last_used.pop(sid, None)
        self._last_used[session_id] = now
        return self._trackers.setdefault(session_id, Tracker())

    def process(self, image_bgr, session_id: str = "default",
                conf: float = config.DEFAULT_CONFIDENCE, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        t0 = time.perf_counter()
        h, w = image_bgr.shape[:2]

        raws = self.detector.detect(image_bgr, conf)
        t_inf = time.perf_counter()

        prepared = []
        for r in raws:
            spec = get_spec(r.label)
            if spec is None:
                continue
            est = estimate_distance(r.label, r.box, w, h)
            nbox = (r.box[0] / w, r.box[1] / h, r.box[2] / w, r.box[3] / h)
            prepared.append((r, spec, est, nbox))

        states = self._tracker(session_id, now).update(
            [(p[0].label, p[3], p[2].meters) for p in prepared], now)

        dets = []
        for (r, spec, est, nbox), st in zip(prepared, states):
            position = horizontal_position(r.box, w)
            dist = st.distance_m
            approaching = st.approaching
            danger = assess_danger(spec.kind, dist, position, st.closing_speed_mps, approaching)
            movable = spec.kind in ("person", "vehicle", "two_wheeler", "animal")
            message = build_message(spec.name, spec.kind, position, dist, danger.level, approaching)
            dets.append({
                "track_id": st.track_id,
                "label": r.label,
                "name": spec.name,
                "kind": spec.kind,
                "confidence": round(r.confidence, 3),
                "box": {"x1": round(nbox[0], 4), "y1": round(nbox[1], 4),
                        "x2": round(nbox[2], 4), "y2": round(nbox[3], 4)},
                "distance_m": dist,
                "distance_label": distance_label(dist),
                "distance_reliable": est.reliable,
                "position": position,
                "approaching": bool(approaching and movable),
                "moving": bool(movable and (approaching or st.lateral_moving)),
                "closing_speed_mps": st.closing_speed_mps,
                "danger": {"level": danger.level, "score": danger.score, "reasons": danger.reasons},
                "message": message,
                "alert_key": f"{r.label}:{position}",
            })
        dets = prioritize(dets)
        top = dets[0] if dets else None
        t_end = time.perf_counter()
        return {
            "ok": True,
            "frame": {"width": w, "height": h},
            "detections": dets,
            "summary": {
                "level": top["danger"]["level"] if top else "SAFE",
                "message": top["message"] if top else None,
                "alert_key": top["alert_key"] if top else None,
                "count": len(dets),
            },
            "timing": {"inference_ms": round((t_inf - t0) * 1000, 1),
                       "total_ms": round((t_end - t0) * 1000, 1)},
        }
