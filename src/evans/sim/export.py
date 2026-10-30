"""
A run's signals, written to a file: CSV for a spreadsheet, ``.mat`` for
MATLAB (or Evans's own ``load``).

The CSV has a ``t`` column and one column per signal channel, named
``block.port`` (``block.port[2]`` for the second channel of a vector).
Duplicate times are kept: two rows at one instant are how a held sample's
step is recorded, and dropping either would turn the step into a ramp.

The ``.mat`` file holds ``tout`` and one matrix per signal, its name made a
valid MATLAB identifier (``G.out`` becomes ``G_out``), with every channel a
column. ``scipy.io.savemat`` writes the version 5 format MATLAB reads.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np


def export_signals(result, path: str | Path,
                   names: list[str] | None = None) -> Path:
    """Write ``result``'s signals (all, or ``names``) to CSV or ``.mat``."""
    path = Path(path)
    chosen = list(names) if names is not None else sorted(result.signals)
    missing = [n for n in chosen if n not in result.signals]
    if missing:
        raise KeyError(f"no signal {', '.join(missing)}")
    suffix = path.suffix.lower()
    if suffix == ".mat":
        _write_mat(result, path, chosen)
    elif suffix in (".csv", ".txt"):
        _write_csv(result, path, chosen)
    else:
        kind = suffix or "a file without an extension"
        raise ValueError(f"cannot export to {kind}; use .csv or .mat")
    return path


def _columns(result, names):
    for name in names:
        data = np.asarray(result.signals[name], dtype=float)
        for channel in range(data.shape[1]):
            label = name if data.shape[1] == 1 else f"{name}[{channel + 1}]"
            yield label, data[:, channel]


def _write_csv(result, path: Path, names) -> None:
    columns = list(_columns(result, names))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", *[label for label, _ in columns]])
        for i, t in enumerate(result.t):
            writer.writerow([repr(float(t)),
                             *[repr(float(values[i])) for _, values in columns]])


def mat_name(name: str) -> str:
    """A signal name as a MATLAB variable: letters, digits, underscores."""
    ident = re.sub(r"\W", "_", name)
    if not ident or not ident[0].isalpha():
        ident = "s_" + ident
    return ident[:63]


def _write_mat(result, path: Path, names) -> None:
    from scipy.io import savemat
    data = {"tout": np.asarray(result.t, dtype=float).reshape(-1, 1)}
    for name in names:
        key = mat_name(name)
        while key in data:
            key = key[:60] + "_x"
        data[key] = np.asarray(result.signals[name], dtype=float)
    savemat(str(path), data)
