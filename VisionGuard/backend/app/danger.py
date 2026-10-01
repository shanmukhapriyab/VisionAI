"""Danger classification: SAFE / CAUTION / WARNING / DANGER.

Score (0-100) = distance score x object-kind factor x position factor + time-to-collision bonus.
A few explicit safety floors then guarantee that the most obvious hazards can never be
under-rated by the arithmetic.
"""
from dataclasses import dataclass, field

from .objects import (ANIMAL, FIXED, FURNITURE, PERSON, SIGNAL, SMALL_ITEM, TWO_WHEELER,
                      VEHICLE, VEHICLE_KINDS)

SAFE, CAUTION, WARNING, DANGER = "SAFE", "CAUTION", "WARNING", "DANGER"
LEVELS = [SAFE, CAUTION, WARNING, DANGER]
RANK = {lvl: i for i, lvl in enumerate(LEVELS)}

CAUTION_MIN, WARNING_MIN, DANGER_MIN = 15.0, 35.0, 55.0

KIND_FACTOR = {
    VEHICLE: 1.4, TWO_WHEELER: 1.3, PERSON: 1.0, ANIMAL: 0.9,
    FURNITURE: 0.75, FIXED: 0.75, SMALL_ITEM: 0.35, SIGNAL: 0.25,
}
POSITION_FACTOR = {"center": 1.0, "left": 0.6, "right": 0.6}
VERY_CLOSE_M = 0.8


@dataclass(frozen=True)
class DangerAssessment:
    level: str
    score: float
    reasons: list = field(default_factory=list)

    @property
    def rank(self) -> int:
        return RANK[self.level]


def distance_score(d: float) -> float:
    if d <= 1.0:
        return 60.0
    if d <= 2.0:
        return 45.0
    if d <= 3.5:
        return 30.0
    if d <= 6.0:
        return 16.0
    if d <= 10.0:
        return 6.0
    return 0.0


def level_from_score(score: float) -> str:
    if score >= DANGER_MIN:
        return DANGER
    if score >= WARNING_MIN:
        return WARNING
    if score >= CAUTION_MIN:
        return CAUTION
    return SAFE


def _raise_to(level: str, floor: str) -> str:
    return floor if RANK[floor] > RANK[level] else level


def time_to_collision(distance_m: float, closing_speed_mps: float, approaching: bool):
    if not approaching or closing_speed_mps <= 0.05:
        return None
    return distance_m / closing_speed_mps


def assess_danger(kind: str, distance_m: float, position: str,
                  closing_speed_mps: float = 0.0, approaching: bool = False) -> DangerAssessment:
    reasons = []
    kf = KIND_FACTOR.get(kind, 0.75)
    pf = POSITION_FACTOR.get(position, 0.6)
    score = distance_score(distance_m) * kf * pf
    if distance_m <= 2.0:
        reasons.append("very near" if distance_m <= 1.0 else "near")
    if position == "center":
        reasons.append("in your path")

    ttc = time_to_collision(distance_m, closing_speed_mps, approaching)
    if ttc is not None:
        bonus = 35.0 if ttc <= 2.0 else 20.0 if ttc <= 4.0 else 10.0 if ttc <= 6.0 else 0.0
        score += bonus * (1.0 if position == "center" else 0.8)
        reasons.append(f"closing at {closing_speed_mps:.1f} m/s")

    score = max(0.0, min(100.0, score))
    level = level_from_score(score)

    # ---- safety floors -------------------------------------------------
    if kind not in (SIGNAL, SMALL_ITEM) and position == "center" and distance_m <= VERY_CLOSE_M:
        level = _raise_to(level, DANGER)
        reasons.append("almost touching")
    if kind in VEHICLE_KINDS and ttc is not None:
        if ttc <= 2.5:
            level = _raise_to(level, DANGER if position == "center" else WARNING)
        if ttc <= 5.0:
            level = _raise_to(level, WARNING)
        if RANK[level] >= RANK[WARNING]:
            reasons.append("vehicle approaching")
    # Signs and lights are information, not obstacles.
    if kind == SIGNAL and RANK[level] > RANK[CAUTION]:
        level = CAUTION
    return DangerAssessment(level, round(score, 1), reasons)


def sort_key(det: dict):
    """Sort key: most dangerous first, then higher score, then closest."""
    return (-RANK[det["danger"]["level"]], -det["danger"]["score"], det["distance_m"])


def prioritize(detections: list) -> list:
    return sorted(detections, key=sort_key)
