import pytest

from app.danger import (CAUTION, DANGER, SAFE, WARNING, assess_danger, level_from_score,
                        prioritize)


def lvl(*a, **k):
    return assess_danger(*a, **k).level


def test_thresholds():
    assert level_from_score(0) == SAFE
    assert level_from_score(15) == CAUTION
    assert level_from_score(35) == WARNING
    assert level_from_score(55) == DANGER


@pytest.mark.parametrize("dist,expected", [
    (10.0, SAFE), (5.0, CAUTION), (3.0, CAUTION), (2.0, WARNING), (0.9, DANGER),
])
def test_person_in_path_by_distance(dist, expected):
    assert lvl("person", dist, "center") == expected


def test_side_objects_are_less_dangerous_than_center():
    assert assess_danger("person", 2.0, "left").score < assess_danger("person", 2.0, "center").score


def test_small_items_are_low_priority():
    assert lvl("small_item", 2.0, "center") in (SAFE, CAUTION)


def test_very_close_obstacle_in_path_is_always_danger():
    assert lvl("furniture", 0.7, "center") == DANGER
    assert lvl("fixed", 0.5, "center") == DANGER
    assert lvl("small_item", 0.5, "center") != DANGER      # a bottle is not a "Stop" event


def test_signals_never_exceed_caution():
    assert lvl("signal", 0.5, "center") == CAUTION or lvl("signal", 0.5, "center") == SAFE
    assert lvl("signal", 0.5, "center") != DANGER


def test_approaching_vehicle_center_is_danger():
    a = assess_danger("vehicle", 6.0, "center", closing_speed_mps=4.0, approaching=True)
    assert a.level == DANGER
    assert "vehicle approaching" in a.reasons


def test_approaching_vehicle_side_is_at_least_warning():
    a = assess_danger("vehicle", 12.0, "right", closing_speed_mps=4.0, approaching=True)
    assert a.rank >= 2


def test_far_slow_vehicle_is_not_alarming():
    assert lvl("vehicle", 25.0, "center", closing_speed_mps=0.2, approaching=False) == SAFE


def test_approach_raises_person_level():
    still = assess_danger("person", 3.0, "center")
    moving = assess_danger("person", 3.0, "center", closing_speed_mps=1.5, approaching=True)
    assert moving.score > still.score
    assert moving.rank >= still.rank


def test_score_is_bounded():
    a = assess_danger("vehicle", 0.3, "center", closing_speed_mps=30, approaching=True)
    assert 0 <= a.score <= 100


def _det(level, score, dist):
    return {"danger": {"level": level, "score": score}, "distance_m": dist}


def test_prioritize_orders_by_level_then_score_then_distance():
    items = [_det(CAUTION, 20, 4), _det(DANGER, 60, 1), _det(WARNING, 40, 2), _det(WARNING, 40, 1.5)]
    out = prioritize(items)
    assert [d["danger"]["level"] for d in out] == [DANGER, WARNING, WARNING, CAUTION]
    assert out[1]["distance_m"] == 1.5
