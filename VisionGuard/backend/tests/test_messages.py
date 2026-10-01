from app.messages import build_message


def test_person_ahead():
    assert build_message("Person", "person", "center", 4.0, "CAUTION", False) == "Person ahead."


def test_chair_on_left():
    assert build_message("Chair", "furniture", "left", 3.0, "CAUTION", False) == "Chair on your left."


def test_vehicle_approaching_from_right():
    msg = build_message("Car", "vehicle", "right", 8.0, "WARNING", True)
    assert msg == "Warning. Vehicle approaching from your right."


def test_stop_when_very_close():
    msg = build_message("Chair", "furniture", "center", 0.7, "DANGER", False)
    assert msg.startswith("Stop.") and "very close" in msg


def test_warning_includes_spoken_distance():
    assert "about 2 meters" in build_message("Person", "person", "center", 2.0, "WARNING", False)


def test_signals_are_informational():
    assert build_message("Stop sign", "signal", "center", 3, "CAUTION", False) == "Stop sign ahead."
    assert build_message("Traffic light", "signal", "left", 3, "SAFE", False) == "Traffic light on your left."


def test_static_object_is_never_said_to_approach():
    msg = build_message("Chair", "furniture", "center", 1.5, "WARNING", True)
    assert "approaching" not in msg
