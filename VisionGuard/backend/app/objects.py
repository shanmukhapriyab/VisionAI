"""Catalog of detectable objects with typical real-world sizes (metres).

Sizes are rough averages used ONLY for approximate monocular distance estimation.
"""
from dataclasses import dataclass

# Object kinds
PERSON = "person"
VEHICLE = "vehicle"
TWO_WHEELER = "two_wheeler"
ANIMAL = "animal"
FURNITURE = "furniture"
FIXED = "fixed"
SMALL_ITEM = "small_item"
SIGNAL = "signal"

# Kinds that can move by themselves (used for "approaching / moving" wording).
MOVABLE_KINDS = {PERSON, VEHICLE, TWO_WHEELER, ANIMAL}
VEHICLE_KINDS = {VEHICLE, TWO_WHEELER}


@dataclass(frozen=True)
class ObjectSpec:
    label: str      # COCO class name
    name: str       # spoken / displayed name
    kind: str
    height_m: float
    width_m: float


_SPECS = [
    ObjectSpec("person", "Person", PERSON, 1.70, 0.50),
    ObjectSpec("car", "Car", VEHICLE, 1.50, 1.80),
    ObjectSpec("bus", "Bus", VEHICLE, 3.00, 2.50),
    ObjectSpec("truck", "Truck", VEHICLE, 3.00, 2.50),
    ObjectSpec("bicycle", "Bicycle", TWO_WHEELER, 1.00, 0.60),
    ObjectSpec("motorcycle", "Motorcycle", TWO_WHEELER, 1.20, 0.80),
    ObjectSpec("chair", "Chair", FURNITURE, 0.90, 0.50),
    ObjectSpec("bench", "Bench", FIXED, 0.85, 1.50),
    ObjectSpec("backpack", "Backpack", SMALL_ITEM, 0.50, 0.30),
    ObjectSpec("bottle", "Bottle", SMALL_ITEM, 0.25, 0.07),
    ObjectSpec("dog", "Dog", ANIMAL, 0.50, 0.30),
    ObjectSpec("cat", "Cat", ANIMAL, 0.30, 0.20),
    ObjectSpec("traffic light", "Traffic light", SIGNAL, 0.90, 0.35),
    ObjectSpec("stop sign", "Stop sign", SIGNAL, 0.75, 0.75),
    # Extra common indoor/outdoor obstacles
    ObjectSpec("fire hydrant", "Fire hydrant", FIXED, 0.70, 0.35),
    ObjectSpec("couch", "Couch", FURNITURE, 0.85, 2.00),
    ObjectSpec("dining table", "Table", FURNITURE, 0.75, 1.40),
    ObjectSpec("potted plant", "Plant pot", FURNITURE, 0.60, 0.40),
    ObjectSpec("suitcase", "Suitcase", SMALL_ITEM, 0.60, 0.40),
]

CATALOG: dict[str, ObjectSpec] = {s.label: s for s in _SPECS}


def get_spec(label: str) -> ObjectSpec | None:
    return CATALOG.get(label)
