"""Tuning a PID to stated limits (core/pidlimits.py), Qt-free."""

import control as ctl
import pytest

from evans.core.pidlimits import LIMIT_KINDS, tune_to_limits

PLANT = ctl.tf([1], [1, 3, 3, 1])


def test_pi_meets_overshoot_settling_and_dc_error():
    r = tune_to_limits(PLANT, "PI", {"overshoot": 10, "settling": 8,
                                     "dc_error": 1})
    assert r.met, r.describe()
    assert r.tune.stable
    by = {c.key: c for c in r.checks}
    assert by["overshoot"].value <= 10
    assert by["settling"].value <= 8
    assert by["dc_error"].value <= 1


def test_pid_meets_a_margin_limit():
    r = tune_to_limits(PLANT, "PID", {"overshoot": 5, "phase_margin": 60})
    assert r.met, r.describe()
    assert r.tune.achieved_pm_deg >= 60 - 1e-6


def test_p_controller_cannot_remove_dc_error_and_says_so():
    r = tune_to_limits(PLANT, "P", {"dc_error": 0.1})
    assert not r.met
    assert not r.checks[0].met
    assert "Not every limit" in r.describe()


def test_contradictory_limits_report_the_miss_not_a_lie():
    r = tune_to_limits(PLANT, "PID", {"overshoot": 0.5, "settling": 0.05})
    assert not r.met
    assert any(not c.met for c in r.checks)


def test_the_loop_in_the_result_is_stable_and_uses_the_gains():
    r = tune_to_limits(PLANT, "PI", {"overshoot": 15})
    assert r.tune.params.Ki > 0 and r.tune.params.Kd == 0
    assert r.tune.stable


def test_no_limits_gives_a_plain_stable_design():
    r = tune_to_limits(PLANT, "PI", {})
    assert r.tune.feasible and r.tune.stable and r.met


def test_unknown_limit_is_an_error():
    with pytest.raises(ValueError, match="unknown limit"):
        tune_to_limits(PLANT, "PI", {"bandwidth": 3})


def test_every_limit_kind_has_a_direction():
    assert {d for _l, _u, d in LIMIT_KINDS.values()} == {"max", "min"}


def test_zones_cover_the_stated_limits():
    from evans.core.pidlimits import EDGE, limit_zones

    zones = limit_zones({"overshoot": 10, "settling": 3, "rise": 1,
                         "dc_error": 2, "phase_margin": 45}, 0.05, t10=0.4)
    by = {}
    for z in zones:
        by.setdefault(z.key, []).append(z)
    assert set(by) == {"overshoot", "settling", "rise", "dc_error"}
    (over,) = by["overshoot"]
    assert over.y0 == pytest.approx(1.1) and over.y1 == EDGE
    above, below = by["settling"]
    assert above.t0 == below.t0 == 3
    assert above.y0 == pytest.approx(1.05) and below.y1 == pytest.approx(0.95)
    (rise,) = by["rise"]
    assert rise.t0 == pytest.approx(1.4) and rise.y1 == 0.9
    assert all(z.at_end for z in by["dc_error"])


def test_crossing_time_interpolates():
    import numpy as np

    from evans.core.pidlimits import crossing_time

    t = np.array([0.0, 1.0, 2.0])
    y = np.array([0.0, 0.5, 1.0])
    assert crossing_time(t, y, 0.25) == pytest.approx(0.5)
    assert crossing_time(t, y, 2.0) is None


def test_five_percent_band_settles_no_later_than_two():
    a = tune_to_limits(PLANT, "PI", {"settling": 6}, settling_band=0.02)
    b = tune_to_limits(PLANT, "PI", {"settling": 6}, settling_band=0.05)
    assert b.checks[0].value <= a.checks[0].value + 1e-9 or b.met
    assert "±5 %" in b.checks[0].label
