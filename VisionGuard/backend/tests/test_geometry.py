import math

import pytest

from app.geometry import (distance_label, estimate_distance, focal_length_px,
                          horizontal_position, spoken_distance)


def test_focal_length_matches_fov():
    f = focal_length_px(640, 90)          # 90 degree FOV -> f == half width
    assert f == pytest.approx(320, rel=1e-6)


def test_person_distance_round_trip():
    """A 1.7 m person at 3 m must be measured as ~3 m (pinhole model round trip)."""
    w, h = 640, 480
    f = focal_length_px(w, 65)
    px_h = f * 1.70 / 3.0
    box = (300, 100, 300 + px_h * 0.3, 100 + px_h)
    est = estimate_distance("person", box, w, h, 65)
    assert est.meters == pytest.approx(3.0, abs=0.05)
    assert est.reliable and est.method == "height"


def test_bigger_box_means_closer():
    near = estimate_distance("chair", (100, 50, 400, 450), 640, 480).meters
    far = estimate_distance("chair", (100, 200, 160, 300), 640, 480).meters
    assert near < far


def test_truncated_box_is_flagged_unreliable_and_cautious():
    # feet cut off at bottom of frame
    est = estimate_distance("person", (200, 100, 300, 480), 640, 480)
    assert est.reliable is False
    full = estimate_distance("person", (200, 100, 300, 470), 640, 480)
    assert est.meters <= full.meters + 1e-6


def test_distance_is_clamped():
    assert estimate_distance("person", (0, 0, 1, 1), 640, 480).meters <= 40
    assert estimate_distance("bottle", (10, 10, 600, 470), 640, 480).meters >= 0.2


def test_unknown_label_raises():
    with pytest.raises(ValueError):
        estimate_distance("unicorn", (0, 0, 10, 10), 640, 480)


@pytest.mark.parametrize("box,expected", [
    ((0, 0, 100, 100), "left"),
    ((270, 0, 370, 100), "center"),
    ((540, 0, 640, 100), "right"),
    ((0, 0, 640, 100), "center"),       # very wide object filling the frame is ahead
])
def test_position(box, expected):
    assert horizontal_position(box, 640) == expected


def test_labels():
    assert distance_label(0.5) == "very close"
    assert distance_label(1.5) == "close"
    assert distance_label(3) == "near"
    assert distance_label(9) == "far"
    assert spoken_distance(1.0) == "about 1 meter"
    assert spoken_distance(2.4) == "about 2 meters"
