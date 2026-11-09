"""Huge matrices print as their corners, not as millions of lines."""

import numpy as np
import pytest

from evans.console.matlab_runtime import display


@pytest.mark.parametrize("shape", [(1_300_000, 2), (2, 1_300_000), (500, 300)])
def test_large_matrix_display_is_short(shape):
    text = display(np.zeros(shape))
    assert len(text.splitlines()) < 40
    assert f"{shape[0]}×{shape[1]} double" in text


def test_small_matrix_display_is_complete():
    assert len(display(np.ones((5, 3))).splitlines()) == 5
