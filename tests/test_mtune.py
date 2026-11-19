"""mtune: the P gain that puts the Nichols curve on a closed-loop M-contour."""
import control as ctl
import numpy as np
import pytest

from evans.core.pidtune import tune_p_for_peak


def test_second_order_integrator_matches_the_closed_form():
    # G = 1/(s(s+1)): Mr = 1/(2ζ√(1-ζ²)) and K = 1/(4ζ²).
    M = 10 ** (2.3 / 20)
    r = tune_p_for_peak(ctl.tf([1], [1, 1, 0]), M)
    zeta = np.sqrt((1 - np.sqrt(1 - 1 / M**2)) / 2)
    assert r.K == pytest.approx(1 / (4 * zeta**2), rel=1e-3)
    assert r.peak_db == pytest.approx(2.3, abs=1e-3)


def test_below_zero_db_is_impossible_for_an_integrator():
    with pytest.raises(ValueError):
        tune_p_for_peak(ctl.tf([1], [1, 1, 0]), 0.9)
