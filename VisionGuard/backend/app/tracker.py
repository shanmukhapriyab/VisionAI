"""Very small multi-object tracker used to estimate motion between frames.

Detections are matched to existing tracks by IoU (same class). For every track we
keep a short history of smoothed distance and horizontal centre, and fit a line to
get a closing speed (m/s, positive = getting closer) and a lateral speed.

IMPORTANT LIMITATION: the camera itself moves when the user walks, so "closing speed"
is RELATIVE speed. A static chair the user walks toward also has a positive closing
speed - which is a valid hazard - but the app only says "approaching" for things that
can move on their own (people, vehicles, animals).
"""
import math
from collections import deque
from dataclasses import dataclass, field

WINDOW_S = 1.6
MIN_SAMPLES = 3
MIN_SPAN_S = 0.5
APPROACH_SPEED_MPS = 0.6
LATERAL_SPEED_PER_S = 0.30     # fraction of frame width per second
EMA_ALPHA = 0.6
IOU_MIN = 0.25
CENTROID_MAX = 0.10


@dataclass
class Track:
    id: int
    label: str
    box: tuple
    first_seen: float
    last_seen: float
    dist: float
    hits: int = 1
    samples: deque = field(default_factory=lambda: deque(maxlen=24))  # (t, dist, cx)


@dataclass(frozen=True)
class TrackState:
    track_id: int
    distance_m: float
    closing_speed_mps: float
    lateral_speed: float
    approaching: bool
    lateral_moving: bool
    hits: int


def iou(a, b) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _center(b):
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def _match_score(a, b) -> float:
    i = iou(a, b)
    if i >= IOU_MIN:
        return i
    (ax, ay), (bx, by) = _center(a), _center(b)
    d = math.hypot(ax - bx, ay - by)
    return 0.05 + (CENTROID_MAX - d) if d < CENTROID_MAX else 0.0


def _slope(points):
    """Least-squares slope of y over t for [(t, y), ...]."""
    n = len(points)
    mt = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    den = sum((p[0] - mt) ** 2 for p in points)
    if den < 1e-9:
        return 0.0
    return sum((p[0] - mt) * (p[1] - my) for p in points) / den


class Tracker:
    def __init__(self, max_age_s: float = 1.5):
        self.max_age_s = max_age_s
        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    def reset(self):
        self._tracks.clear()

    def update(self, observations, now: float) -> list[TrackState]:
        """observations: list of (label, box_normalised(x1,y1,x2,y2 in 0..1), distance_m).
        Returns one TrackState per observation, in the same order."""
        # drop stale tracks
        for tid in [t for t, tr in self._tracks.items() if now - tr.last_seen > self.max_age_s]:
            del self._tracks[tid]

        pairs = []
        for di, (label, box, _) in enumerate(observations):
            for tid, tr in self._tracks.items():
                if tr.label != label:
                    continue
                s = _match_score(tr.box, box)
                if s > 0:
                    pairs.append((s, di, tid))
        pairs.sort(reverse=True)

        assigned: dict[int, int] = {}
        used_tracks = set()
        for _, di, tid in pairs:
            if di in assigned or tid in used_tracks:
                continue
            assigned[di] = tid
            used_tracks.add(tid)

        states: list[TrackState] = []
        for di, (label, box, dist) in enumerate(observations):
            if di in assigned:
                tr = self._tracks[assigned[di]]
                tr.dist = EMA_ALPHA * dist + (1 - EMA_ALPHA) * tr.dist
                tr.box, tr.last_seen = box, now
                tr.hits += 1
            else:
                tr = Track(self._next_id, label, box, now, now, dist)
                self._tracks[tr.id] = tr
                self._next_id += 1
            tr.samples.append((now, tr.dist, _center(box)[0]))
            states.append(self._state(tr, now))
        return states

    def _state(self, tr: Track, now: float) -> TrackState:
        window = [s for s in tr.samples if now - s[0] <= WINDOW_S]
        closing = lateral = 0.0
        if len(window) >= MIN_SAMPLES and window[-1][0] - window[0][0] >= MIN_SPAN_S:
            closing = -_slope([(s[0], s[1]) for s in window])
            lateral = _slope([(s[0], s[2]) for s in window])
        approaching = tr.hits >= MIN_SAMPLES and closing >= APPROACH_SPEED_MPS
        return TrackState(
            track_id=tr.id,
            distance_m=round(tr.dist, 2),
            closing_speed_mps=round(closing, 2),
            lateral_speed=round(lateral, 2),
            approaching=approaching,
            lateral_moving=abs(lateral) >= LATERAL_SPEED_PER_S and tr.hits >= MIN_SAMPLES,
            hits=tr.hits,
        )
