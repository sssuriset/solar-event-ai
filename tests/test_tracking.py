"""Synthetic association tests: no claim of real-event identification."""
from datetime import datetime, timedelta, timezone

import pytest

from solar_event_ai.tracking import associate, summarize, read_detections


def row(frame, x, y, *, obsid="test", flagged=""):
    return dict(obsid=obsid, frame=str(frame), time_utc="2026-01-01T00:00:%02d+00:00" % (frame*5),
                x_px=str(x), y_px=str(y), area_px="9", peak_delta_dn_s="50",
                peak_temporal_sigma="9", qc_flags=flagged,
                _frame=frame, _time=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=5*frame),
                _x=float(x), _y=float(y), _area=9, _peak=50.)


def test_repeated_brightening_forms_one_track():
    rows = [row(i, 10+i, 10) for i in range(4)]
    tracks = associate(rows)
    assert len(tracks) == 1
    summary = summarize(tracks)[0]
    assert summary["n_detections"] == 4
    assert summary["observed_span_s"] == 15
    assert summary["apparent_displacement_px"] == 3


def test_simultaneous_sources_remain_separate():
    rows = [row(i, x, 20) for i in range(3) for x in (10, 50)]
    tracks = associate(rows)
    assert sorted(len(t) for t in tracks) == [3, 3]
    assert len(set(r["track_id"] for r in rows if r["_frame"] == 1)) == 2


def test_time_and_distance_gates_split_tracks():
    rows = [row(0, 0, 0), row(1, 40, 40), row(5, 0, 0)]
    assert len(associate(rows, max_gap_frames=2)) == 3


def test_single_frame_is_preserved_for_review():
    rows = [row(0, 10, 10, flagged="near_image_edge")]
    tracks = associate(rows)
    summary = summarize(tracks)[0]
    assert summary["observed_span_s"] == 0
    assert summary["review_status"] == "short_track_needs_review"
    assert summary["qc_flags_any"] == "near_image_edge"


def test_nearby_competing_assignment_is_flagged():
    rows = [row(0, 10, 10), row(0, 13, 10), row(1, 11, 10)]
    tracks = associate(rows, ambiguity_margin_px=1.5)
    assert len(tracks) == 2
    assert rows[2]["association_ambiguous"] is True


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        associate([row(0, 0, 0)], max_distance_px=0)
