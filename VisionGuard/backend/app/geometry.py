"""Approximate distance and horizontal position from a bounding box.

Distance uses the pinhole camera model:  distance = focal_px * real_height / pixel_height.
It is an ESTIMATE that depends on the assumed camera field of view and the assumed
typical object size. Treat it as "roughly this far", never as a measurement.
"""
import math
from dataclasses import dataclass

from .config import CAMERA_HFOV_DEG
from .objects import get_spec

LEFT_MAX = 0.35    # centre of box left of 35% of frame width  -> LEFT
RIGHT_MIN = 0.65   # centre of box right of 65% of frame width -> RIGHT
MIN_DISTANCE_M = 0.2
MAX_DISTANCE_M = 40.0
EDGE_MARGIN_PX = 3


@dataclass(frozen=True)
class DistanceEstimate:
    meters: float
    reliable: bool   # False when the box is cut off by the frame edge
    method: str


def focal_length_px(frame_width: float, hfov_deg: float = CAMERA_HFOV_DEG) -> float:
    return (frame_width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)


def estimate_distance(label, box, frame_w, frame_h, hfov_deg=CAMERA_HFOV_DEG) -> DistanceEstimate:
    """box = (x1, y1, x2, y2) in pixels."""
    spec = get_spec(label)
    if spec is None:
        raise ValueError(f"Unknown object label: {label}")
    x1, y1, x2, y2 = box
    bw = max(float(x2 - x1), 1.0)
    bh = max(float(y2 - y1), 1.0)
    f = focal_length_px(frame_w, hfov_deg)
    d_h = f * spec.height_m / bh
    d_w = f * spec.width_m / bw

    cut_v = y1 <= EDGE_MARGIN_PX or y2 >= frame_h - EDGE_MARGIN_PX
    cut_h = x1 <= EDGE_MARGIN_PX or x2 >= frame_w - EDGE_MARGIN_PX
    if cut_v or cut_h:
        # Object is partly out of frame, so the truncated side under-measures its size.
        # Use the smaller (closer) of the two estimates to stay on the cautious side.
        meters, method, reliable = min(d_h, d_w), "min(height,width)", False
    else:
        meters, method, reliable = d_h, "height", True
    meters = min(max(meters, MIN_DISTANCE_M), MAX_DISTANCE_M)
    return DistanceEstimate(round(meters, 2), reliable, method)


def horizontal_position(box, frame_w) -> str:
    x1, _, x2, _ = box
    cx = ((x1 + x2) / 2.0) / float(frame_w)
    if cx < LEFT_MAX:
        return "left"
    if cx > RIGHT_MIN:
        return "right"
    return "center"


def distance_label(meters: float) -> str:
    if meters < 1.0:
        return "very close"
    if meters < 2.0:
        return "close"
    if meters < 4.0:
        return "near"
    return "far"


def spoken_distance(meters: float) -> str:
    if meters < 1.5:
        return "about 1 meter"
    return f"about {int(round(meters))} meters"
