"""Turns a scored detection into a short sentence for text-to-speech."""
from .danger import CAUTION, DANGER, WARNING
from .geometry import spoken_distance
from .objects import MOVABLE_KINDS, VEHICLE, SIGNAL

_WHERE = {"center": "ahead", "left": "on your left", "right": "on your right"}
_FROM = {"center": "from ahead", "left": "from your left", "right": "from your right"}


def _spoken_name(spec_name: str, kind: str, approaching: bool) -> str:
    if approaching and kind == VEHICLE:
        return "Vehicle"
    return spec_name


def build_message(name: str, kind: str, position: str, distance_m: float,
                  level: str, approaching: bool) -> str:
    where, frm = _WHERE[position], _FROM[position]
    if kind == SIGNAL:
        return f"{name} {where}."
    moving_thing = approaching and kind in MOVABLE_KINDS
    label = _spoken_name(name, kind, moving_thing)

    if level == DANGER:
        if moving_thing:
            return f"Stop. {label} approaching {frm}."
        return f"Stop. {label} very close {where}." if distance_m <= 1.2 else f"Stop. {label} {where}."
    if level == WARNING:
        if moving_thing:
            return f"Warning. {label} approaching {frm}."
        return f"Warning. {label} {where}, {spoken_distance(distance_m)}."
    if level == CAUTION and moving_thing:
        return f"{label} approaching {frm}."
    return f"{label} {where}."
