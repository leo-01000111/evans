"""
Log every zero-crossing restart of a simulation.

    python tools/sim_restarts.py [model.evx] [--t-end 10] [--solver RK45]

Without a model it runs the shipped ``pid_saturation`` example. For each
restart it prints the event time, which block's crossing value fired (and
that value's index among the block's crossings), the value at the event,
and whether any block's latched mode changed. At the end: the number of
restarts, of restarts that changed no mode, of right-hand-side calls, and
the wall time.

It wraps the solver's private hooks, so it is a diagnostic, not an API.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from evans.examples import FOLDER  # noqa: E402
from evans.sim import SimModel  # noqa: E402
from evans.sim import solver as S  # noqa: E402


def run(path: Path, t_end: float, solver: str, quiet: bool = False) -> dict:
    model = SimModel.load(path)
    log: list[tuple] = []
    counts = {"rhs": 0}

    orig_cross = S._cross
    orig_eval = S._Evaluator.derivatives

    def modes(ev):
        return {bid: (None if getattr(p.block, "_mode", None) is None
                      else tuple(np.atleast_1d(p.block._mode)))
                for bid, p in ev.c.plans.items()}

    def cross(ev, layout, rhs, t_e, y_e, xd, fired, sides, h_ref):
        owners = [(bid, k) for bid, n in layout for k in range(n)]
        before = modes(ev)
        zc = ev.zero_crossings(t_e, y_e, xd, ev.evaluate(t_e, y_e, xd), layout)
        out = orig_cross(ev, layout, rhs, t_e, y_e, xd, fired, sides, h_ref)
        after = modes(ev)
        changed = {b: (before[b], after[b]) for b in after
                   if before[b] != after[b]}
        log.append((t_e, [(owners[i], float(zc[i])) for i in fired], changed))
        return out

    def derivatives(self, *a, **k):
        counts["rhs"] += 1
        return orig_eval(self, *a, **k)

    S._cross = cross
    S._Evaluator.derivatives = derivatives
    try:
        t0 = time.perf_counter()
        res = S.simulate(model, t_end=t_end, solver=solver)
        wall = time.perf_counter() - t0
    finally:
        S._cross = orig_cross
        S._Evaluator.derivatives = orig_eval

    silent = sum(1 for _, _, ch in log if not ch)
    if not quiet:
        for t_e, fired, changed in log:
            what = ", ".join(f"{b}[{k}]={v:+.3g}" for (b, k), v in fired)
            mode = "; ".join(f"{b}: {o} -> {n}" for b, (o, n) in changed.items())
            print(f"t = {t_e:10.6f}  {what:40s}  {mode or 'NO MODE CHANGE'}")
        for w in res.warnings:
            print("warning:", w)
    summary = {"restarts": len(log), "no_mode_change": silent,
               "rhs": counts["rhs"], "wall": wall, "result": res}
    print(f"{path.name}: {len(log)} restarts ({silent} changed no mode), "
          f"{counts['rhs']} RHS calls, {wall:.2f} s")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?",
                    default=str(Path(FOLDER) / "pid_saturation.evx"))
    ap.add_argument("--t-end", type=float, default=10.0)
    ap.add_argument("--solver", default="RK45")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    run(Path(a.model), a.t_end, a.solver, a.quiet)


if __name__ == "__main__":
    main()
