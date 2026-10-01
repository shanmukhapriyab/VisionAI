from app.tracker import Tracker, iou


def obs(dist, cx=0.5, w=0.2, label="car"):
    return (label, (cx - w / 2, 0.3, cx + w / 2, 0.7), dist)


def run(distances, dt=0.2, **kw):
    t, tr, last = Tracker(), 0.0, None
    for d in distances:
        last = tr_state = t.update([obs(d, **kw)], now=tr)[0]
        tr += dt
    return last


def test_iou_basics():
    assert iou((0, 0, 1, 1), (0, 0, 1, 1)) == 1.0
    assert iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0.0


def test_track_id_is_stable_across_frames():
    t = Tracker()
    ids = {t.update([obs(10 - i * 0.1)], now=i * 0.2)[0].track_id for i in range(6)}
    assert len(ids) == 1


def test_two_objects_get_different_ids():
    t = Tracker()
    s = t.update([obs(5, cx=0.2, label="person"), obs(5, cx=0.8, label="person")], now=0)
    assert s[0].track_id != s[1].track_id


def test_approaching_object_detected():
    st = run([12, 11, 10, 9, 8, 7, 6, 5])     # 5 m/s closing at 0.2 s steps
    assert st.approaching
    assert st.closing_speed_mps > 2


def test_stationary_object_not_approaching():
    st = run([6.0, 6.05, 5.95, 6.0, 6.02, 5.98, 6.0])
    assert not st.approaching
    assert abs(st.closing_speed_mps) < 0.5


def test_receding_object_not_approaching():
    st = run([4, 5, 6, 7, 8, 9])
    assert not st.approaching and st.closing_speed_mps < 0


def test_lateral_motion_detected():
    t, last = Tracker(), None
    for i in range(8):
        last = t.update([obs(6, cx=0.1 + i * 0.1)], now=i * 0.2)[0]
    assert last.lateral_moving and last.lateral_speed > 0


def test_needs_minimum_history_before_claiming_approach():
    t = Tracker()
    assert not t.update([obs(5)], now=0)[0].approaching
    assert not t.update([obs(2)], now=0.2)[0].approaching     # only 2 samples


def test_stale_tracks_expire():
    t = Tracker(max_age_s=1.0)
    first = t.update([obs(5)], now=0)[0].track_id
    second = t.update([obs(5)], now=5)[0].track_id
    assert first != second
