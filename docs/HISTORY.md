# Evans history

What was built, in order, with the decisions taken on the way and why, the numbers
that were measured, and the limits that were accepted. **Open work is not here:** it is
in `docs/ROADMAP.md`, the only place an open item lives. When a roadmap item is done,
its text and notes move to the end of the matching part below.

This file replaced five planning documents on 2026-11-19: the v1 spec
(`docs/PLAN-v1-classical-spec.md`), the v2 plan (`docs/PLAN.md`), the UI redesign plan
(`docs/UI-PLAN.md`), the 1.0 proposal (`docs/1.0-PROPOSAL.md`) and the finished half of
`docs/ROADMAP.md`. Their full text is in git history before that date. Paths and line
numbers in the older parts describe the code as it was then.

1. The v1 spec (September 2026)
2. The v2 plan, phases 1 to 8 (October 2026)
3. The UI redesign, UI-1 to UI-8 (October 2026)
4. The roadmap's finished work, Phases 0 to 6 (from 2026-10-27)
5. The 1.0 proposal (2026-11-11)
6. Phase 8, the interface rework: the audit and the finished packages (from 2026-11-16)

---

## 1. The v1 spec (September 2026)

The first goal: a native desktop tool for the CLACO "Classical Control" course, built on
python-control, scipy, numpy and sympy, with PySide6 and pyqtgraph for the window. The v2
plan (part 2) found it about 90 % implemented and replaced it.

### Architecture (fixed diagram, not free-form)
The block diagram is the course's "chosen architecture" (ch5 slide 16/24):

```
                                  di            do
                                   |             |
 r --> [K1] --> (+)--> e --> [K2] --> u --(+)--> [G] --(+)--> y
                 ^(-)                                          |
                 |                        n --(+)--------------+
                 +---------------------------------------------+
```
Blocks: K1 (feedforward, default 1), K2 (feedback controller), G (plant). Optional sensor H in
the return path (default 1). Signals: inputs r, di, do, n; outputs y, u, e.
Notation from the course: L = K2·G (loop), S = 1/(1+L), T = L/(1+L).
All 8 closed-loop TFs (r,di,do,n → y,u) are derived from these; user picks any (input, output)
pair as the "signal tap" to analyse. Also analyse open-loop G, L, S, T directly.

### Layout
Left panel: SVG-like block diagram drawn with Qt (QGraphicsScene). Click a block → editor panel
below; click a signal label → sets analysis tap. Right panel: tabs.

Block editor — TF input modes: polynomial coefficients; expression string
`(s+1)/(s^2+0.5s+1)` (sympy parse); ZPK; 1st-order preset (K, tau); 2nd-order preset (K, zeta, wn);
pure delay approximation (Pade). Always show the factored/normalised form.

#### Tabs
1. **System** — factored TF, poles/zeros table (Re, Im, zeta, wn, tau), stability verdict,
   minimum-phase check, DC gain, system type.
2. **Time** — step / impulse / ramp for the chosen tap, amplitude & initial value; metrics
   (Mp %, tp, ts at ±2% and ±5%, tr 10–90% and 0–100%, undershoot Mu, y_inf) with markers and
   the ±delta band drawn on the plot. **Parameter sweep overlay**: pick any block parameter
   (e.g. Kp) and a list/range of values → overlaid curves with legend (generalises the old
   "multi-K graph").
3. **Frequency** — Bode (mag dB + phase) with GM, PM, w_c (gain crossover), w_180, -3 dB
   bandwidth, resonant peak Mr marked. Nyquist with -1 point, unit circle, M-circles, modulus
   margin circle. Nichols. Overlay L, S, T. Delay margin printed.
4. **Stability** — Routh table (sympy; with a symbolic K → range of stabilising K), closed-loop
   pole map, Nyquist encirclement count (P, N, Z), root locus vs K.
5. **Performance** — system type, steady-state error for step / ramp / parabola, static error
   constants Kp Kv Ka, disturbance and noise rejection (|S|, |T|), bandwidth, trade-off notes.
6. **Design** — controller structure picker for K2: P / PI / PD / PID (ideal & filtered
   derivative) / lead / lag / lead-lag / custom TF. Live sliders for every parameter → all open
   plots refresh. Ziegler–Nichols buttons (step-response method and ultimate-gain method),
   pinned "snapshots" for before/after comparison.

Extras: save/load session (JSON), export plot PNG, copy MATLAB-style text report, a menu of
presets (1st order, 2nd order under/critically/over-damped, integrator + lag, unstable plant,
non-minimum-phase zero, satellite double integrator from ch2).

---

## 2. The v2 plan, phases 1 to 8 (October 2026)

From a classical-control workbench to a MATLAB slice. All eight phases were finished;
Part 6's backlog was taken over by the roadmap on 2026-10-27. The simulator phase (Phase 4)
has no section of its own here: the engine is `sim/`, described in `docs/CODEMAP.md`.

**Goal.** Make this the tool you'd reach for instead of MATLAB for two courses — CLACO
(classical, `COURSE MATERIAL/…classical_approach…pdf`, 254 slides, ch1–8) and DYBAC (modern /
state space) — plus a Simulink that actually simulates.


---

### Part 0 — Where the project actually stands

#### 0.1 What exists

| Layer | Files | Lines | State |
|---|---|---|---|
| `core/` engine | 8 modules | ~2 100 | Runs. Numerically wrong in places (§0.3). |
| `ui/` | 12 modules | ~2 700 | Launches, all 6 tabs render without crashing. |
| `tests/` | 6 files, 64 tests | ~500 | All green — but they don't test the things that are broken. |
| `debug_runner.py` | 1 | 341 | 148 pass / 3 fail. Genuinely useful; keep and grow it. |

Verified this session: `python -m pytest -q` → 64 passed. Offscreen GUI smoke test cycles all
six tabs, clicks a block and a signal tap, no exceptions.

#### 0.2 What's missing outright

- **No modern control at all.** No state space, no `A,B,C,D`, no controllability/observability,
  no pole placement, no LQR, no observers, no Kalman, no discrete-time. Zero lines.
- **No Simulink.** `ui/diagram/` draws a *picture* of one fixed architecture. There is no model
  object, no block library, no wire editing, no solver, no scope. `FixedDiagramView.update_block`
  only swaps a TF; nothing on the canvas is editable.
- **No command layer.** No console, no workspace, no scripting. A "MATLAB slice" without a
  command window and a variable workspace isn't recognisable as MATLAB.
- **No project hygiene.** Not a git repo. No `pyproject.toml` / `requirements.txt`, no README,
  no CI. `__pycache__/` and `.pytest_cache/` sit in the tree.

#### 0.3 What's broken — measured, not guessed

These are the reason Phase 1 exists. Each was reproduced this session.

**(a) 6 of 12 closed-loop transfer functions are wrong.**
Solved the loop by hand and compared against `CourseArchitecture.get_closed_loop_tf` at
`s = 0.7 + 1.3j` for `G = 1/(s+1)`, `K₂ = (2s+1)/s`:

| Case | Wrong pairs |
|---|---|
| `K₁ = 1, H = 1` | `di→u`, `n→e` |
| `K₁ ≠ 1, H = 1` | `r→e`, `di→u`, `n→e` |
| `K₁ ≠ 1, H ≠ 1` | `r→y`, `r→e`, `di→u`, `do→u`, `n→u`, `n→e` |

Root causes, in `architecture.py:160-220`:
- `di→u` returns `−S·K₂`; the course equation (slide 157, ch5 19/24) and the algebra both give
  `−S·K₂·G`. Missing plant factor. — `architecture.py:198`
- `n→e` returns `+S`; correct is `−S`. Sign flip. — `architecture.py:219`
- `r→e` returns `S`; correct is `S·K₁`. Feedforward dropped. — `architecture.py:186`
- **Every formula assumes `H = 1`.** `loop_tf()` correctly includes `H`, so `T = L/(1+L)` is
  right, but `r→y = T·K₁` is off by `1/H`, and the `u` row ignores `H` entirely. The `H` block is
  drawn on the canvas and editable — so it is a trap, not a feature.

**(b) Every Bode plot is silently truncated.** The tabs call `setLogMode(x=True)` *and* pass
`np.log10(omega)` as the x data. pyqtgraph takes `log10` again internally, so all ω < 1 become
`NaN` and are dropped; the rest is on a doubly-compressed axis. Reproduced directly:

```
pi.setLogMode(x=True); c = pi.plot(np.log10(w), ...)   →  xDisp range: nan nan
pi.setLogMode(x=True); c = pi.plot(w, ...)             →  xDisp range: -2.0 2.0   ← correct
```

18 call sites across `frequency_tab.py`,
`performance_tab.py`,
`design_tab.py`. Confirmed visually in a screenshot: the
magnitude curve starts a third of the way across the axis. **The low-frequency half of every Bode
plot in the app does not exist.** Margin annotations (`add_vline(np.log10(wc))`) land in the wrong
place for the same reason.

**(c) Internal stability is never checked.** Ch6 1/26 defines closed-loop stability as *all*
closed-loop TFs being stable. The app verdicts on one TF at a time, so an unstable pole/zero
cancellation between `K₂` and `G` reports "✓ Stable". This is exactly the trap the chapter exists
to teach; the tool currently teaches the wrong thing.

**(d) Ziegler–Nichols is unusable.** 3 of 3 failures in `debug_runner`. `zn_ultimate` uses
`root_locus` whose `_find_marginal_gain` returns `nan` for every test system, because
`np.sort_complex` re-sorts roots at each `K` so branch tracking is meaningless. `zn_step` raises
on any plant without dead time — correct in principle, but the app offers no Padé delay to create
one (see (f)), so the button can never succeed.

**(e) `nichols()` M-circles are wrong.** The code admits it in a comment, then plots the *Nyquist*
M-circle mapped naïvely to (phase, dB) — that's a different locus. Use
`ctl.nichols_grid` data or derive properly.

**(f) Dead code / stubs.**
- `pure_delay_pade` returns a **tuple**, not a TF: the conversion is below an unconditional
  `return`. — `tf_utils.py:116`. Nothing calls it.
- `SignalGraph.get_tf(fit=True)` imports `tf_utils.fit_frequency_response`, which doesn't exist.
- `LeadLagParams.alpha` defaults to `10.0` with `is_lead=True`, and `lead_tf` raises on `α ≥ 1`.
  The default construction is an exception.
- `analyse()` catches `ZeroDivisionError` for DC gain, but numpy raises a `RuntimeWarning` and
  returns `inf`/`nan` instead — the guard never fires.

**(g) 15 silent `except: pass` / `except: return` in the UI.** When a computation fails the tab
just goes blank. Debugging is guesswork.

**(h) Usability, from the screenshots.** `_auto_tspan` uses `50/|Re(p)|`, so a pole at −1 gives a
50 s window and the whole transient is squeezed into the left 5% of the plot. The diagram panel is
a 320–520 px column holding a diagram rendered at ~15% of the available area. The metrics table
shows 2 rows of 10.

#### 0.4 One genuinely good thing

`SignalGraph.frequency_response` — the `(I − H·A)⁻¹` matrix solver in
`signal_graph.py:161` — is **correct**. I checked all 12
input/output pairs against hand-solved ground truth: 9 exact, and the 3 `n→*` mismatches are a
pure sign-convention difference (the graph subtracts noise at `architecture.py:287`,
the course diagram adds it), not an error in the solver.

So the *numerical* path is right and the *hand-derived analytic* path is wrong. That inverts the
obvious fix and drives decision D1.

---

### Part 1 — What "MATLAB slice" means here

Scope, explicitly bounded. Everything in **Have** or **Build**; **Won't** is stated so it doesn't
creep back in.

| MATLAB thing | Verdict |
|---|---|
| Control System Toolbox — classical (tf, step, bode, nyquist, nichols, margin, rlocus, routh) | Have, needs fixing |
| Control System Toolbox — modern (ss, ctrb, obsv, place, lqr, kalman, c2d, gram, balred) | **Build** (Phase 3) |
| Simulink — canvas, block library, solvers, scopes, subsystems | **Build** (Phase 4) |
| Command Window + Workspace + scripting | **Build** (Phase 5) |
| LTI Viewer / `sisotool` / PID Tuner style apps | **Build** (Phase 6) |
| Symbolic Math (Routh with free `K`, partial fractions, Laplace) | Partly have; extend |
| Simscape, Stateflow, code generation, HDL, MIMO robust control (H∞, μ) | **Won't** |
| General-purpose numerics (matrix language, `.m` file compatibility) | **Won't** — Python is the language; MATLAB-shaped *aliases* only |

The unifying idea: **one model, many views.** A Simulink model can be linearised into a TF/SS and
land in the analysis tabs; a TF designed in the analysis tabs can be dropped into a Simulink
model. That bridge is what makes it a slice of MATLAB rather than two unrelated apps.

---

### Part 2 — Six decisions to make before writing code

**D1 — The block-diagram graph becomes the single source of truth; derive TFs *exactly*, not per-ω.**
Delete the hand-written formulas in `architecture.py`. Build one `Model` graph and derive any
input→output TF by symbolic linear solve over ℝ(s): build `(I − H(s)·A)` with sympy rational
entries, solve, `cancel` to `N(s)/D(s)`, convert to a `control.TransferFunction`. This gives exact
poles/zeros (so Routh, root locus and pole maps stay correct) and handles any topology including
`H ≠ 1`, which is what breaks today. Keep the existing numeric solver as the cross-check oracle in
tests. *Cost:* ~1 day. *Payoff:* class (a) bugs become structurally impossible, and free-form
Simulink topologies get analysis for free.

**D2 — Write our own simulation engine; do not build Simulink on `ctl.interconnect`.**
`interconnect` works well for the pure-continuous nonlinear case (spiked it: PI + saturation +
plant, 1001 points in 0.13 s, correct clipping). But it **cannot mix timebases** — a continuous
plant and a discrete controller raises `ValueError: Systems have incompatible timebases`. A
Simulink without multi-rate isn't Simulink. Build a proper engine (Phase 4.2) and use
`interconnect` only as a validation oracle for continuous-only models.

**D3 — Keep the fixed course architecture as a *preset*, not as the architecture.**
The ch5 2-DOF diagram is the spine of the course and must stay one click away. But it becomes a
saved `Model` file that the generic engine loads — not a hard-coded class. Prevents the
codebase from forking into "fixed" and "free-form" halves.

**D4 — MATLAB compatibility is aliases, not a language.** *(Superseded: the Script tab
gained a MATLAB translator in Phase 8, and since 0.9.6 the console prompt runs MATLAB
through it too — MATLAB is the default language everywhere, Python the fallback.)*
No `.m` parser. A Python REPL with a preloaded namespace where `tf`, `step`, `bode`, `margin`,
`lqr`, `place`, `c2d`, `stepinfo` behave MATLAB-shaped. Course snippets mostly transcribe;
nobody maintains a parser. If `.m` support is wanted later it's an additive Phase 8.

**D5 — No slycot; use scipy for the linear-algebra gaps.**
Verified: `lqr`, `place`, `acker`, `lqe`, `care`, `dare`, `ctrb`, `obsv`, `c2d` all work without
it. `ctl.gram` raises `ControlSlycot`. Wrap `scipy.linalg.solve_continuous_lyapunov` /
`solve_discrete_lyapunov` ourselves — 20 lines, avoids a Fortran toolchain on Windows.
Also note `ctl.d2c` does not exist in 0.10.1; implement it.

**D6 — Errors surface, always.**
Replace all 15 silent handlers with a `@guard` decorator that draws the traceback into the panel
and logs it. A blank tab must become impossible.

---

### Part 3 — Target structure

```
app.py
src/evans/
  core/
    tf_utils.py        (fix: pade, dc_gain; add partial fractions, Laplace pairs)
    model.py       NEW  Model/Block/Port/Connection — the one graph type
    algebra.py     NEW  exact symbolic I/O transfer functions over the graph  [D1]
    internal.py    NEW  internal stability, hidden modes, pole-zero cancellation  [0.3c]
    timeresp.py        (fix: _auto_tspan, settling on non-convergent)
    freqresp.py        (fix: nichols M-circles; migrate off deprecated ctl.bode)
    stability.py       (fix: root-locus branch tracking; add Jury)
    performance.py     (keep)
    tuning.py          (fix: lead/lag defaults; rebuild Z-N on fixed root locus)
    statespace.py  NEW  ss, tf↔ss, canonical forms, similarity, minreal
    structural.py  NEW  ctrb/obsv, PBH, Kalman decomposition, Gramians, balred  [D5]
    statefbk.py    NEW  place, acker, LQR, LQI, servo augmentation, Nbar
    observers.py   NEW  Luenberger, reduced-order, Kalman, separation principle
    discrete.py    NEW  c2d/d2c, Jury, discrete rlocus, deadbeat
    sim/           NEW  the Simulink engine  [D2]
      blocks/          library: sources, continuous, discrete, math, nonlinear, routing, sinks
      compile.py       flatten subsystems, classify, sort, detect algebraic loops
      solver.py        fixed/variable step, multi-rate scheduler, zero-crossing events
      linearize.py     numerical Jacobian about an operating point → ss  (the bridge)
      io.py            .fmdl JSON save/load
  ui/
    plots.py           (fix: log-axis contract; BodeAxisItem with decade ticks)
    diagram/           rewritten as the live canvas: palette, wiring, undo, params
    console/       NEW  REPL dock, workspace browser, figure windows  [D4]
    tabs/              existing 6, fixed + 5 new modern-control tabs
tests/
  golden/          NEW  analytic ground truth (2nd-order metrics, known margins, LQR on a
                        textbook plant) — the tests that would have caught §0.3
docs/
```

---

### Part 4 — Phases

Each phase ends with a stated acceptance test. Estimates are focused working days.

#### Phase 1 — Correctness ✅ **DONE**

1. ✅ `core/model.py` + `core/algebra.py`: exact symbolic I/O TFs over a graph. [D1]
2. ✅ `CourseArchitecture` ported onto it; the 12 hand-derived formulas deleted.
3. ✅ Log-axis contract fixed in `plots.py` — `make_freq_plot` / `plot_freq` /
   `freq_vline` / `freq_marker` / `freq_text` all take **raw ω**, with a `LogFreqAxis`
   giving decade majors and 2…9 minors.
4. ✅ `core/internal.py`: internal stability over all 12 TFs, hidden-mode and
   cancellation detection, plus a `deceptive` flag for the case where the reference
   response looks clean and the loop is not.
5. ✅ `_auto_tspan`, root-locus branch tracking (Hungarian assignment), exact
   `marginal_gain` via sympy, `pure_delay_pade`, `LeadLagParams`, Nichols M-contours,
   `dc_gain`.
6. ✅ `@guard` + `ErrorBanner`; all 15 silent handlers gone.
7. ✅ Migrated off deprecated `ctl.bode(plot=False)`.

**Also found and fixed during the work** (not in the original plan):
- `ctl.stability_margins` returns **six** values `(gm, pm, sm, wpc, wgc, wms)`; slicing
  the first four silently reports the stability margin as a crossover frequency.
  Now unpacked in exactly one wrapper.
- `compute_step_metrics` estimated `y∞` from the tail of a finite simulation, biasing
  every settling/rise time by ~6%. Now uses the exact `amplitude·G(0)` when stable.
- `guard` nesting: an inner guard's banner was cleared by the outer guard's success
  path. Fixed with a generation counter.
- Design tab could build an invalid lead/lag (α on the wrong side of 1); α is now
  constrained to the selected structure.

**Acceptance — met.** `tests/golden/` asserts all 12 closed-loop TFs against hand-solved
algebra for `K₁≠1, H≠1` *and* against the independent numerical solver; 2nd-order
`Mp`/`tp`/`ts`/`tr` against the ch.4 closed forms; margins against
`control.stability_margins` and analytic values (`1/(s+1)³` → GM 18.06 dB at √3);
`Ku=8, ωu=√3` exactly; no NaN below ω=1. **210 tests pass** (was 64).
`debug_runner.py`: **153 pass, 0 errors** (was 148/3).

#### Phase 2 — Make the classical half genuinely good ✅ **DONE**

- ✅ Layout: left panel widened to 420–760 px and the diagram height capped, so a 3.3:1
  diagram no longer renders at 15% of a tall empty column; `fit_view` resets the
  transform and double-click re-fits. Metrics table sized for all ten rows.
- ✅ Symbolic Routh now **reduces the conjunction** of first-column inequalities to an
  interval: `0 < K < 6`, `-1 < K < 8`, `K > 1`. Cross-checked against `marginal_gain`.
- ✅ Padé delay wired into the block editor as two new modes — *Pure delay (Padé)* and
  *FOPDT (delay + lag)* — which is what makes the Z-N reaction-curve button reachable.
- ✅ Bode templates (gabarits, ch.6 25–26/26 and ch.7 17/20): low-frequency `|S| ≤ s_d`
  and high-frequency `|T| ≤ t_n` drawn as forbidden regions on `|L|`, with an
  infeasibility warning when they overlap.
- ✅ Bode–Freudenberg (ch.7 18/20) computed, not just asserted: `∫ln|S|dω` evaluated on
  a three-segment grid, verified against `π·Σ Re(pₖ)` to 4e-8 for an RHP pole and 4e-5
  for a stable plant. Amplified bands shaded on the trade-off plot. Refuses when the
  closed loop is unstable, since the theorem assumes otherwise.
- ✅ `core/report.py` MATLAB-style text report; `core/session.py` with a versioned
  format, v1 back-compatibility, and all-or-nothing loading. Export menu: copy report,
  save report, export tab as PNG.
- ✅ Corrected `|S| + |T| = 1` → `S + T = 1`; the magnitudes satisfy `|S|+|T| ≥ 1`, and
  the sum is now plotted so the inequality is visible.
- ✅ `factored_str` collapses repeated roots to powers and drops a unit denominator:
  `1/(s+1)³` instead of `(s² + 2s + 1)(s + 1)`.

#### Phase 3 — Modern control ✅ **DONE**

Five core modules, each tested before any UI existed:

| Module | Contents |
|---|---|
| `core/statespace.py` | construction, tf↔ss, similarity transforms, controllable/observable/**modal** forms, minimal realisation, per-mode residues, modal response decomposition |
| `core/structural.py` | ctrb/obsv + ranks, **PBH test per mode**, stabilizability/detectability, Gramians, Hankel singular values, balanced realisation and reduction with its error bound, Kalman decomposition |
| `core/statefbk.py` | robust pole placement, Ackermann, LQR (with the Riccati solution), LQI, `Nbar` reference scaling, control-effort extraction |
| `core/observers.py` | Luenberger, reduced-order, Kalman filter, observer-based compensator, separation-principle verification, estimation-error response |
| `core/discrete.py` | c2d (5 methods, with prewarp), **d2c** (absent from python-control), Jury criterion, deadbeat, sample-rate sweep, z→(ζ, ωn) |

**UI** — one **Modern** tab with five sub-views (State Space · Structure · State
Feedback · Observer/Kalman · Discrete) over a single shared `ModernContext`. Grouped
rather than five top-level tabs, which would have made the tab bar unreadable. Editing
or reducing the model anywhere updates every view, and a design made for the previous
model is cleared rather than silently kept at the wrong dimension. Bridges both ways:
**← Load plant G(s)** and **Send to analysis →**.

**Acceptance — met.**
- LQR on the ch.2 satellite reproduces the analytic Riccati solution
  `K = [1/√R, √((2√R+1)/R)]` to **1e-9** at three weightings, and the returned `P`
  satisfies the ARE to 1e-9.
- `place` and `acker` agree to 1e-7 and both hit the requested eigenvalues to 1e-9.
- `c2d` → `d2c` round-trips to **1e-13** across three plants and two rates.
- A non-minimal realisation is correctly flagged, and `minimal()` reduces it while
  preserving the transfer function to 1e-9.
- The separation principle is *verified*, not asserted: 1.2e-12 mismatch.
- Balanced reduction stays inside the Hankel bound `2·Σσ` at every order.

**Four slycot dependencies routed around** (decision D5 turned out to reach further than
expected — `control.gram` was only the first):
- `minreal` → SVD staircase projection onto the controllable subspace, then its dual.
- `gram` → `scipy.linalg.solve_continuous_lyapunov`.
- `canonical_form(..., "modal")` → eigendecomposition with 2×2 real blocks for
  conjugate pairs.
- `d2c` does not exist at all → matrix logarithm for ZOH, with an explicit refusal when
  no real continuous equivalent exists.

**Bugs found while building:**
- Balancing divided by `√σ` without checking minimality, so a redundant state produced a
  singular transform and silent nonsense rather than an error.
- `_psd_sqrt` via Cholesky failed on a semi-definite Gramian — a perfectly reducible
  system raised `LinAlgError`. Now a symmetric eigendecomposition.
- `control_effort` returned `(1, N)` rows for a 2-output system, which no plotting call
  accepts.
- Qt's `valueChanged` passes the new value into slots also connected to argument-less
  signals, so the Discrete view's refresh raised `TypeError` on every spin-box change.
- `MatrixEditor` parsed inside a Qt slot, outside any `@guard`, so a typo in A escaped as
  a crash instead of reaching the error banner. It now emits raw text and the guarded
  view parses it.
- Eigenvalue plots autoscaled their imaginary axis to round-off (±6e-6), so three
  coincident real poles appeared spread across the plot. `frame_poles` floors the
  imaginary range at a fraction of the real one.

#### Phase 5 — MATLAB shell ✅ **DONE** · [D4]

**`src/evans/console/`** — the API, testable with no display:
- `api.py` — **~60 MATLAB-shaped commands** in nine groups. Not just names: the
  *shapes* match, which is what makes transcription work. `stepinfo` returns MATLAB's
  field names, `margin` returns `(Gm, Pm, Wcg, Wcp)` with `Gm` in absolute units and the
  frequencies in MATLAB's confusing order, `damp` displays a table, `allmargin` adds the
  modulus margin MATLAB omits. `s` is the Laplace variable, so `G = 1/(s**2+2*s+1)`
  works. Every command delegates to the same core functions the tabs use — a console
  that disagreed with a tab would be worse than no console.
- `figures.py` — a plot command builds a **`FigureSpec`** and hands it to the installed
  *sink*. The UI installs one that opens a docked figure; the default just records. That
  is what keeps `step(G)` runnable from a headless script and drawable in the window
  from one implementation.
- `interpreter.py` — persistent namespace, captured output, `ans`, statement-by-statement
  script execution so a failure names the line that stopped it.

**`src/evans/ui/console/`** — command window with transcript, ↑/↓ history, Tab
completion (user names before commands) and Shift+Return continuation; workspace browser
that lists *user* variables only and opens a system in the analysis tabs on double-click;
a capped figure dock; a script editor running against the same workspace (F5).

**Two bridges**, both live rather than copies: the console starts with `G`, `K2`, `arch`
and `model` already bound, so `arch.set_block('G', tf([3],[1,3]))` at the prompt changes
what the tabs analyse. View ▸ *Send current plant to the console* adds `L` and `T`.

**MATLAB habits: accommodated, translated or explained.** A trailing `;` suppresses the
echo. `%` becomes a comment — but only when the line does not already parse, so a real
modulo survives. The rest are **not** silently rewritten, because guessing would change
meaning; each gets a message naming the fix instead:
`[1 2 3]` → "needs commas", `s^2` → "Python uses ** for powers" (caught at *run* time,
since `^` is valid Python), `end` in an index, `~=`, and a case-slipped name.

**The nargout problem.** MATLAB chooses between drawing and returning by counting output
arguments; Python cannot see that. Rather than pick one, the commands return the data
*and* draw, with a one-line `repr` — so `step(T)` at a prompt shows
`<time response: 2000 points over 0…22>` instead of two thousand numbers, and
`t, y = step(T)` still unpacks. `damp` uses the same trick to be a table and a triple at
once.

**Acceptance.** 58 tests: every advertised command exists and is callable, `stepinfo`
reproduces the ch.4 overshoot, `margin` matches the analytic `Gm = 8` at `ω = √3`,
`errconst` and `lqr` agree with the core modules, every figure kind renders, and the
console survives an error and keeps its namespace.

#### Phase 6 — The "apps" ✅ **DONE**

1. ✅ **LTI Viewer** — `core/viewer.py` + `ui/apps/lti_viewer.py`. Any set of systems, seven
   response types, right-click to add characteristics (the MATLAB gesture) with the menu
   offering only the ones that mean something for the response on screen.
2. ✅ **Control System Designer** — `core/designer.py` + `ui/apps/designer_app.py`. Drag a
   closed-loop pole on the root locus; Bode and step follow. Compensator poles/zeros editable,
   plus "set K for ζ" and "set K for overshoot".
3. ✅ **PID Tuner** — `core/pidtune.py` + `ui/apps/pid_tuner.py`. Response-time and
   transient-behaviour sliders, before/after overlay, and a readout that says what each slider
   actually sets.
4. ✅ **Snapshot/compare generalised** — `core/collection.py` + `ui/apps/snapshots.py`. The bar
   sits above the tabs, so a snapshot is of the *architecture*, not of whichever panel is open;
   Compare hands the stored designs to the LTI Viewer.
5. ✅ Console commands `pidtune`, `ltiview`, `sisotool`, `pidtuner`, through an **app sink**
   mirroring the figure sink — so the API stays Qt-free and a typed command and a clicked menu
   item reach the same window.

**Three decisions worth recording.**

*The tuner solves, it does not search.* At the target crossover the controller's required
magnitude and phase are both known, so a PI (two free parameters) is determined outright and a
PID spends its third on the classical `Ti = 4·Td`. The achieved margin is therefore **exact**:
`margin(C·G)` returns the requested `ωc` and `φm` to 1e-14. Where a structure cannot meet a
target — a PI asked to *add* phase — it refuses and names the reason instead of returning gains
that do something else.

*The locus is computed at unit gain*, so it does not move when the gain does. Dragging a pole is
then a position on a fixed curve, which is what makes the gesture legible; `evaluate()` takes the
locus back as an argument so a drag costs no root solves.

*A dragged point is projected onto the locus*, not fed to `K = 1/|L(s)|`. Off the locus that
formula answers a different question, and the reported distance says how far off the request was.

**Acceptance.** 79 tests (511 total, up from 432) and 22 more `debug_runner` checks (175, 0
errors). The golden values are analytic: ζ = 0.5 on `1/(s(s+1)(s+2))` gives **K = 28/27** exactly
(hand-derived in the test's docstring), the overshoot and damping entry points agree to 1e-5, a
known gain round-trips through `point_to_gain` to 1e-10, and the locus crossing comes back as
K = 6, ω = √2.

**Bugs found while building it.**

- **A long plot title silently blanks its panel.** A pyqtgraph title is a `LabelItem` whose
  *minimum* width is the text width, so a 63-character title laid a 434-pixel panel out 1080
  wide and pushed every curve off the right-hand edge. Nothing raised; the values were all
  correct; the plot just looked empty. Fixed centrally in `plots.set_title`, which caps the
  label so the view box drives the layout — this also repaired the console figure view's
  root-locus and Nyquist titles, which had the same defect since Phase 5.
- **Qt flattens a `str`-mixin enum.** `QComboBox.itemData` stores the member in a `QVariant` and
  returns a plain `str`, which compares and hashes equal to the member — so every dict lookup
  still worked and the only symptom was `.value` raising three calls later, in a different file.
- **`_new_session` left stale architecture references** in the snapshot bar and the console, so
  a snapshot taken afterwards would have been of a plant no longer on screen.
- **The neutral crossover is wrong for a PI.** Defined as "where the controller needs no phase",
  it is right for a PID but gives a PI `Ki ≈ 1e-6` — a P controller wearing a PI's name. Each
  structure now aims at the phase it can actually supply.

#### Phase 7 — Course content ✅ **DONE**

A **Lessons** menu with one worked example per chapter (ch2 satellite, ch3 NMP undershoot, ch4 the
second-order family, ch5 the 2-DOF architecture, ch6 margins and M-circles, ch7 the waterbed, ch8
Ziegler–Nichols). Each loads a model, opens the right tab, and shows a note.

**The decision that makes this worth having.** A lesson contains no prose about numbers. It
contains `Claim` objects — a sentence, a *probe* that measures the quantity from whatever model is
loaded, and the value the theory predicts. The panel shows predicted beside measured, and
`test_lessons.py` checks every claim of every lesson. A note that stops being true fails the build
instead of quietly misleading a student, and changing the plant turns the ticks into crosses in
front of you, which is a better demonstration than a paragraph.

Claims carry a `mode` — `equals`, `at_least`, `at_most` — because some of the course's results are
bounds. Ch.3's undershoot theorem says *Mu > 1/(e^{c·ts} − 1)*; pinning that to a number would be
asserting the simulation rather than the theorem.

**Acceptance.** 60 tests. 29 claims across 7 lessons, several exact: ωc = √(2^⅔ − 1) and
PM = 180° − 3·arctan ωc for ch6, Pc = 8 and Tc = 2π/√3 for ch8, Mp = exp(−πζ/√(1−ζ²)) for ch4.
Plus the arguments the notes make, checked independently — that *no* proportional gain stabilises
a double integrator (not just the one loaded), and that an unstable pole makes ∫ln|S| = π·Σ Re(pᵢ).

**Two claims of mine that were wrong, and the code was right.**

- "Changing K₁ leaves every closed-loop pole where it was" — false. K₁ is in the reference path, so
  its own pole genuinely joins the r→y response. What is true is that K₁ cannot move the roots of
  1 + L, which is what the claim now measures.
- Ch.6 at K₂ = 1 has |L(0)| = 1 exactly, so the loop *starts* on the 0 dB line and never crosses
  it: no gain crossover, and therefore no phase margin and no delay margin. Not a bug — the
  quantities are defined at a crossing that is not happening. The lesson now uses K₂ = 2 and makes
  the degenerate case an exercise.

#### Phase 8 — Packaging ✅ **DONE**

`git init`, `.gitignore`, `.gitattributes`, `pyproject.toml`, README, and the repository published
at [github.com/leo-01000111/evans](https://github.com/leo-01000111/evans). Then:

1. ✅ **`--check`**, a headless self-test (`src/evans/selftest.py`). Its payload is not smoke
   checks: it runs the course lessons' analytic claims, so a pass means the numbers agree with the
   theory rather than merely that nothing raised. Exit code is the failure count, so
   `app.py --check && deploy` does what it looks like it does.
2. ✅ **CI** — ruff, pytest on Linux *and* Windows, then `app.py --check`. The Linux job installs
   the Qt runtime libraries PySide6 links against even offscreen.
3. ✅ **PyInstaller** one-*folder* build (`packaging/evans.spec`). One-file unpacks the whole
   Qt runtime on every launch; one-folder starts immediately. It builds two entry points over one
   bundle — `Evans.exe` windowed and `Evans-check.exe` console, because a windowed
   executable on Windows has no stdout and `--check` there would set an exit code and print
   nothing.
4. ✅ **ruff clean**, from 301 violations to zero. 225 were auto-fixed, ~20 were real dead code,
   and the rest are configured off *with a stated reason each* rather than silently.

**Acceptance.** `ruff check .` passes. 589 tests. `app.py --check` reports 41/41 in 5.5 s, and
the *frozen* build passes its own self-test.

**What the linter caught that the tests did not.** A blanket rename of unused loop variables hit
three loops in `solver.py` that *do* use the variable — `F821 undefined-name`, in code paths the
suite does not reach. That is the argument for the linter in one example.

**What the frozen build caught that nothing else did.** Three defects in a row, none visible from
the source tree:

1. `collect_submodules("control")` reaches `control.tests`, which imports pytest, whose plugin
   discovery then reaches whatever else is installed — torch, jax, OpenCV, transformers. **1.5 GB**
   from a 340 MB application. Dropped; the static scan already follows what this code imports.
2. Excluding matplotlib and python-control's plotting modules looked free — this app draws with
   pyqtgraph and never calls them. But `control/__init__.py` imports `ctrlplot`, `freqplot`,
   `timeplot` and five more unconditionally, so `import control` became `ModuleNotFoundError`.
   matplotlib is a hard runtime dependency of python-control 0.10. Same for `PySide6.QtTest`,
   which pyqtgraph imports — caught by a test before it reached a build.
3. A Windows console is cp1252 and the report is full of ζ, ω and −, so printing raised
   `UnicodeEncodeError` *inside* a check's `try` block: a display problem recorded as a
   correctness failure, which is a lie about the build. The development shell is UTF-8, so the
   source tree never hit it.
4. **The windowed build would not launch at all.** A GUI executable on Windows has *no standard
   streams* — `sys.stdout` and `sys.stderr` are `None` — and numpy's `f2py/cfuncs.py` does
   `errmess = sys.stderr.write` at import time, reached through `scipy.linalg`. So the launch died
   with `AttributeError: 'NoneType' object has no attribute 'write'` before the window appeared.
   Fixed with a runtime hook (`packaging/rthook_stdio.py`) that supplies discard streams for every
   package at once rather than patching them one by one.

   **The verification hole matters more than the bug.** The self-test passed, and CI was written to
   run it — against `Evans-check.exe`, the *console* build, which does have streams. The
   entry point people actually double-click was the one never tested. CI now self-tests both, and
   a test asserts that it does.

**Deliberately deferred, not overlooked.** `B905` (`zip(..., strict=True)`) is switched off with a
note. Fifteen call sites, mostly in the solver, where a length mismatch between ports and widths
would be a genuine bug — but turning it on blind converts working code into raising code, so it
wants a per-site audit rather than a flag.

---

### Part 5 — Sequencing, risk, and what I'd cut

**Order:** ~~1 → 2 → 4 → 3 → 5 → 6 → 7 → 8~~ — **all eight phases complete.** Phase 4 (Simulink) before Phase 3 (modern control),
because Phase 4 depends on the Phase-1 graph while it's fresh, and because Phase 3's tabs are
additive and low-risk. Total ≈ **28–40 focused days**. Phases 1+2 alone (≈ 1 week) turn a tool
that quietly prints wrong numbers into one you can trust.

| Risk | Mitigation |
|---|---|
| Symbolic TF derivation too slow on big graphs (D1) | Cache per (model-hash, port-pair); fall back to the numeric solver above ~20 blocks |
| Algebraic loops in user-drawn models | Detect at compile, name the cycle on the canvas, offer "insert unit delay / memory block" |
| Stiff models hang the UI | Run the solver on a `QThread` with a progress bar and a cancel button |
| Scope with 1e6 points is unusable | Downsample for display, keep full data for export |
| Phase 4 sprawls | Ship the block table above and stop. Lookup tables, buses and Stateflow are not in scope |

**What I'd cut if time runs short:** Phase 6 apps (nice, not load-bearing), the Python Function
block, `balred`/Hankel, PRBS and chirp sources, and the script editor — keep the console.

**What I would not cut:** Phase 1. Every hour spent on features before the 6 wrong transfer
functions and the truncated Bode plots are fixed is an hour spent making a confident liar.

### Part 6 — Backlog: large features, not scheduled

> **Superseded 2026-10-27 by [ROADMAP.md](ROADMAP.md)**, which ranks every remaining gap
> into phases with TODOs. The table below is kept as history.

Written down 2026-10-16 from a survey of Octave, Scilab/Xcos, OpenModelica, Simulink, Pluto and bdsim.
None of these is in the current round.

| Feature | What it means | Who does it |
|---|---|---|
| ✅ Symbolic maths | `syms s`, `laplace`, `ilaplace`, `simplify`, `subs` on formulas instead of numbers, via SymPy (already a dependency for block algebra). **Done 2026-10-27**, see below. | MATLAB Symbolic Toolbox, Octave `symbolic` |
| Code-first models | Build a Model-tab diagram from a script (`m = Model(); m.add(Gain(2)); m.connect(...)`), round-tripping with the canvas; export diagrams to SVG/Graphviz. | bdsim |
| ✅ Stiff solvers + events | BDF/Radau via `solve_ivp` for stiff models, zero-crossing detection for relay/saturation/switch blocks, progress + abort on long runs. **Done**, see below. | Simulink `ode15s`, OpenModelica DASSL |
| Browser build | Run the Qt-free core (numpy/scipy, FigureSpec sinks) in a web page via Pyodide — nothing to install. | mat2py, Octave Online |

Deferred medium features (wanted, not crucial): variable editor, compare simulation runs,
model workspace + parameter sweep, log a signal from a wire, `sim('model.fmdl')`/`set_param`
from scripts, live parameter sliders.

#### What became of two of them (2026-10-27)

**Stiff solvers and events were already in the engine** by the time this was picked up, and
the table had not caught up: Radau, BDF and LSODA, with Simulink's names mapped onto them;
terminal zero-crossing events with latched modes for every discontinuous block; a progress
bar and a Stop button on a worker thread. One gap was real. Progress, and so Stop, was only
checked at sample hits, and a purely continuous model is one span from 0 to `t_end`: the bar
sat at 0 % and Stop waited for the run to finish. The solver now reports from inside the
right-hand side, throttled to every 0.1 s of wall time rather than by simulated progress, so
a stiff model grinding at one instant still reaches Stop.

**Symbolic maths** is `console/symbolic.py`. A symbolic value is a `Sym` wrapping a SymPy
expression or matrix, printed as MATLAB prints it (`s^2`, `heaviside(t)`, `[x, 1]`). The
runtime sends any operator with a `Sym` side to `symbolic.binary`, which keeps `*` and `.*`
apart; `exp`, `diff`, `inv`, `det`… switch to their symbolic meaning only when an argument
is symbolic. Covered: `syms` (with assumptions), `sym`, `str2sym`, `laplace`, `ilaplace`,
`simplify`, `expand`, `factor`, `collect`, `partfrac`, `numden`, `subs`, `diff`, `int`,
`limit`, `taylor`, `solve`, `sym2poly`/`poly2sym`, `double`, `vpa`, `pretty`, `latex`,
`isAlways`, `heaviside`, `dirac`, `matlabFunction`, `fplot`, and indexing, concatenation
and matrix algebra on symbolic matrices (`C*inv(s*eye(2) - A)*B`). Not covered: symbolic
functions (`syms y(t)`), and so `dsolve`; `ztrans`.

Two places where SymPy's answer is not MATLAB's had to be bridged. `ilaplace` substitutes a
positive `t` so the result has no `heaviside(t)` factor, as MATLAB writes it, but `laplace`
must *not*: a positive `t` makes `dirac(t)` zero before it is integrated. And a two-sided
`limit(1/x, x, 0)` is SymPy's complex infinity, MATLAB's `NaN`.

### Part 7 — Next up (from first hands-on use, 2026-10-16) ✅ **DONE**

1. **Live tab still shows the bottom figure area.** In a live script figures are inline under
   their cell, so the Console's figure strip below is redundant there. Decide: hide it while
   the Live tab is active (keeping "Open in figures" as the way to pop one out larger), or
   argue for keeping it — and record the reasoning either way.
2. **Export report → PDF doesn't work.** Find out why: no TeX engine on PATH (expected
   fallback is HTML plus an install hint — check that message appears), the engine search
   missing MiKTeX's install folder, the background build failing silently, or the .tex not
   compiling. Make the failure visible and the success path work with MiKTeX and tectonic.
3. **Model canvas: middle-mouse-button drag pans the canvas**, as in Simulink.
4. **Script re-run figure bugs** (the clear-and-rerun from round one):
   - Figure numbers keep counting up across runs (3, 4 instead of 1, 2). A full Run that
     clears the previous run's figures should restart numbering, as MATLAB's `close all`
     does.
   - Split puts them in the wrong order after several runs: run 1 gives 1 left / 2 right, run
     3 gives 6 left / 5 right. The older figure should stay left, the newer one right.
   - *Move ↔* does nothing different from pressing Split again when already split. It should
     swap the shown figure to the other side (or be removed if Split already covers it).
5. **Make the repo usable from a fresh clone:** fix the Ubuntu-only algebraic-loop test
   failure so CI is green; add a README Quick start (clone → venv → `pip install -e ".[dev]"`
   → `python app.py` → `pyinstaller …`); choose an open licence and add `LICENSE` (pyproject
   says "Proprietary"); add `.claude/` to `.gitignore`; move `debug_runner.py` and the
   planning docs out of the root; set a repo description; tag a version so CI publishes the
   exe as a GitHub Release anyone can download.

#### How Part 7 was resolved (2026-10-20)

1. **Hidden on the Live tab.** A live script's figures already sit under the cell that drew
   them, which is where they are read; the strip below repeated them at a smaller size and
   took a third of the height from the document. Keeping it would only have helped for
   zooming and saving, and a window does both better. So the strip hides while the Live tab
   shows, and the cell button became *Open in window*, which opens the figure in its own
   window (its *Dock* button still files it in the figure area for later).
2. **The cause was latexmk.** It was tried first, and MiKTeX's latexmk is a Perl script that
   MiKTeX installs without Perl, so every export failed while pdflatex worked. latexmk is
   now last and only used when Perl is found; pdflatex and xelatex run twice. The search
   also covers MiKTeX's and TeX Live's default folders, MiKTeX installs missing packages
   without a prompt, a failing engine falls through to the next, and if all fail the HTML is
   written too and the dialog shows TeX's own `!` error line.
3. **Middle-drag pans** the Model canvas, over blocks and wires too, without disturbing a
   wire that is half drawn.
4. **Figure numbers** are the lowest free number, as in MATLAB, so a cleared run starts at 1
   again. **Split** pairs the selected figure with its neighbour and always puts the newer
   one right — the reported 6-left/5-right came from Split moving whichever tab was
   selected, and from unsplitting appending tabs out of order (tabs now keep drawing order
   on both sides). **Move ↔** swaps the two shown figures when moving one would empty its
   side, instead of folding the split away as Split already does.
5. **Fresh clone:** MIT `LICENSE`; README Quick start; `.claude/` ignored; the plans moved to
   `docs/`, `debug_runner.py` to `tools/`; CI publishes a GitHub Release from a `v*` tag, and
   no longer waits six hours on a hung test.

### Part 8 — Help, navigation, several scripts, an assistant (decided 2026-10-22)

1. **An integrated help window.** A separate top-level window, opened through
   `ui/help.py`'s `open_help(topic)` (the one place every route to help already goes).
   Its pages are hand-written, for the app only. The website keeps its generated reference.
   They cover the 88 console commands in `api._GROUPS` and the MATLAB basics scripts lean
   on (`zeros`, `plot`, `linspace`, `disp`…). Agents draft each page from the code, with a
   runnable example, and they are reviewed in batches before they land.
2. **Hover for syntax, Ctrl+click to go.** Hovering a function shows its syntax in a popup
   (the table in `ui/code/signatures.py`). Ctrl+click on a built-in opens its help page. On
   a local function it jumps to the definition in the same script. On a function defined in a
   `.m` file in the current folder or on the path, it opens that file in a new tab at the
   function.
3. **Several scripts at once, in the Script editor only** (live scripts stay single). Tabs
   with an unsaved-changes marker, and a Save / Discard / Cancel prompt on closing a tab or
   quitting. *Untitled* tabs until the first save. The same tabs reopen on restart, at the
   same cursor. The debugger follows into files: breakpoints in any tab, and stepping into a
   function in another `.m` file opens its tab and pauses there.
4. **An assistant on OpenRouter**, not Claude: Anthropic does not allow a third-party app to
   offer claude.ai subscription sign-in, and driving the user's own Claude Code is a grey
   area for a public download. Instead it is a dockable side panel, on free OpenRouter
   models: a default, plus a picker that lists the current free ones. The key comes only
   from `OPENROUTER_API_KEY` and is never stored. To keep token use low, a request carries
   only the selection (or the `%%` section at the cursor), a workspace summary (names, types
   and sizes, never values) and the last error. It can propose an edit to the active script
   or cell as a diff to accept or reject, and propose a console command that runs only once
   approved. It works in the console, the script and the live script.

**How it is divided:** the help window and its pages (1) and the assistant (4) each get a
session of their own. Several scripts (3) and then hover / Ctrl+click (2), which opens files
in 3's tabs, are done in the main session. The assistant's panel and client are built
standalone first. Its hooks into the editor and console land after 3, which rewrites
`ScriptEditor`.

---

## 3. The UI redesign, UI-1 to UI-8 (October 2026)

The interface plan that followed the v2 plan. It is kept for its principles, its
information architecture and what was found while building it. Phase 8 (part 6) later
replaced its docks with side panels and dissolved the three apps into the Design tab and
the panes; where the two disagree, Phase 8 is what was built. UI-8's last item, moving
the classic analysis tabs onto the shared design system, is still open (roadmap,
Phase 8).

### Purpose

Evans already has a strong functional foundation: classical and modern control analysis, a block-diagram simulator, a MATLAB-shaped command window, lessons, plotting, design tools, and packaged builds. The main weakness is not missing functionality; it is that the interface has grown organically around an older six-tab layout.

This plan redesigns the application around a clearer mental model:

> **One control system, three workspaces, arrangeable panels, and a UI that remembers how the user works.**

The redesign should preserve the numerical engine and existing capabilities while making the application easier to understand, more usable on ordinary screens, and more coherent as a desktop engineering tool.

### Current problems

The current UI is centered on a permanent left-hand architecture panel and a flat tab bar in `src/evans/ui/mainwindow.py`. This causes several measurable problems:

- The application can require approximately 2038 px of horizontal space because the Simulink toolbar is one unbreakable row.
- The permanent architecture/BlockEditor column consumes space on every analysis screen, including Simulink and Modern Control.
- Eight top-level tabs mix three different concepts: views of one analysis model, a block-diagram modeling environment, and a state-space workbench.
- LTI Viewer, Control System Designer, and PID Tuner behave as separate top-level windows instead of parts of one workflow.
- Emoji tab labels can render as missing-glyph boxes and are not a reliable accessible navigation mechanism.
- Important model and stability information is hidden in the status bar and displayed as coefficient arrays rather than readable transfer functions.
- The snapshot bar is always visible despite being an occasional workflow feature.
- Simulink block parameters use modal interactions, making it difficult to edit a block while keeping the diagram visible.
- Window geometry, dock positions, splitter sizes, and workspace state are not persisted.
- Panels do not follow one consistent spacing, typography, or density system.

### Design principles

1. **Preserve functionality.** This is a UI redesign, not a numerical rewrite. Existing analysis, simulation, console, lesson, export, and design features must remain available.
2. **Make the current model obvious.** The user should always know what plant/controller is loaded and whether the system is stable.
3. **Optimize for normal screens.** The application must work at 1280×720 and remain comfortable at 1920×1080.
4. **Use progressive disclosure.** Frequently used actions remain visible; advanced settings live in expandable panels, menus, or docks.
5. **Prefer one main window.** Related tools should be dockable panels rather than disconnected windows.
6. **Use one visual rhythm.** Shared spacing, panel headers, controls, icons, status badges, and error states should be implemented centrally.
7. **Keep state alive.** Switching workspaces or panels should not destroy the user's current analysis or model.
8. **Make errors actionable.** A failed calculation should explain what happened and how to recover; blank panels are not acceptable.

### Target information architecture

Replace the current eight-peer tab structure with three top-level workspaces.

```text
Evans
├── Analyse   Current control system: plots, metrics, stability, design, lessons
├── Model     Simulink-style block-diagram editor and simulation
└── Console   Command window, workspace, scripts, and figures
```

Suggested navigation:

- A compact left navigation rail or sidebar.
- Text labels plus bundled icons; no emoji as the primary navigation mechanism.
- `Ctrl+1` — Analyse
- `Ctrl+2` — Model
- `Ctrl+3` — Console
- A `View → Reset layout` action.

Each workspace owns its panel arrangement and restores it independently.

### Visual design system

Create shared UI primitives and styling rather than styling each tab independently.

#### Spacing and layout

Use a small spacing scale:

- 4 px — compact internal spacing
- 8 px — standard control spacing
- 12 px — section spacing
- 16 px — major panel spacing

Prefer layouts that can shrink gracefully. Avoid fixed widths unless they are required for legibility.

#### Shared components

Create reusable components such as:

- `PanelHeader`
- `SectionCard`
- `MetricCard`
- `StatusBadge`
- `ToolbarGroup`
- `ContextBar`
- `EmptyState`
- `ErrorBanner`
- `PropertyEditor`

#### Typography and labels

- Use consistent heading levels.
- Use plain-language action labels.
- Keep technical notation in plot labels and model summaries where it helps.
- Replace coefficient-array summaries with factored, readable expressions.
- Do not rely on emoji to communicate meaning.

#### Status and severity

Use consistent visual states:

- Neutral / informational
- Success / stable
- Warning / incomplete or undefined
- Error / failed computation
- Critical / unstable system

Color should not be the only indicator; pair badges with text and accessible symbols.

### Error and feedback behavior

The existing guarded-panel/error-banner foundation should be extended consistently.

Every analysis panel should provide:

- A useful empty state before the first calculation.
- Inline validation for invalid inputs.
- A clear explanation when a metric is undefined.
- A recoverable error message instead of a blank plot.
- An expandable technical-details section for debugging.
- Progress and cancellation feedback for long simulations.

Example:

```text
Phase margin is undefined

The selected system does not cross 0 dB, so no phase-margin crossover exists.

[Show details] [Change signal]
```

### Layout persistence

Use `QSettings` to persist:

- Window geometry
- Current workspace
- Dock visibility and positions
- Splitter sizes
- Selected pane layout
- Last-used solver settings
- Recent sessions
- Optional panel visibility

Restore layout on startup, but provide a reliable reset action when a saved layout becomes unusable.

### Accessibility and usability requirements

- Keyboard navigation for all major actions.
- Tooltips for icon-only buttons.
- Meaningful accessible names for controls.
- No emoji-only labels.
- Sufficient contrast for statuses, warnings, and plot annotations.
- Focus order that follows the visual order.
- Do not encode important information only through color.
- Ensure the application remains usable without a mouse for common analysis and simulation tasks.


### Out of scope

This plan does not require:

- Rewriting the numerical/control engine.
- Replacing pyqtgraph.
- Adding a custom theme solely for visual novelty.
- Building a ribbon interface.
- Adding MATLAB `.m` parsing.
- Removing or hiding advanced functionality.
- Replacing native Qt behavior where it is already reliable.

The goal is a clearer, more professional, more responsive interface around the existing capabilities.

---

### Implementation status

One line per phase of the plan (the phase descriptions themselves are in git history).

| Phase | State | Notes |
|---|---|---|
| UI-1 — Make it fit | **done** | Simulink toolbar is a `QToolBar` with overflow. Window minimum 2038×643 → 840×685; the app resizes to 1280×720. Regression test asserts the budget and that no single panel dictates the window width. |
| UI-2 — Context bar and model panel | **done** | `ui/context_bar.py`: factored transfer functions, internal-stability badge, PM/GM/ωc. Diagram and block editor moved to a dock behind Ctrl+\. Analysis area is 99 % of the width at 1280 px. |
| UI-3 — Workspaces and persistence | **done** | `ui/workspace.py`: Analyse / Model / Console on a rail, Ctrl+1/2/3. `QStackedWidget`, so switching preserves live state. `QSettings` on close; View ▸ Reset layout. The console and figures stopped being hidden docks and became the Console workspace. |
| UI-4 — Analysis pane grid | **done** | `ui/panes.py`: 1 / 1×2 / 2×2, fourteen pane kinds. Plot panes *are* `LTIViewer` in compact mode, so the viewer is the multi-system form of the same renderer. Root locus added to `core/viewer.py` as a response kind. The classic tabs remain beside the grid. |
| UI-5 — Dockable applications | **done** | LTI Viewer, Control System Designer and PID Tuner are tabbed docks in Analyse. Opening one from the console navigates to the workspace its edits land in. One top-level window with all three open. |
| UI-6 — Simulink ergonomics | **done** | Click-click wiring fixed; `ui/sim/inspector.py` replaces the modal parameter dialog; port hit areas widened without changing the drawn mark; a standing wiring hint; rubber-band selection; align and distribute as one undo step. Wire routing still draws straight lines. |
| UI-7 — Modern Control regrouping | **done** | The five views renamed to the plan's vocabulary (Model / Structure / Design / Estimation / Discrete), each with a tooltip and accessible name saying what it is for. Control columns scroll instead of dictating width. |
| UI-8 — Visual polish and hardening | **mostly** | Emoji gone from every button and tab label, enforced by a test. `ui/design.py` primitives used by all new surfaces. Tested at 1280×720, 1366×768 and 1920×1080. Bundled icon set added 2026-10-20 (`ui/iconset.py`, 53 SVGs in the theme's ink, app icon on the window and the exe): on the rail, the Model toolbar, the script and live-script run controls, the figure controls and the pane picker. Still outstanding: retrofitting the six classic analysis tabs onto the design system. |

#### Where it ended up

```
MainWindow.minimumSizeHint()   2038 × 643   →   920 × 344
SimTab minimum width                 1602   →       152
Top-level windows with every app open   7   →         1
Analysis area at 1280 px               —    →       99 %
Tests                                 598   →       674
```

#### Things found while implementing

**Qt flattens a `str`-mixin enum through `QVariant`.** `QComboBox.currentData()` returns a
plain `str` that compares and hashes equal to the member, so every dict lookup keeps working
and the only symptom is `.value` raising somewhere else entirely. It bit the LTI Viewer's
response picker and then the pane's source picker; both now rebuild the member from the
combo's text.

**A non-proper closed loop has no time response.** Closing the unity-feedback loop around the
course's non-minimum-phase plant `(1−s)/(1+s)` gives `T = (1−s)/2` — more zeros than poles, no
state-space realisation, no step response. It is reachable from the Presets menu, and it used
to surface as a raw `ValueError` in an error banner. It is a property of the system, not a
failure to compute, so `core/viewer.py` now says so and the pane shows an empty state with the
reason.

**Word-wrapped help text is taller the narrower it gets.** The classic analysis tabs fit at
1400 px and then wanted 748 px of window height at 1280 px, because their control columns wrap.
A height-for-width effect, not a fixed size, and invisible to any check that measures at one
width only. They are scrolled now, so a secondary view cannot set the application's minimum.

**A test that shares a window has to put it back.** The resolution tests measure minimum sizes,
so a pane another test left showing the Modern tab, or an app dock left open, changes the next
test's answer. The reset fixture now restores the workspace, the view, the pane layout *and*
the pane kinds.

---

## 4. The roadmap's finished work, Phases 0 to 6 (from 2026-10-27)

The roadmap was written 2026-10-27 from four audits of the code (MATLAB language,
Simulink, toolboxes, workflow/interop), each gap checked against the source. This was
its view of Evans then:

**Where Evans stands.** It is a credible free tool for control courses and small control
design work: python-control models with MATLAB names, `sisotool`/`pidtuner`/`ltiview`,
exact block algebra, a solver with stiff methods and zero-crossings, `.mlx` opening and
LaTeX reports. It is not yet a general MATLAB replacement. An ordinary engineer's script
usually stops at "Unrecognized function or variable" within a few lines, a colleague's
Simulink model cannot be opened, and logged data in a CSV with a header cannot be loaded.

**The order below follows what a normal user hits first.** Most of Phases 1–3 is wrapping
numpy, scipy and sympy, which Evans already ships, with MATLAB's argument order, so
it is cheap. Phases 6 and 7 are expensive, and the scope decision in 7 comes before any
of that work starts.

Each item below is as it was ticked, with its notes. Where a note says part was not
built, that part is a `[ ]` item in the roadmap.

### Phase 0: Silent wrong answers (core done 2026-10-27)

These gave a wrong value without any error, the failure the v2 plan's Part 5 (part 2 above) ranks worst.
Tests: `tests/golden/test_confident_liars.py`, last section.

- [x] `{1,'a';2,'b'}` was 1×4, and `c{2,1}` read `c{1}`. `Cell` now has a shape, stored
      column by column. Indexing with one or two subscripts, growing, `[a; b]`, `'`,
      `for` over columns, `cell(n)` (n×n), `num2cell` and `fieldnames` (a column) all
      follow it.
- [x] `struct('a',{1,2})` was 1×1 and is now a 1×2 struct array. `{{…}}` stores the
      cell itself.
- [x] `error('my:id','boom %d',3)` used the identifier as the message and lost the
      identifier. `e.identifier` is kept, and `rethrow`, `throw` and `MException`
      were added.
- [x] `persistent` crashed with a Python `UnboundLocalError`, and `global` was
      dropped. Both work now, `global` across function files and the workspace.
- [x] Cells and structs were shared, not copied: after `b = c; b{1} = 5`, `c{1}`
      was 5 too, and the same happened with `t = s; t.a = 9`. `assign` now copies
      each level it writes to.

- [x] Struct arrays are always rows: `struct('a',{1;2})` is 1×2, not 2×1. **S**
      *Done 2026-10-28:* `StructArray` has a shape like `Cell`'s; indexing,
      growing, `'`, `[s; t]` and `for` follow it.
- [x] A `for` loop whose variable is a `global` does not write it back. **S**
      *Done:* a global or persistent loop variable is written each time round.
- [x] `clear all`, `clear global` and `clear functions` do not reset globals or
      persistents. **S** *Done:* MATLAB's rules; plain `clear` keeps a global's
      value and drops only the workspace's link.
- [x] `numel("hello")` is 5 and should be 1 (string arrays, Phase 4). **S–M**
      *Done 2026-11-09 with Phase 4's string arrays: `"…"` is its own type.*
- [x] Writing one element of a cell, struct or array copies it, so growing one in a
      loop is quadratic. `c{end+1} = k` for 10⁴ elements takes about 3.5 s, against
      about 0.5 s before cells were copied; numeric arrays already behaved this way.
      Copy only when the value is shared, for example by marking it at `b = c` and at
      function calls. **M** *Done 2026-11-03 for cells and structs (0.09 s):*
      `share()` in the runtime marks a value, deeply, wherever a second
      reference can appear: every plain store (so `b = c`, `d = c{1}` and a
      builtin's result are all covered), parameters, loop variables, lambda
      captures, `ans`, values put into a container, and everything a Python
      chunk leaves in the workspace. Translated writes pass `owned=True` and
      write an unmarked level in place; library callers still always copy.
      Writing the marked tests turned up a second liar: anonymous functions
      read their variables when called. They now capture them when made.
- [x] The same for numeric arrays: `a(k) = v` copies the array, about 0.4 s for
      10⁴ writes and quadratic past that. **M** An ndarray cannot carry the
      mark, and NumPy views share memory (`b = a(:)` may be a view), so
      in-place writes need their own tracking and tests.
      *Done 2026-11-11:* the runtime keeps a registry, `_OWNED`, of the
      arrays a translated write may change in place: weak references keyed
      by the memory's owner (a view's `.base`), and only arrays `assign`
      has just made itself (the first write's copy, a grown array) are
      entered. `share()` drops the owner of every array it meets, view or
      not, so every place a cell already got marked covers arrays too; a call
      to a library function outside a short list of arithmetic ones, or to
      any Python callable, drops them all, and so do the start and end of
      each console chunk and every turn the event loop gets (poll, pause).
      Dropping only costs one copy. A level of a container that had to be
      copied is no longer written in place below it, and a property with a
      `set.` method never is. Scalar writes into an owned double array take a
      short route (`_poke`). Fill of `zeros(1,n)` by `a(k) = k^2`, this
      machine, before → after: 10³ 0.11 → 0.02 s, 10⁴ 1.25 → 0.24 s,
      10⁵ 16.5 → 1.9 s (a bare loop of 10⁵ is 1.3 s); `A(i,j)` over a
      316×316 matrix 25.9 → 2.6 s. Tests: `tests/golden/test_array_writes.py`.
      *Left:* growing (`a(end+1) = v`) still reallocates each time;
      a fill loop that passes the array to a MATLAB function or a library
      function off the list copies once per call (correct, quadratic again);
      a thread reading the workspace while a loop runs could see writes land.
- [x] **`varargout` in a function file fails**: `function varargout = f()` with
      `varargout{1} = …` gives "Too many output arguments" for `[a, b] = f()`.
      Found 2026-11-11 while checking the site's claims. **S–M** *Done 2026-11-11:
      varargout's elements are returned after the named outputs, `[c{k}] = f()`
      asks for as many outputs as `c{k}` names, and anonymous functions pass
      nargout on. Left: a cs-list mixed with other targets, `[a, c{:}] = f()`.*
- [x] **`true(n)`, `false(m,n)` fail** with "Index exceeds the number of array
      elements": the name resolves to the constant, which is then indexed.
      `logical(zeros(...))` works meanwhile. Found 2026-11-11 during the array-writes
      work; it predates it. **S** *Done 2026-11-11: `true`/`false` are functions
      now, scalar with no arguments.*
- [x] Search the rest of the language for more of these, with a probe script of MATLAB
      lines run against known MATLAB answers. **M** *Done as the Phase 6 reference
      corpus (2026-11-14): it found 32 silent wrong answers, all fixed 2026-11-18 (see
      Phase 6 below). Its other findings are open in the roadmap, Phase 6.*

- [x] **A struct array's field is a comma-separated list** (found 2026-11-23 while
      checking `who`): `{s.a}` of a 1x2 struct array was a 1x1 cell holding a tuple,
      `[s.a]` of text failed, and `f(s.a)` got one argument. `_spread` now splices
      `s.a` (`Runtime.field_list`); test in `tests/golden/test_confident_liars.py`.
- [x] **A cs-list beside other targets,** `[a, c{:}] = f()` and `[d{:}, b] = f()`:
      the list takes as many outputs as it names, counted when the statement runs
      (`Emitter._assign_mixed`, `Runtime.list_part`). Done 2026-11-24; test in
      `tests/golden/test_confident_liars.py`.
- [x] `who` and `whos` inside a function list the function's variables. *Found
      working on 2026-11-23 (`_caller_scope`); the roadmap item was stale.*

### Phase 1: Everyday data work at the console (core done 2026-10-28)

Needed for any "process my logged data" job, whether coursework, a hobby project or test
data at work. All of it is in numpy and scipy already.

The functions live in `src/evans/console/lib_*.py`, one mixin of `_Library` per group
below, with tests in `tests/golden/test_lib_*.py`. *`fitlm` came with Phase 4's `table`. Every
command has had a help page since 2026-11-03 (`interp`, which only refuses, aside).*

**File I/O** **M**
- [x] `readmatrix`, `writematrix`, `csvread`, `csvwrite`, `dlmread`, with a header row
      skipped.
      *Also `dlmwrite`.*
- [x] `readtable` and `writetable` with column names, together with a real `table`
      (see Phase 4). Pandas is excluded from the bundle, so it is built on numpy.
      *A small column table, not Phase 4's:* `T.col`, `T(rows, vars)`,
      `Properties.VariableNames`, `height`/`width`, `table(x, y)` named after
      its arguments, `array2table`/`table2array`. No `T{…}`, assignment into
      a table, `sortrows` or `join` yet.
- [x] `fopen`, `fclose`, `fgetl`, `fgets`, `fprintf(fid, …)` to a file, `fscanf`,
      `textscan`, `fread`, `fwrite`.
      *Also `feof`, `frewind`, `ftell`, `fseek`. `cd` lasts one run, as before.*
- [x] `jsondecode` and `jsonencode`.
- [x] `xlsread`/`readtable` on `.xlsx`. This needs openpyxl, a new dependency, so
      decide first. **M** *Done 2026-11-03, openpyxl added:* `readmatrix`,
      `readtable`, `writematrix`, `writetable` with `'Sheet'` and `'Range'`;
      `xlsread`, `xlswrite`, `sheetnames`. A sheet is read into the same text
      grid a CSV is split into, so header detection is shared. `.xls` and
      `.ods` are refused by name.

**Statistics and linear algebra** **S**
- [x] `var`, `mode`, `cov`, `corrcoef`, `prctile`, `quantile`, `skewness`,
      `kurtosis`, `movmean`, `movmedian`, `smoothdata`, `detrend`.
- [x] `normpdf`, `normcdf`, `norminv`, `ttest`, `regress`. `fitlm` with its summary
      table is **M**. *`fitlm` done with Phase 4's `table`.*
- [x] `svd`, `qr`, `lu`, `chol`, `pinv`, `null`, `orth`, `expm`, `logm`, `sqrtm`,
      `cross`, `dot`, `cond`, `trace`, `triu`, `tril`, `circshift`, `sub2ind`,
      `ind2sub`. *`trace` existed already.* `rng` seeds the generator `rand`
      and `randn` use; the streams are not MATLAB's.
- [x] `randi`, `randperm`, `rng`.

**Strings** **M**
- [x] `strsplit`, `strjoin`, `strtrim`, `strrep`, `regexp`, `regexprep`, `contains`,
      `startsWith`, `endsWith`, `split`, `join`, `upper`, `lower`, `pad`.
      *Also `regexpi`, `strfind`, `strncmp(i)`, `blanks`, `deblank`, `isspace`,
      `isletter`, `isstrprop`. `split` returns a column cell, as Evans has no
      string arrays.*
- [x] `sprintf` and `num2str` over cell arrays. Decide how far `"…"` string arrays go
      beyond `char` (Phase 4). *As in MATLAB, `sprintf('%s,', c{:})` works and
      `sprintf('%s', c)` and `num2str(c)` refuse the cell. `"…"` stays char
      until Phase 4.*

**Cells and structs** **S**
- [x] `cellfun` and `arrayfun` (with `'UniformOutput', false`), `cell2mat`,
      `struct2cell`, `cell2struct`, `rmfield`, `orderfields`, `isequal`,
      `ismember` on cells of text. *Also `isequaln`, `iscellstr`, `getfield`,
      `setfield`, `deal`, and `isfield` with a cell of names. `'ErrorHandler'`
      is refused. An anonymous function still returns one output, so
      `[a, b] = cellfun(@(x) max(x), c)` needs a function file.*

**Signal processing for measured data** **M**
- [x] `filtfilt`, `fir1`, `fir2`, `designfilt` (the common forms), `pwelch`,
      `periodogram`, `spectrogram`, `resample`, `decimate`, `interp`, `xcorr`,
      `impz`, `grpdelay`. *`designfilt` covers the Butterworth IIR and window
      FIR forms and works with `filtfilt(d, x)`, `filter(d, x)`, `freqz(d)`,
      `impz(d)` and `grpdelay(d)`.*
- [x] Windows: `hann`, `hamming`, `blackman`, `kaiser`, `window`.
      *Also `hanning`, `rectwin`, `triang`, `bartlett`.*
- [x] Start from the `_iir`/`freqz` code in `matlab_runtime.py`.

**Fitting, optimisation, integration** **S–M**
- [x] `lsqcurvefit`, `lsqnonlin` (on `scipy.optimize.least_squares`), `fsolve`,
      `fminunc`, `fmincon` (on `minimize`), `linprog`, `intlinprog` (`milp`),
      `quadprog`. *Also `optimoptions`. `fmincon` uses SQP, not MATLAB's
      interior-point: the same local minimum on well-posed problems.*
- [x] `integral`, `integral2`, `quadgk`, `polyder`, `polyint`, `spline` and `pchip`
      as functions, `interp2`, `griddata`. *Also `ppval`.*
- [x] `fit` with the common `fittype` names (poly1…poly9, exp1, exp2, power1, sin1).
      A `cftool` GUI is **L** and waits. *Also `coeffvalues`, `coeffnames`,
      `confint`; custom equations are refused.*

**Workspace and system helpers** **S**
- [x] `who`, `whos`, `which`, `exist` with a type, `dir`, `ls`, `delete`, `copyfile`,
      `movefile`, `mkdir`, `system`, `getenv`. *Also `rmdir`, `setenv`,
      `computer`, `ispc`/`isunix`/`ismac`. `who` inside a function lists the
      workspace, not the function's variables.*
- [x] `clock`, `now`, `datestr`, `datetime` (Phase 4), `pause` that honours Stop.
      *Also `datenum`, `datevec`, `date`. `datetime` came with Phase 4
      (`console/lib_dates.py`).*
- [x] `dec2bin`, `bin2dec`, `dec2hex`, `factorial`, `nchoosek`, `primes`, `isprime`,
      `gcd`, `lcm`, `erf`, `gamma`, `beta`. *Also `hex2dec`, `dec2base`,
      `base2dec`, `erfc`, `erfinv`, `erfcinv`, `gammaln`, `betaln`, `nthroot`.*

- [x] Several outputs from an anonymous function, so `[a, b] = cellfun(@(x) max(x), c)`
      works without a function file. **S–M** *Done with Phase 0's `varargout` work
      (2026-11-11: anonymous functions pass nargout on); found working in the
      2026-11-19 documentation audit.*

### Phase 2: Simulink for daily use (core done 2026-10-30)

The engine was ahead of the editor and of its links to the console. Tests:
`tests/golden/test_sim_workspace.py`, `test_sim_library.py` and
`test_sim_editing.py`.

- [x] **Block parameters take workspace expressions.** `Kp`, `2*pi*f` and `[1 2 3]`
      instead of a `QDoubleSpinBox` (`ui/sim/params.py`), evaluated in the console
      workspace at compile time, with a clear error naming the block and the
      parameter. This opens model variables and parameter sweeps. **M**
      *`sim/workspace.py`. The block keeps the text (saved as written) and runs
      on a stand-in until compile; a constant expression is evaluated at once
      so the canvas has its value. The Model tab evaluates on the GUI thread
      and hands the solver a compiled copy. Integer parameters (port counts,
      indices) stay numbers.*
- [x] **To Workspace output reaches the console.** `SimResult.workspace` is filled
      but dropped in `ui/sim/sim_tab.py` `_on_finished`. Add a From Workspace block
      too. **S** *A run on the Model tab leaves `out` in the workspace, as
      Simulink's single-output default does. To Workspace has Simulink's three
      save formats (Timeseries by default; `plot` draws one). From Workspace
      reads `[t, u]`, a struct with `time`/`signals.values`, or a timeseries.*
- [x] **`sim`, `open_system`, `load_system`, `set_param`, `get_param` in MATLAB
      syntax,** returning a `SimulationOutput`-like struct (`out.tout`, `out.yout`,
      logged signals). **M** *`console/lib_sim.py`, with `new_system`,
      `save_system`, `close_system`, `add_block`, `delete_block`, `add_line`,
      `delete_line`, `find_system` and `gcs` too. A top-level Outport is now
      allowed and is a column of `yout`. The run settings moved from the
      toolbar into the model (`StopTime`, `Solver`, `MaxStep`, `RelTol`,
      `AbsTol`, saved in the `.fmdl`); a model takes its file's name. `sim`
      given a model object still returns the Python result.*
- [x] **A Fcn / MATLAB Function block** whose body is a MATLAB expression or a
      function, run through the same translator. Watch the per-step cost. **M**
      *`sim/blocks/user.py`: translated once, about half a second for a 10 s
      run with both blocks. Workspace variables are read at compile time.
      `persistent` gives no memory (it updates at every solver stage).*
- [x] **Logic blocks:** Relational Operator, Logical Operator, Compare To Constant,
      Compare To Zero, Bitwise Operator. **S** *The comparisons latch and
      declare zero crossings, so a switch lands on the instant.*
- [x] **Missing common blocks:** Memory, Discrete-Time Integrator, Discrete FIR/Filter,
      Repeating Sequence, Signal Builder, Counter, Data Store Read/Write, XY Graph,
      2-D Lookup Table, Prelookup. **M** *Memory needs its sample time stated
      (Simulink's inherits). Signal Builder takes typed points, not a graph
      editor. Counter is Counter Limited. Prelookup comes with an
      Interpolation (Prelookup) block. Data stores are wired through at
      compile time, one writer per store, so a read feeding its own write is
      reported as an algebraic loop.*
- [x] **Conditionally executed subsystems:** enabled, triggered, If/Switch Case
      action, and an Integrator reset port. **M–L** *`sim/blocks/conditional.py`.
      Flattening adds a hidden gate on the control input and a hold on each
      output; the solver freezes a closed gate's members and lets gates and
      the Integrator's reset act at events, sample hits and fixed steps
      (`fire`). States held or reset on enabling; outputs held or reset while
      disabled. A triggered subsystem refuses continuous states, as Simulink
      does. One control port per subsystem (no enabled-and-triggered).*
- [x] **Goto/From.** Buses were cut on purpose; reconsider them after Goto/From. **M**
      *Local and global tags, dissolved into wires at compile time. Buses are
      still not reconsidered.*
- [x] **Diagram editing:** rotate and flip, text annotations, signal labels on wires,
      Create Subsystem from Selection, draggable wire bends. **M** *From the
      canvas's context menu; each is one undo step. Routes follow the port
      directions, so a flipped feedback block wires cleanly. Grouping is
      `sim/edit.py`, one Inport per entering signal.*
- [x] **Export:** the diagram to SVG/PNG/PDF and to the printer, and scope data to CSV
      and `.mat`. **S** *Export menu and the canvas's context menu; the
      scope's Export… button.*
- [x] **Compare runs:** overlay the last N runs in a scope (deferred in the v2 plan's Part 6).
      **M** *The last five are kept; "Compare with earlier runs" draws up to
      five, dashed and fading. The ticked channels survive a rerun. An XY
      Graph block gets its own view in the scope.*
- [x] **Sample models:** a few `.fmdl` files from the courses (DC motor, cruise control,
      inverted pendulum, PID loop with saturation), reachable from File ▸ Examples.
      There are none in the repo now. **S** *`src/evans/examples/`, rebuilt by
      `tools/build_examples.py`. The PID example builds its anti-windup loop
      from blocks: see the PID limit below.*
- [x] **Ungroup / Expand Subsystem**, the inverse of Create Subsystem. **S**
      *Done: `sim/edit.ungroup_subsystem`, right-click > Expand subsystem, one
      undo step. Inner blocks keep their place and names (suffixed on a clash);
      nested subsystems stay intact. Conditional subsystems are refused with a
      message, since the Enable/Trigger/Action condition has no home in the
      parent.*
- [x] **Snap blocks by port alignment.** Dragging a block snaps to other blocks' edges
      and centres today (`guides_changed` in `ui/sim/items.py`, drawn by the canvas's
      guides). Add snapping of a port to the port it will be wired to: while
      dragging, line up a block's output or input with the matching input or
      output of a neighbour (and of a connected block first) so the wire between
      them is one straight run, and show a guide through the two ports. Handle
      rotated and flipped blocks and several ports on one block, prefer ports
      that are already wired, and let a modifier key turn it off. **S–M**
      *Done:* `port_snap` in `ui/sim/items.py` is a pure function over
      `PortCandidate`s (wired pair, then ports of connected blocks, then any
      opposite port); it overrides edge/centre snapping per axis and draws a guide
      through the two ports. Rotated blocks align in x, Alt turns it off.
- [x] **Better block shapes.** Every block is a rectangle today (`BlockItem` in
      `ui/sim/items.py`). Some should look like what they are, as in Simulink's
      library: a triangle for Gain, a circle or rounded Sum with its signs at the
      ports, a round Product, a rounded Integrator box with 1/s, a Saturation and
      a Switch drawn with their characteristic, a Step, Ramp and Sine showing the
      waveform, a narrow bar for Mux/Demux, a flag shape for Goto/From and port
      blocks, and a distinct outline for Subsystem. The ports must stay where the
      router expects them and the hit area must follow the shape. Rotate and flip
      must work, and the shapes must read in both themes and in exports. Keep the
      rectangle as a fallback and add a "classic boxes" setting. **M** *Done:
      `ui/sim/shapes.py`, one `Shape` per type chosen by `shape_for`, the box as
      fallback; ports, sizes and routing unchanged. View ▸ Classic block boxes
      (persisted). Turned shaped blocks write their id beside the wire. A linked
      subsystem can later be `SubsystemShape(dashed=True)` or another band.*
- [x] **Scope overhaul, the finished parts** (`ui/sim/scope.py`; the rest is open in
      the roadmap):
      - **Copy straight from the plot:** Ctrl+C or a right-click menu entry copies
        the plot as an image (and the visible data as tab-separated text) to the
        clipboard, to paste into a report or a spreadsheet. **S**
        *Done: Ctrl+C and a right-click "Copy plot and data" entry copy the
        image and the visible range as tab-separated text.*
      - **Better exports:** PNG at a chosen size and DPI, SVG, and PDF/EPS through
        the matplotlib path the console figures already use, with the theme either
        as on screen or on a white page for papers; the same for XY graphs. **S–M**
        *Done: Export… adds PNG (size in inches and DPI), SVG, PDF and EPS via
        `figure_mpl`, as on screen or on white; time and XY views.*
      - **Undock:** pop a scope out into its own window (and several at once, one
        per Scope block), keep it live over the next run, and dock it back. **M**
        *Shaped 2026-11-11 (Leon's idea), and the next scope item to build:*
        - **Double-click a Scope block → its own window**, as in Simulink,
          showing only the signals wired into that block. It stays open,
          redraws on the next run, and several can be open side by side.
        - **The bottom scope becomes the "global scope"** (every logged
          signal), collapsed by default behind a **Show global scope**
          button, with its long list of signal checkboxes inside it. Whether
          it was open is remembered.
        - **Double-click on a Scope block opens the plot, not the parameters.**
          Its settings stay reachable from the inspector that shows when the
          block is selected. Other blocks keep double-click for parameters.
        - Copy (Ctrl+C), Export…, and "Compare with earlier runs" work in the
          pop-out windows too: they share the same plot widget.
        *Done: double-click a Scope block for its window (only its wired
        signals, one per block, redrawn after each run, closed with the
        model); the bottom scope is the global scope behind Show global
        scope, remembered. Docking a window back is not built: the global
        scope covers it.*
      Docking a scope into the side panel and back came later, with Phase 8's R6.
- [x] **Script pre-run for a model.** Link one or more `.m` files to an `.evx`, run
      in order when the model opens and/or before each run, so a model's
      parameters (`Kp`, `Ts`, plant matrices) are set up by the script that
      defines them, as a Simulink model's PreLoadFcn/InitFcn do. Wanted:
      - A "Model scripts" dialog on the Model tab: an ordered list of `.m` files
        (relative to the `.evx` where possible), each ticked for *on open*,
        *before every run*, or both, with move up/down and a Run now button. **M**
      - The paths and flags saved in the `.evx`; a missing file is a warning that
        names it, not a failed open. Older files without the field open with no
        scripts. **S**
      - Scripts run in the console workspace, so block parameters that name
        workspace variables see them at compile time (`sim/workspace.py`); output
        and errors go to the console with the script's name and line, and an error
        in a pre-run script stops the run and says which one. **S–M**
      - A guard against surprises: ask before running scripts from a model that was
        just opened from a file the user did not create (like MATLAB's callback
        warning), with a "trust this model" choice remembered per path. **S**
      - MATLAB-side parity: the `set_param(model, 'PreLoadFcn', …)` and
        `'InitFcn'` forms in `console/lib_sim.py`. Loading a `.slx`'s callbacks
        belongs to `.slx` import (Phase 7). **S**

      *Done 2026-11-12:* `sim/scripts.py` (Qt-free: entries, paths, run order,
      the trust rule, the callback mapping); a `scripts` field in the `.evx`,
      written only when there are any, so the format version stays 1; *Scripts…*
      on the Model tab (`ui/sim/scripts_dialog.py`). Decisions: a script that is
      missing *before a run* stops the run (on open it is a warning), since the
      run would only fail later on the variable it defines; new rows are ticked
      for both; *Run now* runs the selected rows with no trust prompt, since the
      user asked for them by name. Trusted means a model built in Evans, an
      example, a file saved from a trusted model, or one the user chose to trust;
      Save does not make a stranger's model trusted. `InitFcn`/`PreLoadFcn` take
      script names only (`'setup; gains'`), not code, and the help pages say so.
      `load_system` runs the on-open scripts and `sim` the before-run ones, with
      the same trust check when the app is there. Fixture:
      `tests/fixtures/models/model_scripts.evx`.

Found while doing this phase:

- [x] A **PID block with "Limit output" on stalls the solver** once its output reaches
      the limit (already so on `main`): the conditional integration in its
      derivative is not latched, so the step size collapses. Give the PID modes,
      as Saturation has. **S–M** *Done 2026-11-03:* latched `[clip, run]`
      modes and a third zero crossing on the error. Riding the limit is a
      true sliding mode, so it still ends in the chatter fallback (with its
      warning, as Simulink warns of consecutive zero crossings), now about
      1 s instead of 40. The output is hard-clipped, since a latched mode
      lags a step in that fallback.
- [x] A **Unit Delay fed by a continuous signal acts as a zero-order hold**: it
      outputs u(k) over [k, k+1), not u(k−1). Fed by another discrete block it
      delays correctly, because it reads that block's value before the update.
      Simulink gives u(k−1) either way. Decide the update order before changing
      it; the triggered subsystem's held outputs follow the same convention. **S–M**
      *Done 2026-11-03, Simulink's order:* blocks due at one hit update
      upstream first, the model re-evaluated between rounds, so each sees its
      feeders' new outputs (this also removed an extra sample of delay after a
      ZOH). Unit Delay holds two states, like Memory. Blocks whose held output
      does not read their input (`Block.held_reads_input`: Unit Delay, Memory,
      Counter, forward Euler, strictly proper filters) act first, which
      resolves discrete loops; a loop without one runs with a warning. The
      conditional subsystems' holds act at events, not at sample hits, so
      they were not affected.
- [x] A fixed-step run does not log its final instant (`_fixed_step` records
      only the edges before `t1`). **S** *Done 2026-11-03.*

### Phase 3: Plotting (core done 2026-11-03)

Plotting stopped at 2-D lines and bars, and figures are a large share of what people use
MATLAB for. The plot functions moved to `console/lib_plot.py`, a mixin like the other
`lib_*` groups. 2-D axes are still drawn by pyqtgraph (`ui/console/figure_view.py`);
3-D axes and pies are drawn by a new matplotlib renderer, `console/figure_mpl.py`,
embedded in the figure, which also writes PDF/EPS and the live report's figures, so
every spec saves however it was made. Tests: `tests/golden/test_lib_plot.py`
(headless) and `test_plot_ui.py`; the self-test checks the 3-D, contour and PDF/EPS
paths the frozen build would otherwise only reach on first use.

- [x] `scatter`, `errorbar`, `area`, `fill`, `patch`, `pie`, `text`, `xline`, `yline`,
      `yyaxis`, `tiledlayout`/`nexttile`, `annotation`, `colororder`. **M**
      *Also `bar(..., 'stacked')`, a real `barh`, `subtitle`, `cla`, `lines`, and axes
      handles: `ax = nexttile`, `gca` or `subplot` passed first to `plot`, `title` and
      the rest. Line specs in any order (`'o-r'`), their colours and `'Color'`,
      `'LineWidth'`, `'Marker…'` and `'DisplayName'` are now honoured; before, the
      colour letter was ignored for the theme's cycle, which stays the default.
      `legend` honours the four corners of `'Location'`.*
- [x] 3-D: `plot3`, `surf`, `mesh`, `contour`, `contourf`, `quiver`, `meshgrid` (check
      it exists), `view`, `zlabel`, rotate with the mouse. **L**
      *Also `scatter3`, `quiver3`, `fill3`, `surfc`/`meshc`, `zlim`, `shading`,
      `peaks`, `axis` modes (`equal`, `tight`, `ij`, `off`, six limits) and
      `lims = axis`/`xlim`. No OpenGL in the bundle, so 3-D is matplotlib's mplot3d:
      drag to turn, right-drag to zoom; `[az, el] = view` does not read the
      mouse's angle back. Contours are traced by contourpy (matplotlib's) and drawn
      by pyqtgraph, so they overlay plots and read out on hover. `C = contour(...)`
      returns MATLAB's contour matrix. `meshgrid(x, y, z)` is done (Phase 4).*
- [x] Images: `imagesc`, `image`, `imshow`, `colormap`, `colorbar`, `caxis`. **M**
      *Also `clim` and the colour-map functions (`jet(n)`, `gray(n)`, …). `parula`
      is MathWorks' own, so it is viridis. True-colour (m×n×3, 0–1) images work now;
      `imread` is still to do (listed below); `imshow` of doubles is black at 0 and
      white at 1, as in MATLAB, and `imshow` of `uint8` spans 0–255 (Phase 4).*
- [x] A data cursor and a hover readout in `ui/console/figure_view.py`. **M**
      *Every 2-D curve, marker, bar, contour and reference line reads out on hover
      (the analysis tabs' `HoverReadout`); an image reads out its pixel. A click
      pins a data tip, a click on the tip removes it, and the plot menu has
      Remove data tips. 3-D axes show matplotlib's coordinate line; data tips on
      them came 2026-11-09 (below).*
- [x] Export figures to PDF and EPS alongside PNG/SVG, and `exportgraphics`. **S**
      *PDF and EPS are drawn by matplotlib on a white page, for papers; PNG, JPEG,
      TIFF and SVG are the figure as on screen, a picture at `'Resolution'` or
      `print -r300`. EPS drops transparency, as PostScript must.*
- [x] Let annotations typed at a later prompt reach the current figure (`title`,
      `legend` on a separate line), as MATLAB allows. Today they must be on the
      plot's line. **M** *The prompt keeps its figures (and `hold`) from line to
      line; reading the current axes marks its figure touched, and at the end of
      the line touched figures are redrawn in place in their tab. A figure closed
      in the window is forgotten, so nothing brings it back. A script run still
      starts with none.*
- [x] `figure(n)` going back to figure `n`, and `gcf` following the selected tab. **S–M**
      *Done 2026-11-09:* figures carry a number (`FigureSpec.number`); `figure(n)`
      selects it or opens it with that number, and the next plot replaces its
      contents. `gcf` follows the selected tab, `close(n)`/`close` and `clf`
      keep numbers and tabs consistent. Help pages for `gcf`, `close`, `clf`.
- [x] Data tips on 3-D axes, and the live colour map of a mesh after a theme switch
      without a redraw. **S each** *Done 2026-11-09:* `figure_mpl.DataTips3D`: a click
      (not a drag) pins a tip on the nearest vertex, a click on a tip takes it off;
      tips are artists in the axes, so they turn with the view.
      `figure_mpl.retheme` recolours a drawn canvas in place on a theme switch, so
      the camera, the tips and the colour map survive it.
- [x] `histogram` and `stem` pages, and the rest of the plotting commands that still have
      none (`stairs`, `semilogy`, `loglog`, `saveas`, `print`, `sgtitle`, `close`,
      `clf`, `gcf`). **S** *Done 2026-11-09:* eleven pages, listed under Plotting
      and Plot types.

### Phase 4: Running other people's MATLAB code (2026-11-09 to 2026-11-11)

This is what decides whether a colleague's `.m` file runs. *Started 2026-11-09 (0.16.0):*
the cheap items are done; the large types are not.

- [x] An error for an unknown name that says when the function is a MATLAB one Evans
      does not have yet, so the user knows they haven't mistyped it, with a link to
      a "not in Evans" list. **S** *`console/matlab_names.py` holds the list and the
      "Not in Evans" help page is built from it; a test fails if a listed name is
      later implemented, or the page goes stale.*
- [x] Everyday basics found missing while writing the help pages: `magic`,
      `fileread`. **S**
- [x] `eval`, `evalin`, `feval`, `str2func`, `func2str`, `exist`, `inputParser`,
      `validateattributes`, `nargin(fn)`. **M** *Done 2026-11-09, `console/lib_lang.py`,
      and `inputParser` (done 2026-11-09 in `matlab_runtime.InputParser`:
      `addRequired`/`addOptional`/`addParameter`/`addSwitch`/`parse`, `Results`,
      `Unmatched`, `UsingDefaults`, validators, name matching as MATLAB's). `eval` runs in the base workspace; inside a function it
      reads variables and refuses to set them. `evalin` takes `'base'` only. `nargin(fn)`
      is not reachable inside a function, where `nargin` is the call's own count.
      The operators exist as functions (`plus`, `minus`, …) so `@plus` works.*
- [x] **`c{:}` / `varargin{:}` in a call's argument list.** Found 2026-11-09 from a
      lab (`ore.m`, which forwards `varargin{:}` to a recursion function). The cell is
      not expanded into separate arguments: `f3(c{:})`, `fwd(1,2,3)` with
      `f3(varargin{:})`, `fh(1,2,varargin{:})` and `@(varargin) f3(varargin{:})` all
      fail with a raw Python `TypeError`, while `sprintf('%s,', c{:})` on a builtin
      works. Fix at the call site so a cs-list expands to zero or more arguments,
      mixed with fixed ones; also check `[c{:}]`, `{c{:}}` and
      `[varargout{1:nargout}] = f(...)`. `varargin` itself is already a list of the
      surplus arguments (`matlab.py` ~1357). The repros
      are tests in `tests/golden/test_lib_lang.py`. **M** *Done 2026-11-09: the
      translator splices `c{:}` into argument lists and matrix rows
      (`cell_list` in the runtime), and `@(a, varargin)` lambdas take any number
      of arguments. `[varargout{1:nargout}] = f(...)` works since 2026-11-11.*
- [x] **MATLAB-style errors for user functions.** Too many arguments should say
      `Too many input arguments.`, and a missing parameter that is used should say
      `Not enough input arguments.` or name the variable, not `NoneType` arithmetic.
      Anonymous functions and handles must say the same, not `<lambda>() takes 1
      positional argument`. Keep whatever supports `nargin` and `exist('x','var')`.
      **S–M** *Done 2026-11-09: a function takes `*_extra` and raises `Too many input
      arguments.`; a missing parameter is still `None` inside (so `nargin` and
      `exist` work) and a failure that touches it is reported as `Unrecognized
      function or variable 'b'.` (`friendly()` in the runtime, also what `catch e`
      sees, with MATLAB identifiers). Handles say `Too many/Not enough input
      arguments.`*
- [x] **Errors name the function and line,** in MATLAB's form (`Error using f (line 2)`
      then `Error in ore (line 10)` with the source line), instead of `Error in
      line 11`. This misled the lab user twice. Keep the Python traceback behind a
      debug flag. **M** *Done 2026-11-09: `Error using f (line 2)`, the message,
      then `Error in g (line 5)` and the source line for each caller, down to the
      script (`Error in line 10`). Function files are compiled per chunk under
      `<name.m:line>` and registered in `Runtime.frames`. `Interpreter.debug_errors`
      or `EVANS_DEBUG=1` appends the Python traceback. A failure outside any
      function keeps the short `Error in line N:` form.*
- [x] A script file named with dots (`C.3.2.m`) cannot be called by name in MATLAB;
      say what Evans does and give a clear message. **S** *Done 2026-11-09: typing
      `C.3.2` or `C.3.2.m` says the name is not valid and suggests `C_3_2.m` or Run
      from the editor. Evans has no `run('C.3.2.m')` yet.*
- [x] Nested functions that share the parent's variables. **M** *Done 2026-11-09:
      a function met before its parent's `end` is nested when it has an `end` of its
      own; it becomes a closure defined at the top of the parent, and the variables
      both use are `nonlocal`. Files where every function runs to the next
      `function` are unchanged.*
- [x] Integer and single types: `int8`…`uint64`, `single`, `logical()`, `double()`,
      with saturation. Images and hardware data depend on them. **M** *Done
      2026-11-09 (`console/numtypes.py`, `lib_types.py`). Values are numpy
      integer and float32 scalars and arrays; arithmetic runs in double and is
      cast back, rounding half away from zero and saturating, so `int64` and
      `uint64` beyond 2^53 are not exact. An integer meets a double (or single)
      and stays an integer; two integer classes are an error. Also `cast`,
      `intmax`/`intmin`/`flintmax`/`realmax`/`realmin`, `isinteger`/`isfloat`,
      `idivide`, `bitand`/`bitor`/`bitxor`/`bitshift`/`bitcmp`, `zeros(…,'int8')`
      and `'like'`, and `imshow` of `uint8` spans 0–255. Library functions
      keep an integer input's class only when MATLAB's do (`max`, `abs`,
      `sort`, `reshape` …; not `sum` and `prod`, which give a double, see the
      reference corpus); the rest hand back doubles. Display is
      the classic form (`x = 5`, no `int8` banner). Not done: `typecast`,
      integer-valued `containers.Map` keys (still stored as doubles), N-D.*
- [x] `containers.Map`. **S–M** *Done 2026-11-09. A handle; text or double keys
      (other key types are stored as doubles until integer types exist);
      `copy` and `Map` arrays are not done. The translator turns
      `containers.Map(...)` into a runtime call that yields to a user variable
      called `containers`.*
- [x] A real `table`: constructor, `T.col`, row filtering, `height`, `width`,
      `sortrows`, `join`; then `datetime`, `duration`, `timetable`. **L**
      *Done 2026-11-09.* `table` with `'VariableNames'`, `'RowNames'`,
      `'Size'`; `T{rows, cols}`; assignment (`T.col = …`, `T.x(i) = …`,
      `T(i, :) = {…}`, growing past the end, `T{…} = …`, `T.Properties.*`);
      `T(rows, :) = []`; `addvars`, `removevars`, `renamevars`, `movevars`;
      masks; `head`, `tail`, `summary`, `sortrows` (matrices, cell text and
      tables), `unique`, `[T1; T2]`, `[T1, T2]`, `join`, `innerjoin`,
      `outerjoin`, `groupsummary`, `varfun`, `rowfun`, `findgroups`,
      `splitapply`, `table2cell`, `cell2table`, `table2struct`. `datetime`
      (parts, text, formats, `ConvertFrom`), `duration` and the unit
      functions, `calmonths` and friends, `between`, `dateshift`, `weekday`,
      `timetable` indexed by number, mask, exact time or `timerange`, and
      `fitlm` with its coefficient table and summary (linear terms only) with
      `predict`. *Left out:* time zones, categorical, `stack`/`unstack`,
      `retime`/`synchronize`, matrix-valued variables, `fitlm` interactions,
      a datetime's two-line display, `plot` of a datetime axis.
- [x] String arrays as their own type (`numel("abc") == 1`, `["a" "b"]`), distinct
      from `char`. **M** *Done 2026-11-09. `"abc"` is a `Str` (a `str`
      subclass, so every text function takes it); `["a" "bc"]` is a `StrArray`
      (a cell subclass of `Str`). `+` joins, `==`/`<` compare, `string`,
      `strlength`, `isstring`; `upper`, `strrep`, `strsplit`, `join` … give
      strings back for strings. Not done: assigning into a string array keeps
      cell rules, `missing`, `<missing>` and `strings(n)`, string `.^`/`*`
      errors only name the operator.*
- [x] N-D arrays (`zeros(2,2,2)`, `cat(3,…)`, `permute`, `squeeze`). The 2-D
      assumption runs through the runtime, so this is a large change. **L**
      *Numeric and logical arrays and cells of any rank: `zeros`/`ones`/`rand`/
      `randn`/`cell`, `size`/`ndims`/`numel`, indexing and assignment with any
      number of subscripts (growing, deleting a page) and column-major linear
      indexing, `cat`, `permute`, `squeeze`, `reshape` (with `[]`), `repmat`,
      `meshgrid(x,y,z)`, `ndgrid`, reductions, `max`/`min`, `cumsum`, `sort`,
      `any`/`all` along a dimension, broadcasting, and display as `ans(:,:,k)`
      pages. `A'` and `A*B` refuse N-D arrays, as MATLAB does; most
      other functions see the `A(:,:)` view.*
- [x] `classdef` (properties, methods, constructors, handle classes). **L** *Done
      2026-11-09, `console/classes.py` and the parser in `matlab.py`. Value and
      handle classes, attributes (`Access`, `Constant`, `Dependent`, `Static`),
      `get.`/`set.` methods, inheritance with `obj@Super(...)` and
      `method@Super(obj)`, operator overloading, `disp`/`display`, events and
      enumerations. Not done: arrays of objects, `subsref`/`subsasgn`,
      property validation, `dynamicprops`, `@Class` and `+pkg` folders.*
- [x] `sparse`, `speye`, `nnz` and the iterative solvers, on `scipy.sparse`. **M**
      *Done 2026-11-09:* `sparse` (all five forms), `speye`, `spalloc`, `spones`,
      `sprand`, `full`, `issparse`, `nnz`, `nonzeros`, `nzmax`, `spfun`, `spdiags`
      (build, extract, replace); `pcg`, `gmres`, `bicgstab`, `bicg`, `minres`
      (flag, relres, iter, resvec, `M1`/`M2`, `x0`); `eigs` (symmetric and
      general, `'smallestabs'` and a shift) and `svds`. A sparse matrix is a
      `Sparse` value (`lib_sparse.py`): `+ - .* * \ / ^ '`, comparisons,
      indexing, `A(i,j) = v`, `A(:,k) = []` and `[A B; C D]` keep it sparse where
      MATLAB does; `size`, `abs`, `sum`, `find`, `diag`, `norm`, `kron` work on
      the sparse form and any other function is handed `full(A)`. A single
      element `A(i,j)` is a plain number, and writing elements one by one is
      slow (build with `sparse(i,j,v)`). Not done: function handles as `A` in
      the solvers or `eigs`, `lsqr`, `ilu`, `ichol`; they stay on the not-in-Evans
      list.
- [x] `.mat` v7.3 (HDF5) through h5py, a new dependency. **M**
      *Done 2026-11-09, h5py added* (`matfile73.py`): `save ... -v7.3` (and
      `-append` onto a 7.3 file) and `load` of both numbers, text, logicals,
      complex, empty, cells (through `#refs#`), structs, struct arrays and sparse
      matrices. Tables, function handles and classes in a MATLAB-written file are
      skipped with a warning. The writer follows MATLAB's layout from its
      documentation; it has not been opened in MATLAB itself.
- [x] Save live scripts back to `.mlx`, not only to plain live `.m`. **M**
      *Found already done:* the editor's Save keeps an `.mlx` an `.mlx`, Save as
      offers both, and it warns before dropping captions and templates (`.mlx`
      has no place for them). Added a test that the three SiPro labs, saved by
      MATLAB R2023a, read back the same after Evans writes them again. The writer
      has still not been opened in MATLAB.
- [x] `uigetfile`, `uiputfile`, `inputdlg`, `msgbox`, `questdlg`, `waitbar`, `ginput`,
      and `input` at the console prompt. **M**
      *Done 2026-11-09:* also `uigetdir`, `listdlg`, `errordlg`, `warndlg`,
      `helpdlg` and `keyboard`. The commands ask a *dialog host*
      (`console/dialogs.py`), like the figure and app sinks: the window installs
      Qt dialogs, and anything else (a test, a headless run) gets a scripted host
      that records the question and answers Cancel. `input` and `keyboard` read a
      line from the console's own prompt; `ginput` waits for clicks on the figure
      on top. `waitbar(h)` is closed by `close(h)` or `delete(h)`. `input`
      evaluates in the base workspace; `msgbox` waits until closed, unlike
      MATLAB's.

### Phase 6: Platform and trust (the finished items)

Professional users need this before Evans can be used for paid work.

- [x] **Autosave and crash recovery.** Nothing is saved on its own today. Write a
      recovery copy of every unsaved document (editor scripts, live scripts, Model
      tab diagrams, console history, the workspace) to a folder under the user's
      app data every minute or so and after each edit pause, never over the real
      file. On the next start after a crash, offer to restore them. Add a setting
      for the interval and for turning it off, delete the copy on a normal save or
      close, and keep the last few versions of a model. Test with a simulated kill
      mid-edit. **M** *Done 2026-11-10, `ui/recovery.py`:* each running Evans
      has a folder under app data (`recovery/session-<pid>-<start>`) with a
      heartbeat; on a timer it writes the unsaved script tabs, the live script
      and the diagram (when they differ from their files), each through a
      temporary file and a rename, and keeps three earlier copies of the model.
      A clean quit deletes the folder. At the next start a folder whose Evans is
      gone (or whose heartbeat stopped) is offered back: Restore / Discard / Ask
      next time; restored documents come back unsaved and nothing touches the
      real files until the user saves. File ▸ Autosave for crash recovery turns
      it off and sets 30 s – 5 min (1 min by default). Tested with a real
      process killed mid-session (`tests/golden/test_recovery.py`). *Left out:*
      the workspace (a `save` of it can be large and not every value can be
      written), copies on an edit pause (only the timer), and restoring the
      earlier model copies from the dialog (they stay in the folder only until
      the user answers). The console history was already saved after every
      command.
- [x] **Ask before quitting with an unsaved model or live script.** Found while
      doing autosave: only the script editor's tabs are settled on quit
      (`confirm_close_all`). The Model tab and the Live editor have no unsaved
      mark and no prompt, so a quit drops their changes silently, and the Model
      tab's Save always asks for a file (it does not remember the one it came
      from). The baselines autosave now keeps (`SimTab.mark_saved`,
      `LiveScriptEditor.mark_saved`) are the "is it unsaved?" test this needs.
      **S–M**
      Done: the Live tab's file name and a new file label at the Model tab's
      bottom right carry the `●` mark, kept current from the cells' edits
      and the canvas's `model_changed` (no polling). Quit settles script
      tabs, then the live script, then the model (Save / Discard / Cancel,
      shared helper `ui/unsaved.py`); a Save whose file dialog is cancelled
      counts as Cancel. Open, Open Recent, File ▸ Examples and double-clicking
      a workspace model ask before replacing unsaved content. Running cells
      or a simulation never counts as a change: the comparison is the live
      .m text (no outputs) and the model's JSON (a run uses a compiled
      copy). Left as it was: a console Simulink command that puts another
      model on the canvas does not ask (a script should not stop on a
      dialog), and a model shown from the workspace counts as unsaved.
- [x] **Rename the model file extension `.fmdl`** (FauxMatlab model, a leftover of the
      old name). The new extension is `.evx`, chosen
      2026-11-09 after a search found no common program using it (`.evm` was the
      runner-up). Save new files with it,
      keep reading `.fmdl` for good, offer "Save as new format" on an old file and
      never rename on open, register the new type in the Windows installer and the
      macOS bundle (file association and icon), update File > Open/Save filters,
      the examples under `src/evans/examples/`, `tools/build_examples.py`, the help
      pages, the site and the tests. The `"format"` tag inside the file stays
      readable as it is (CLAUDE.md lists it as a naming exception) and gets a
      version field instead. **S–M**
      *The flow, decided 2026-11-09:* opening a `.fmdl` works as now. The first
      plain **Save** on it shows a one-time prompt ("Evans is moving to a new
      model file, `.evx`. Save this one in the new format?") with *Save as .evx*
      and *Keep .fmdl this time*, and Save then writes `name.evx` beside the
      original. Rules: the original is never deleted or renamed, and the new file
      is written completely before anything else happens; Open, `open_system`,
      `sim`, referenced models and script links try `.evx` first, then `.fmdl`;
      Save As offers both types, so a copy for someone on an older Evans can still
      be saved as `.fmdl`; autosave never converts and never asks; a file already
      in `.evx` never sees the prompt. The patch notes tell users that older
      versions cannot open `.evx`.
      *Done 2026-11-11:* as decided. `sim/model.py` holds the suffixes and the
      `.evx`-first lookup, and writes a model to a `.part` file that is then
      swapped in, so a failed save leaves the old file whole. The Model tab
      now remembers its file (`SimTab.model_path`): **Save** writes to it and
      **Save As…** asks, offering `.evx` and `.fmdl`. An example, the starter
      model and one the console puts on the canvas have no file, so Save asks
      where. If `name.evx` already exists, Save as .evx opens Save As instead of
      overwriting it. A recent `.fmdl` with a newer `.evx` beside it opens the
      `.evx`. The installer task is now `modelassoc`, covering both types.
      Left for later: the release's patch notes must say older versions
      cannot open `.evx`. Referenced models and script links do not exist yet;
      when they are built, use `find_model_file`.
- [x] **Full test run crashes in garbage collection (Windows).** Found while
      doing the `.evx` rename (2026-11-11). With that branch, `python -m
      pytest` died with "Windows fatal exception: access violation" during
      garbage collection three times. It was in `test_symbolic.py` twice
      (`test_numden_and_sym2poly_make_a_tf`, and in `inv`), and once in
      `test_plot_ui.py::test_a_theme_switch_recolours_a_mesh_without_redrawing`
      (pyqtgraph `AxisItem.paint`). It follows test-run allocation, not any
      one test: it needs both updated tests that now run through,
      `test_sim_editing.py::test_the_examples_show_what_they_promise` and
      `test_sim_workspace.py::test_save_and_load_by_name`, and neither alone
      triggers it. Neither makes Qt objects. HEAD without the branch runs the
      same files clean, and main has crashed like this at least once
      before. A `gc.collect()` after every test removes it (run time ×2.5);
      once per file does not. The real app survives opening, running and
      saving every example and both prompt answers. Likely a PySide6/pyqtgraph
      wrapper left by an earlier Qt test and collected late: find which
      test, and delete its widgets properly. **S–M**
      *Fixed, 2026-11-11:* not a leftover widget. matplotlib's Qt canvas
      queues its redraw (`draw_idle`: a data tip, a theme switch, a rotation)
      on a zero-length timer. `test_plot_ui.py`'s 3-D tests closed and
      dropped a view before that timer fired, so the redraw ran on a canvas
      whose Qt side was gone. `height()` raised inside the timer callback,
      and PySide6 6.10 then released an object it did not own, the canvas
      class's own `paintEvent` function. Whatever touched that freed memory
      next crashed: a paint, or the next garbage collection, wherever the
      run happened to be. Found with a probe that collected after every
      module, then a walk over `gc.get_referents` that stopped on the
      dangling pointer. The figure view now builds its canvases from a
      subclass whose queued redraw does nothing once the canvas is deleted
      (`figure_view._canvas_class`). App code, not a test: closing or
      rebuilding a 3-D figure with a redraw still queued could hit it too.
      Test: `test_a_redraw_queued_for_a_deleted_canvas_does_nothing`.
- [x] Install page: step-by-step for an unsigned Windows installer (SmartScreen
      > More info > Run anyway) and an unnotarised Mac app (Privacy & Security >
      Open Anyway). **S** *Already there (checked 2026-11-11):*
      `site/pages/install.html` has `#smartscreen`, `#gatekeeper` and `#unsigned`.
- [x] **Mac update path** (the part of "Auto-update on macOS" that 1.0 needed). *Done
      2026-11-11: the update check reads the `.dmg` asset on a Mac and the installer
      `.exe` elsewhere (`update.asset_pattern`), and the Mac prompt opens the `.dmg`
      download.* Before that, the Mac app checked GitHub at launch
      (`update.is_packaged`) and offered the release page because it cannot replace
      itself, but it read the Windows `.exe` asset's presence and checksum, so a
      release whose Windows build was missing would have hidden the update from Macs
      too. Self-update stays open in the roadmap: with the ad hoc signature CI uses,
      Gatekeeper quarantines a downloaded replacement, so it needs notarisation first.
- [x] **The MATLAB reference corpus, recorded.** MATLAB R2023a Update 2's answers to the
      496 probes in `tools/matlab_reference/evans_reference.m`, recorded 2026-11-13 on
      the school computer with the Control, Signal and Optimization toolboxes, are in
      `tools/matlab_reference/evans_reference.mat`. A one-off replay through
      `Interpreter.run_script` (2026-11-14) gave 424 of 492 usable probes in agreement
      and 68 not. Left out: probes 472, 476 and 477 (that computer has MOSEK on its
      path, and its `linprog`/`quadprog`/`intlinprog` answered instead of MATLAB's)
      and 488 (a datetime display format, not a real difference). The checker and the
      remaining differences are open in the roadmap.
      - [x] **Silent wrong answers (32).** The worst kind; fix these before 1.0. **M**
            *Fixed 2026-11-18, all 32; each has a case in
            `tests/golden/test_confident_liars.py` (class, size and value as
            recorded) and `test_types.py`.*
            - Char matrices: `['ab'; 'cd']` and `lower(['A';'B'])` give a cell,
              not a 2×2 / 2×1 char (176, 228). (fixed 2026-11-18: a
              `CharMatrix` value for char arrays of more than one row; it
              indexes, converts with `double`, shows as `2×2 char array`, and
              rows of different lengths are an error. Not yet: `char(a, b)`,
              `strvcat`, and char matrices inside other functions.)
            - `x = 5; x(2) = 7` makes the array `int64` (319). (fixed
              2026-11-18)
            - `double("3.5")` gives the character codes, not 3.5 (252). (fixed
              2026-11-18)
            - `sum`/`prod` of integers saturate in the integer class; R2023a
              gave the true value as a `double` (51, 52, 405). (fixed
              2026-11-18. Settled from the recording, not from `which sum`:
              `evans_reference.mat` holds class `double` and the unsaturated
              values 200 and 40000 for probes 51, 52 and 405, so the Phase 4
              note that `sum` keeps the integer class was wrong for `sum` and
              `prod`; `cumsum`, `max`, `abs` … still keep it, and `single`
              stays `single`. The `which sum` re-record below is still worth
              doing, to rule out a shadowing `sum` on that machine.)
            - Edge cases: `1/-0` is `+Inf` (34); `rem(5,0)` is not NaN (6);
              `size(1:0)` is `[0 0]`, not `[1 0]` (69); `sum`/`mean` of
              `zeros(0,3)` give one value, not 1×3 (110, 114); `sum(x, [1 2])`
              adds over the wrong dimensions (151); `eps(single(1))` is a
              `double` (30); after `for k = 1:0`, `k` should exist as `[]` (318);
              `s(5) = 'e'` on a 3-char string should pad with char 0 (158).
              (all fixed 2026-11-18; `eps` is now a function, `eps(x)` works)
            - Text: `num2str` of a matrix gives one row (185); `int2str(2.5)`
              rounds to 2, not 3 (189); `mat2str` of logicals should say
              `true`/`false` (188); `sprintf('%s', 65)` gives `'65'`, not `'A'`
              (206); `strcmp(cell, char)` returns one value (226); `regexp`
              tokens are nested one level too deep (221); `strcat({'a '}, 'b')`
              gives a char (175); `string(1/3)` should be `"0.33333"` (251);
              `sprintf` with a string format should return a string (264, 265).
              (all fixed 2026-11-18; 221 already matched by the time it was
              checked, so it only gained a regression test. `num2str` of a
              row with fractions, `[1.5 2.25]`, now spaces like MATLAB too.)
            - Control: `pole` returns a complex row, not a real column (412,
              440, and `rlocus` columns in 446); `freqresp` squeezes to a column
              (435); `margin` when the gain is exactly 1 at DC (418: MATLAB gives
              Pm −180, Wcp 0; Evans Inf, NaN). (all fixed 2026-11-18: `pole`
              is a real column when no pole is complex, `freqresp` is
              `ny×nu×N`, a piece of a complex array with no imaginary part is
              real so `r(:, 1)` of `rlocus` is real, and `margin` reports
              Pm −180 at Wcp 0 for a unit DC gain.)
            - `interp1(..., 'nearest')` breaks a tie downwards (367). (fixed
              2026-11-18)
- [x] A startup-time test and budget, and a size budget. The `dist/Evans` folder is
      343 MB. **S** *Done 2026-11-11:* `tests/test_startup_budget.py` (cold window
      build, median 9.3 s here, budget 20 s, `EVANS_STARTUP_BUDGET_S` to override);
      CI runs `tools/check_size.py` on `dist/Evans` (395 MB), the installer (140 MB)
      and the `.dmg` (126 MB): 0.24.0 plus 15%.
- [x] A `CHANGELOG.md` in the repo and a stated stability policy. **S**
      - [x] `CHANGELOG.md`, *done 2026-11-11:* every version from 0.9.0 to 0.20.0,
        a "before 0.9" entry and an Unreleased section. `tests/test_changelog.py`
        fails when the current `evans.__version__` has no section.
      The stability policy was decided 2026-11-11 (part 5) and stated in the README's
      and the site's "Stability" sections; its text is in the roadmap's 1.0 section.
- [x] Fix the `pyproject.toml` comment that still says "432 tests". **S**

---

## 5. The 1.0 proposal (2026-11-11)

Written from the roadmap and the code for the Phase 6 item "a stated stability policy,
and a 1.0 once Phases 1–2 land" (Phases 0–4 were done by then). Leon decided it the same
day; the decisions and the policy are in the roadmap's 1.0 section, which is where they
stand now. Phase 8 was added to what blocks 1.0 on 2026-11-16. Kept here: the reasoning.

### What 1.0 would mean

1.0 says: *you can build on Evans without it breaking under you.* It is not a
claim that Evans does everything MATLAB does (the "Not in Evans" help page
says what it does not). It is a promise about what stays put.

### Must-have before 1.0 (proposed)

| Item | Why it should block 1.0 |
|---|---|
| **The stability policy above, in the README and site, plus a `.evx` round-trip test** across every example and a fixture file per past format (**done**: README and site "Stability" sections; `tests/golden/test_model_compat.py` with frozen fixtures in `tests/fixtures/models/`) | A promise nobody can check is not one. The format version exists; what is missing is a test that keeps old files opening. Small. |
| **A reference corpus of real MATLAB outputs** (Phase 6; also closes the open "search for more silent wrong answers" item in Phase 0) | "MATLAB-compatible" is the promise. It is currently backed by closed-form tests and reading MATLAB's documentation. A corpus run once on a licence turns it into a regression suite. Medium; needs a MATLAB licence to produce. |
| **Numeric array writes in place** (Phase 0, `a(k) = v` is quadratic) | The one known performance trap in ordinary loops; 10^4 writes take 0.4 s and it grows with the square. A 1.0 user who pre-allocates and fills a vector should not hit it. Medium. |
| **A startup-time and size budget** (Phase 6) | Cheap, and stops 1.x from slowly getting heavier (343 MB today). Small. |
| **Mac update path** (read the `.dmg` asset; notarisation is a separate question, below) | Today a missing Windows asset hides the update from Macs. That is a bug, not a feature. Small. |

### Can wait until after 1.0

- **Handle graphics** (`h = plot(...)`, `set(h, ...)`): large, additive, no
  compatibility risk for existing files or scripts.
- **Better block shapes, scope overhaul, subsystem leftovers, script pre-run for
  a model, MIMO `linearize`, a user block API:** all additive. The script pre-run
  adds fields to the model file, which is allowed under the policy.
- **Phase 5** (serial hardware, system identification, `dsolve`) and **Phase 7**
  (acausal modelling, FMU, `.slx` import, code-first models, browser build,
  extensions): each is a large separate product decision. None changes what 1.0
  promises.
- **Profiler, `publish`, git status in the file browser, the `B905` audit.**
- **Self-updating on macOS:** needs notarisation first.

The questions put to Leon, all answered by the decisions:

1. **Code signing before 1.0?** The Windows installer is unsigned on purpose. A
   1.0 that SmartScreen warns about reads badly, but the Certum certificate costs
   money and the user count is small. Sign for 1.0, or keep it unsigned and say so
   in the release notes?
2. **macOS notarisation before 1.0?** The Apple developer fee, and it is the
   prerequisite for Mac self-update. Is a Mac-first-launch warning acceptable at
   1.0? And an Intel build: only if someone asks?
3. **A Linux build (AppImage or `.deb`)?** CI already tests on Ubuntu. Is Linux a
   1.0 platform, or "runs from source" until later? The policy above would then
   name the platforms it covers.
4. **Does the reference corpus block 1.0?** It needs a MATLAB licence, which only
   you may have access to. If not, the MATLAB-compatibility promise is worded
   more softly ("where documented").
5. **How long do you guarantee `.fmdl` reading?** The proposal says all of 1.x.
   A shorter promise is cheaper to keep.
6. **Is the Python-side API (`evans.*`) part of the promise,** or console-only?
   The proposal leaves it out.
7. **Date or readiness?** 1.0 when the must-haves land, or on a date (a semester
   start, say) with whatever has landed?

---

## 6. Phase 8, the interface rework (from 2026-11-16)

Planned 2026-11-16 from a UI audit (research into comparable tools, a code inventory
and offscreen renders of every workspace) and two rounds of decisions with Leon. It
continued the UI redesign (part 3), and where the two disagree it is what was built.
Its open packages, decisions and rules are in the roadmap; the finished packages are
below, each with what was built and the decisions taken where the spec met the code.
The specs themselves are in git history.

### 8.0 What the audit found

Evans has the right skeleton: three workspaces on a rail (`ui/workspace.py`), a loop
summary bar (`ui/context_bar.py`), linked analysis panes (`ui/panes.py`), one window.
What is missing is what ties it together:

- No way to search for an action. Seven menus, one of them (Settings) with one item.
- Undo exists only on the Model canvas. A plant edit, *Apply as K₂*, a preset or a
  snapshot restore on Analyse cannot be undone.
- "Model" names two things: the block-diagram workspace, and the dock that edits the
  course loop (*Edit model*, View ▸ Model panel).
- Three saves: File ▸ Save session (Ctrl+S), the Model toolbar's Save (no shortcut),
  and the script editor's Ctrl+S, which shadows the first.
- The Apps menu opens three docks (LTI Viewer, Control System Designer, PID Tuner)
  that only make sense on Analyse but stay open over Model and Console and squeeze
  them. At default width they clip their own plots behind a horizontal scrollbar.
- The loop dock (`_model_dock`) docks to the left of the rail, so the rail ends up in
  the middle of the window.
- Cedric's panel exists only on the Console workspace, and the shrimp at the rail's
  foot opens the documentation, not Cedric.
- Blocks can only be added from the palette (double-click or drag). No keyboard path.
- No start screen. First launch shows one step response; examples and presets are in
  menus only. Nothing ties a model, its scripts and its figures together on disk.
- Plot defects seen in the renders (8.3).

### Finished packages

- [x] **R0 — Quick fixes, no structural change.** *sonnet.* **M**
  Small independent items, one batch, one full test run.
  - **Root locus range and ticks.** With the default plant `4/(s²+2s+4)` every branch
    lies on Re = −1. The pane's x-range collapses to about 1e-15, tick labels read
    `−1.0000000000000002` and the plot fills with bars. Find where the root-locus
    response sets its view range (`core/viewer.py` builds the data, `ui/apps/`
    `lti_viewer.py` `_paint` draws it; the Designer's `_draw_locus` in
    `ui/apps/designer_app.py` has the same risk). Fix: after computing the data
    bounds, if a span is under 1e-6 of the other axis's span (or under 1e-9
    absolute), widen it to match the other axis's span, centred. Add a test with
    this plant that asserts the x-range is at least 1 wide and every tick label is
    under 8 characters.
  - **Legend over the data.** In a small pane the legend covers the curve (seen on
    the root locus and Bode panes at 2×2). Place the legend in the corner with the
    fewest data points (count points in each quadrant of the view box), and when the
    pane is narrower than 360 px hide the legend if there is a single curve (the
    pane header already names the system).
  - **Bode label collisions.** The *peak*, *BW* and *ωc* annotations overlap when
    their frequencies are close. After placing them, sort by x and nudge each label
    up by one text height while it intersects the previous one.
  - **Examples open fitted.** `MainWindow.open_example` calls
    `self._sim_tab.load_model(...)` but not `fit_all()`; `_on_console_model` does.
    Call `self._sim_tab._canvas.fit_all()` after loading in `open_example`, and in
    `SimTab.load_model` itself so File ▸ Open gets it too. Fit after the page is
    shown (a zero-size view fits to nothing): if the Model page is not current,
    switch first or fit on the next `showEvent`.
  - **First launch opens 2×2.** In `evans/app.py` `main()` and wherever
    `restore_layout()` returns False, call `win.set_pane_layout(4)` (it uses
    `DEFAULT_LAYOUT` = step, Bode, root locus, metrics). `reset_layout()` also goes to
    2×2 instead of `set_layout_size(1, ("step",), (None,))`. Update the tests that
    assert one pane after a reset.
  - **Files dropped on the window open.** `MainWindow.setAcceptDrops(True)`;
    `dragEnterEvent` accepts only `event.mimeData().hasUrls()` with local files;
    `dropEvent` calls `self.open_recent(path)` per file (it already routes models to
    Model and scripts to Console). The canvas's own block drops use another mime
    type and must keep working (`ui/sim/canvas.py` `dropEvent`): test both.
  - **Model file shortcuts.** On the Model toolbar (`SimTab._build_toolbar`) the
    tooltips for Open, Save, Save As gain `(Ctrl+O)`, `(Ctrl+S)`, `(Ctrl+Shift+S)`.
    Do not set the shortcuts on those toolbar actions (two actions with one
    shortcut are ambiguous in Qt and neither fires). Instead make the File menu's
    actions dispatch on the current workspace, in new methods `MainWindow.file_open`,
    `file_save`, `file_save_as`:
    Analyse → `_open_session` / `_save_session`; Model → `self._sim_tab.open_model()`
    / `save_model()` / `save_model_as()`; Console → the script editor's own open and
    save (`ui/console/script_editor.py` defines Ctrl+N/O/S/Shift+S/W on the editor;
    when the editor has focus its shortcut wins, so check that pressing Ctrl+S with
    focus in the command window also saves the current script and does not raise an
    ambiguity). Rename the menu items to *Open…*, *Save*, *Save as…* and set their
    status tip from the workspace on `_on_workspace_changed` ("Save the loop",
    "Save the model", "Save the script"). Tests: one per workspace, patching the
    file dialogs.
  - **One verb.** "Apply to Architecture" (`ui/tabs/design_tab.py`), "Apply as K₂"
    (designer and PID tuner) and "Send to analysis →" (`ui/tabs/modern/`
    `modern_tab.py`) all become **Apply to loop**. Tooltips say which block changes
    ("Sets K₂ to this controller").
  - **Check the glyphs on a real screen.** The offscreen renders showed empty boxes
    for ω, ζ, ▾ and superscript minus. That is probably the offscreen platform's
    font database lacking the fallback faces named in `theme.py`
    (`SANS_FALLBACKS`, `MONO_FALLBACKS`). Run `python app.py` on Windows, look at the
    context bar (ωc), the Bode axis (10⁻¹), the *Characteristics* button and the
    Designer's *Set K for ζ* button. If any box shows on a real screen, replace the
    glyph with text the bundled fonts have, and add the string to the no-pictogram
    test. Write here what was seen either way.
  Done when: the items above have tests, `tests/golden/test_ui_layout.py`,
  `test_ui_smoke.py`, `test_canvas.py` and `test_apps_ui.py` pass.
  *Done 2026-11-18:* all items built, tests in `tests/golden/test_r0_quick_fixes.py`.
  Root locus: the panes draw through `LTIViewer`, so the range fix lives there
  (`_fit_degenerate`) and in the Designer's `_frame`, both via
  `plots.widen_degenerate_range`. Legend: `emptiest_corner` / `place_legend`, hidden
  under 360 px when it has one entry. Bode labels: `plots.separate_labels` (redone on
  resize, since text size is in pixels). `SimTab.load_model` fits at once and again on
  the next show if the page was hidden. A file dropped on the canvas is handed up by a
  `files_dropped` signal (a drop on the code editors still inserts the path as text).
  `app.main()` never called `restore_layout()`, so a saved layout was not coming back
  at launch; it now does, and opens 2x2 when nothing is saved.
  *Glyphs (checked without a screen, 2026-11-18):* with fontTools, Segoe UI has
  omega, zeta, superscript minus and subscript 2 but not the small down triangle
  (U+25BE); Consolas has all of them; Cascadia Mono lacks superscript minus; Arial
  lacks superscript minus and subscript 2; Archivo and Martian Mono have none of the
  Greek or the triangle. Painting each glyph with the theme's own font chain through
  the real Windows platform gave a non-blank, non-notdef image for omega, zeta, the
  triangle, superscript minus and subscript 2 in both sans and mono. No glyph was
  replaced. **A by-eye check on a real screen is still left for Leon** (R9 repeats it).
  *Added 2026-11-18 (Leon):* File ▸ New (Ctrl+N) dispatches like Open and Save
  (`MainWindow.file_new`): a default loop on Analyse (one undo step, "New loop"), an
  untitled model on Model (`SimTab.new_model`), a new script on Console, or a new live
  script when the Live tab shows (`LiveScriptEditor.new_document`). "Session" is gone
  from the File menu and the loop file dialogs: until R7, loops and files; then
  projects. R4's *New ▸* submenu builds on `file_new`.

- [x] **R1 — Undo for the loop, and an Edit menu.** *sonnet.* **M**
  - *Done 2026-11-18:* `ui/loop_undo.py` (`ReplaceLoop`), `MainWindow.change_loop`
    / `_after_loop_change` / `_loop_baseline`, Edit menu with a `QUndoGroup`,
    `tests/golden/test_loop_undo.py` (20 tests). `change_loop` takes `before` from
    the baseline, not from a fresh `session_dict`, so the Design tab, snapshot bar and
    Modern tab (which write `arch` before signalling) are covered; `mutate` is
    optional. The canvas swaps its `undo_stack` when you descend into or leave a
    subsystem, so `_sync_undo_group` (also run on `path_changed`) adds the live stacks
    to the group and drops the dead ones. "Undo: <text>" uses the group's
    `indexChanged` and `redoText()`. A new session is itself an undoable step
    ("New session"). The Model toolbar buttons keep working; only their shortcuts
    went. Ctrl+Z in the script editor still undoes typing (tested). Changed
    assertion: `test_title_bar.py` menu list now has Edit after File.

- [x] **R2 — The side panel.** *opus.* **L**
  The structural package. After it there are no `QDockWidget`s left except the app
  docks, which R3 removes.
  *Done 2026-11-18:* `ui/side_panel.py` (`SidePanel`, `page_with_panel`); each page
  is `[content | SidePanel]`; one `AssistantPanel` (`MainWindow._cedric_panel`)
  moved by `_place_cedric` on every workspace change; `LoopSource` and
  `ModelSource` are read-only `DescriptionSource`s (context origin
  `"description"`, no region, `apply` refuses); tests in
  `tests/golden/test_side_panel.py` plus the rewritten layout, Cedric, rail and
  history tests. Decisions where the spec met code it did not foresee:
  - **The window minimum would have grown.** The Console page's minimum was set by
    the Live tab's 1000 px button row, and the snapshot bar's status label asked
    192 px; a 240 px panel beside either broke the 1280 px budget. The Live
    buttons now sit in a `QToolBar` (overflow behind its arrow, as the Model
    toolbar does) and the snapshot status label takes no width. With every panel
    open the minimum is 1061×331, under 0.27.0's 1146×331 (the test pins that).
  - `SidePanel.is_open` is its own flag, not `isHidden()`: a child widget counts
    as hidden until its window first shows, so a fresh Analyse panel looked
    closed and then appeared. The width is the one asked for or last dragged
    (`splitterMoved`), never read back from the geometry, which lags a layout.
  - Ctrl+Shift+A stays a toggle (checked while the panel in view shows Cedric),
    so the Console tab bar's *Ask Cedric* button keeps working as before; the
    shrimp only opens. The panel's × closes it whatever the tab.
  - `ConsolePanel.show_history` cannot reach the side panel, so it emits a new
    `side_requested("history")`; `.workspace` and `.history` stay attributes.
  - `ContextBar.describe()` (summary plus PM, GM, ωc) feeds `LoopSource`, since
    `summary()` has no margins and its text is asserted elsewhere.
  - The Model panel's old 340 px cap is gone (default 320, minimum 240).
  - No `Workspace`-level setting was added: the three `side/<workspace>/…` keys
    are layout keys (cleared by Reset layout), and `modelPanel`/`cedricPanel`
    are migrated, then removed, on the first restore that finds them.
  Check by eye on a real screen: the Docs button and the shrimp at the rail's
  foot, the Live toolbar's overflow arrow at narrow widths, the side panels'
  tab bar and × in both themes, and dragging a panel wider then closing and
  reopening it.

- [x] **R3 — The Design tab; the three apps go.** *opus.* **L** Needs R1 and R2.
  *Done 2026-11-18:* `ui/design_panel.py` (`DesignPanel`), the Compare menu in
  `ui/panes.py` (`CompareOption`, `AnalysisPane.set_compare`/`tick_compare`,
  `PaneGrid.compare_options`), `MainWindow.show_design` / `_apply_design` /
  `_sisotool` / `_pidtuner` / `_ltiview`; tests in the rewritten
  `tests/golden/test_apps_ui.py` (45). Decisions where the spec met the code:
  - **No `compact` flag.** With the docks gone nothing wanted the full layouts,
    so `ControlSystemDesigner` and `PIDTuner` are compact-only (their Bode and
    step plots, *Apply to loop* and the tuner's plant/current/tuned overlay
    are deleted). The designer is one widget: locus (220 px), the rays check, a
    stack of two control pages (Gain, Compensator) and a readout; the panel's
    segmented control picks the designer's page or the tuner. The readouts
    are word-wrapped labels, not text boxes. `PIDTuner.set_plant` lost its
    `baseline` argument (only the deleted plots used it).
  - **Signals, not apply calls.** The designer emits `changed(what, final)`
    and the tuner `changed(final)` only for user gestures (never from
    `set_plant`/`set_compensator`/`set_kind`), and the panel throttles: a held
    slider or pole target applies at most every 50 ms, release applies once
    more. The designer's own drag timer became a 50 ms throttle (it was a
    60 ms debounce, so a steady drag never updated).
  - **Merge keys are per gesture**: `design-gain/<n>` and so on, `n` bumped
    after each final apply. With a fixed `design-gain` two separate drags in a
    row would have merged into one undo step.
  - **Re-reading the loop** happens in `DesignPanel.loop_changed`, called from
    `_after_loop_change` and `_on_console_executed`. Its own apply only marks
    the *other* half stale (a PID applied from the PID view re-reads the
    designer when you switch back). Hidden halves re-read when shown, and both
    halves are built on first show, not at launch (a quarter of a second off
    the startup budget).
  - **Reset** goes back to K₂ as it was at the tab's last non-spontaneous
    show (switching workspace and back counts as a new opening). It is its
    own undo step, "Design: reset", and the widgets follow it.
  - **`sisotool(G, C)`** loads G and, with C, writes C into K₂ in the same
    undo step ("sisotool"): with live apply a designer showing C while the
    panes showed another K₂ would be two truths. `pidtuner(G)` without a type
    now keeps the type chosen in the tab (`api.pidtuner`'s default `kind`
    became `None`); `pidtuner(G, 'pid')` sets it without applying.
  - **Compare.** Entries are keyed `("loop", Source)`, `("snapshot", label)`,
    `("system", name)`. A snapshot draws as *the pane's own system* of the
    snapshot's loop (its L in a Bode-of-L pane). `ltiview(...)` sets the first
    plot pane's Compare set to exactly the named systems and keeps them on
    offer in every pane; `ltiview` with nothing named compares G, L and T. A
    deleted snapshot drops out at the next refresh. Ticks ride along a 1/2/4
    re-layout (like sources) but are not saved.
  - **The pane minimum.** The Compare button would have widened every plot
    pane by its own width (116 px offscreen), so 1×2 and 2×2 with the side
    panel open would no longer fit 1280. The two header combos now elide from
    seven characters instead of twelve; the pane's minimum is exactly what it
    was (402 px offscreen) and the window's minimum is unchanged.
  - **Found: the root-locus pane could freeze.** `core.stability.
    marginal_gain` handed the axis-crossing equations to sympy with the
    coefficients as exact rationals; for a tuned PID times 1/(s+1)³ the
    rationals had huge denominators and the solve ran for minutes. Live apply
    made that one slider move away, so it now eliminates K and takes the real
    roots of one polynomial in ω numerically, polished by Newton (the
    textbook values still agree to 1e-9; `test_analysis_values.py`).
    `pid_tuner._settles` stays: the Model's tune dialog imports it.
  - Kept: `ui/apps/lti_viewer.py` (the pane renderer; its full mode is still
    used by `test_plot_readouts.py`), the *Design* workflow pane kind, and the
    console's "Apps" command group name.
  Changed assertions: `test_title_bar.py` (no Apps menu);
  `test_r0_quick_fixes.py` (the Design tab has no Apply button);
  `test_ui_layout.py` (no dock at all; the app-dock size and windows tests
  became Design-tab ones, the size one measured against the Loop tab
  because the context bar's width depends on the loop earlier tests left;
  `sisotool(G, C)` also sets K₂); `test_apps.py`
  (`pidtuner(G)` sends no kind). Check by eye on a real screen: the
  segmented control and the Design tab at the panel's 240 px minimum (the
  Gain page may scroll sideways there), dragging the pole target and the gain
  slider with four panes following, the Compare menus and their legends in a
  small pane, and the shortened header combos at 1280 wide.

- [x] **R4 — Menus, preferences, bottom bar, a slimmer context bar.** *sonnet.* **M**
  Needs R2 and R3.
  *Done 2026-11-18:* `ui/preferences.py` (`PreferencesDialog`,
  `preferences_dialog(window)`), `LoopStatus` and the elided, two-line-capable
  context bar in `ui/context_bar.py`, the four menus and the Plant menu in
  `MainWindow` (`_build_menus`, `_build_export_menu`, `_build_plant_menu`,
  `_build_status_bar`, `_sync_status_bar`), tests in
  `tests/golden/test_r4_menus.py` (33). Decisions where the spec met the code:
  - **File ▸ New stays the single per-workspace New** (Leon, 2026-11-18), not
    a "New ▸" submenu; Open, Save and Save as dispatch as in R0. R7 makes the
    submenu. Autosave is no longer a menu: `MainWindow` keeps
    `_autosave_enabled` / `_autosave_interval` (read from `recovery`), and
    `set_autosave` is the one place they change.
  - **Export ▸ is a File submenu** with the six items unchanged; the PNG item
    is *Export pane as PNG…* on Ctrl+Shift+E and still saves the whole pane
    grid, as before. Ctrl+Shift+P is free for R5.
  - **Block palette (Ctrl+B)** was a Model-toolbar action only. The shortcut
    moved to View ▸ Block palette (two actions with one shortcut fire
    neither); the toolbar button stays. `SimTab.palette_changed` keeps the
    menu check in step. The shortcut works on any workspace but only the
    Model has a palette to show.
  - **Preferences** is one non-modal dialog (`MainWindow.preferences_dialog()`
    builds it once, `show_preferences()` shows it), a form of three groups,
    every control applied at once and an accessible name on each. Its
    controls follow changes made elsewhere through `sync()`, which the
    window's setters call. The theme combo goes through `choose_theme`; a
    declined restart puts the old choice back. The integrated title bar shows
    the saved preference (it stays unticked and disabled off Windows). New
    persist keys, with getters and setters that refuse a bad value:
    `startup/show` (`start` default, `reopen`; nothing reads it until R8) and
    `model/scopeOpensIn` (`window` default, `panel`; R6 reads it).
  - **Edit** has Undo, Redo, *Send loop to the console*, Preferences… (Ctrl+,
    with `QAction.PreferencesRole`). `keys.label` now rewrites `Ctrl+,` and
    `Ctrl+/` for the Mac. Keyboard shortcuts (Ctrl+/) is omitted until R5.
  - **Bottom bar.** `LoopStatus` (lamp, PM, GM, ωc) is built by `ContextBar`
    (`ContextBar.status`, so `verdict`, `summary()` and `describe()` still
    work) and put in the status bar by `addPermanentWidget`, visible on
    Analyse only. The verdict note is the lamp's tooltip. The Console shows
    *Idle* / *Running* from a new `ConsolePanel.run_state_changed(bool)`,
    emitted for typed commands and for scripts (`_begin_run` / `_end_run`).
  - **The context bar is slimmer and cannot widen the window.** G(s) and
    K₂(s) are elided labels (`text()` and the tooltip stay whole) in a box
    that goes beside each other when both fit and stacks otherwise. That is
    what brought the R3 case (a wide loop needing 1284 px) back inside
    1280×720: the labels used to ask for their full text width. The Plant
    button is a `QToolButton` with an instant popup (Qt draws its arrow; no
    glyph in the label).
  Changed assertions: `test_title_bar.py` (four menu titles; the title-bar
  toggle is read from the dialog); `test_block_shapes.py` and `test_theme.py`
  (the classic-boxes and theme controls are the dialog's); `test_recovery.py`
  (autosave on/off and interval are the dialog's); `test_update.py` (Check for
  updates automatically is no longer in a menu, it is in the dialog);
  `test_ui_layout.py` (the margin labels are `_context.status._pm`; the
  snapshot-bar action is `_act_snapshot_bar`, and the dialog follows it).
  Check by eye on a real screen: the Plant button and its arrow, the context
  bar going from one line to two as the window narrows, the lamp and margins
  in the status bar in both themes, the Preferences dialog's look, and
  Ctrl+, and Ctrl+Shift+E from each workspace.

- [x] **R5 — Search: the command palette, and the shortcut sheet.** *sonnet.* **M–L**
  Needs R4.
  *Done 2026-11-18:* `ui/search.py` (Qt-free: `Entry`, `score`, `rank`, `remember`;
  `tests/test_search.py`, 16), `ui/search_registry.py` (`collect(window)`),
  `ui/search_popup.py` (`SearchPopup`), `ui/shortcuts.py` (the sheet), the title-strip
  field in `ui/titlebar.py`, `MainWindow.show_search` / `toggle_search` /
  `show_shortcuts` / `show_pane_kind`, `PaneGrid.active_index`, and
  `tests/golden/test_search_ui.py` (36). Decisions where the spec met the code:
  - **Scoring** is a subsequence match with the best alignment (a small DP over the
    matched letters): +4 at the start of the text, +2 at a word start (also camelCase),
    +2 for a letter right after the previous one, a small gap and length penalty.
    `rank` groups current workspace, global, other workspaces; empty query puts the
    recent entries first. `search/recent` holds 20 ids (`persist.search_recent`).
  - **Menu entries** come from walking the menu bar; ids are the action's object name
    when set (Undo, Redo, Search, Keyboard shortcuts) and otherwise a slug of the path
    (`file.save_as`, `file.export.model_diagram`). The *Open recent* and *Examples*
    submenus are skipped in the walk (`searchSkip` property): their files and models
    have entries of their own ("Open: x.m" under *Recent*, "Example: ..."), so every
    action still appears once. Workspace-specific actions carry
    `action.setProperty("workspace", ...)`: Export (analysis ones Analyse, model ones
    Model), Send loop, Snapshot bar, Block palette.
  - **Where R3/R4 moved things:** "Design tabs" are the Design panel's Gain ·
    Compensator · PID (`Design: PID` calls `show_design`); presets are the Plant menu's
    seven, listed from `MainWindow._PRESETS`; there is no separate go-to-workspace entry
    because View already has the three workspaces.
  - **Help pages** ("Help: bode", 540 of them) belong to Console for ranking but do not
    switch workspace: the help window is its own window. Everything else of another
    workspace switches first.
  - **Active pane:** `PaneGrid.active_index` follows a mouse press anywhere inside a
    pane (one application-level filter in the grid that reacts to presses only; clamped
    when the layout shrinks). There is no visual marker for the active pane yet; *Show
    Bode* reports "Pane 2: Bode" in the status bar.
  - **Popup:** a child of the window, plate 560 px (window less 32 if smaller), top 48 px
    under the window's top, selection in the tab bars' plate with signal-yellow text, 2 px
    frame and a hard 4 px offset shadow painted by the widget. A press on the title-strip
    field toggles it rather than closing and reopening. A failing entry shows in the
    status bar, not a trace. The palette and the registry are built on first use, so
    startup is unchanged.
  - **Title strip:** `TitleBar.search_button` (a flat button dressed as a field, at most
    280 px, minimum width 0 so it never widens the window; shown from 900 px; the real
    window's own minimum is wider, so that rule is tested on a bare strip). `region_at`
    reports it as client.
  - **Shortcut sheet:** Help ▸ Keyboard shortcuts (Ctrl+/) is non-modal and built from
    `collect(window, for_sheet=True)` (disabled actions stay, Undo and Redo keep fixed
    names) plus `shortcuts.EXTRA_KEYS`; the same content is the help guide
    `help/pages/shortcuts.md` (a guide, in `help.GUIDES`; linked from the index). A test
    fails when a shortcut is missing from the page; regenerate it with
    `shortcuts.markdown(collect(window, for_sheet=True))`. Added Ctrl+` to the fixed
    list, and Shift+F5 is not listed (F5, F10, F11 as the spec asks).
  Changed assertions: `test_r4_menus.py` (the View menu now starts with Search…; the Help
  menu has Keyboard shortcuts; `test_ctrl_shift_p_is_left_for_search` became
  `test_ctrl_shift_p_belongs_to_search_alone`); the README test count. Check by eye on a
  real screen: the popup in both themes (the selected row, the muted section, the mono
  shortcut), the field in the title strip with the integrated title bar, Ctrl+K and
  Ctrl+Shift+P from each workspace including the script editor, and the sheet.

- [x] **R6 — Canvas quick insert; scope dock option.** *sonnet.* **M** Needs R2 (for
  the side panel) and R4 (for the preference); may run beside R5 or R7.
  *Done 2026-11-18:* `ui/sim/quick_insert.py` (`QuickInsert`, `rank`, `catalog`),
  the three ways in on `SimCanvas` (`open_quick_insert`, `mouseDoubleClickEvent`,
  `_starts_quick_insert`, `_add_connected`), `ScopeView` split out of `ScopeWindow`
  in `ui/sim/scope_window.py`, `SimTab.show_scope` / `dock_scope` / `undock_scope` /
  `docked_scopes`, and `SidePanel.add_tab(before=)`, `remove_tab`, `set_title`.
  Tests: 14 new in `tests/golden/test_canvas.py`, 13 in `test_scope_windows.py`,
  1 in `test_side_panel.py`. Decisions where the spec met the code:
  - **Alt keeps the armed wire, not a cancel.** The spec says today's release on
    nothing "cancels" the wire; it does not, it leaves it armed for the second click
    of click-click wiring (`test_releasing_on_empty_space_keeps_the_wire_armed`).
    Alt on the release gives exactly that, and a plain release after a drag of at
    least 12 px opens the popup. A release on the start port, or within 12 px of it,
    is a click and stays armed.
  - **There was no standing wiring hint.** Only the status line while wiring. The
    canvas now has `HINT` ("Double-click or type to add a block. Drag from a port to
    wire it.") as the viewport tooltip, and the wiring status line adds "drop it on
    empty canvas to add a block (Alt: keep it)".
  - **Popup:** 220 px plate over a field and at most eight rows, in the search
    popup's look (2 px frame, hard 4 px shadow, plate-coloured selection). Empty query
    lists Step, Gain, Sum, Integrator, TransferFcn, Scope, ... first; otherwise
    `search.score` on the type name, then on "category name" at a 20 point penalty.
    A wire dropped from an output lists types whose default block has an input, and
    the reverse. Row click, Enter insert; Esc and a press anywhere else cancel (the
    wire too).
  - **Placement is local and snapped:** a plain insert goes at the point (grid-snapped,
    as `add_block` always does); a dropped wire puts the new block's first matching
    port within half a grid step of the drop point (port offset read from a probe
    `BlockItem`). Block and `Connect` are one macro, "Add connected block". A wire
    from an input that already has a wire is refused with a status message.
  - **Typing** opens the popup for one printable character without Ctrl/Alt/Meta
    (Shift allowed, space not) when no wire is armed and no input-method item has
    focus. The new branch sits last in `keyPressEvent`, after Esc, Delete/Backspace,
    Copy, Paste and Select all, so none of them changed.
  - **Scope:** `ScopeView` (plot plus a Dock/Undock button) is what moves; a
    `ScopeWindow` is a window around one. Docking adds a tab `scope:<path>` titled
    "Scope: <title>" before Cedric, opens the panel and selects it. A double-click
    raises a scope where it already is (window or tab) and otherwise obeys
    `model/scopeOpensIn`; `open_scope_window` on a docked scope undocks it.
    `close_scope_windows` also removes docked tabs; a run redraws both.
  Check by eye on a real screen: the popup's look in both themes, its position near
  the view's edges, a dropped wire (rubber wire visible behind the popup), typing
  with the mouse outside the canvas (opens at the centre), and docking a scope with
  curves on screen, then dragging the panel wider.

- [x] **R6b — Fixes from Leon's review of R2–R5 (2026-11-18).** *sonnet.* **M**
  Leon ran R5's build. Search, the menus, Plant, the lamp and margins, the side
  panels and Cedric were approved. These five things were not:
  *Done 2026-11-18:* `ui/search_field.py` (`SearchField`: a 32 px button in the signal
  yellow with a 2 px frame, `#WorkspaceSearch` in `theme_qt.py`) is in the context bar
  (`ContextBar.search_button`, between G/K₂ and *Plant*), floating over the canvas
  (`sim/arrange.py` `FloatingSearch`, centred, 55 % opaque, clear of the arrange panel)
  and in the Console's tab-row corner beside *Ask Cedric* (240 px there, 360 px at most
  elsewhere). `MainWindow.search_fields()` lists the three; each toggles the palette and
  is ignored by its outside-click rule. The title strip lost the button, its constants
  and the `region_at` case. *Design* button in the context bar; **Edit loop and Design
  both toggle** (close the Analyse panel when it already shows that tab:
  `toggle_loop_editor`, `toggle_design`; `show_*` still only open, for the console
  commands). The designer's locus and the PID page's plot take the free height (minimum
  220 px, no stretch spacer below, the Gain/Compensator stack is only as tall as the view
  in sight). The PID plot is a compact `LTIViewer` (the panes' renderer): Step shows the
  closed loop T, Bode and Nichols show the open loop L, redrawn at most every 50 ms and
  only while in sight; an infeasible target leaves the last plot, as it leaves K₂. The
  Loop tab's diagram stretches (150 px minimum, cap gone), the editor keeps its natural
  height. Model: one selected block reopens a closed panel on Properties (not several,
  not while `rubberBandRect()` is set); `PropertiesTab` is the 28 px vertical tab
  (`‹PROPERTIES`, one letter per line), shown only while the panel is closed, under the
  arrange panel at the right edge. A docked scope tab lives inside the panel, so the
  tab (shown only while it is closed) cannot meet one. Check by eye: the yellow field
  in both themes, the context bar at 1280 px with the panel open (the field shrinks
  first), the vertical tab on a short canvas.

- [x] **R6c — Search field redone; two small layout fixes (Leon's review of R6/R6b,
  2026-11-19).** *sonnet.* **M** Leon approved the Design button, the Design and PID
  layouts, quick insert, two-click wiring, the shortcut sheet, Preferences and Export.
  He rejected the R6b search fields ("the buttons look so bad"; the palette "just kind
  of appears" instead of growing from what was clicked). His decisions, asked and
  answered; do not reopen them:
  - **One field, centred in the window's title strip** (between the menu bar and the
    caption buttons, horizontally centred on the window, like a command centre).
    Same place on every workspace. Remove the three per-workspace `SearchField`s from
    the context bar, the Model canvas and the Console tab row. The field must be a
    client area in `TitleBar.region_at` again (R5 had this; `test_title_bar.py`).
    Where there is no integrated title bar (macOS, Linux, or the preference off), the
    same field floats top-centre over the current workspace's content instead.
  - **Look at rest: Model's R6b style everywhere.** Semi-transparent (about 55 %),
    no fill, thin frame, muted text "Search…" left and the shortcut
    (`keys.label("Ctrl+K")`) right in the mono face. Yellow (signal) 2 px frame on
    hover and while open. Theme tokens only.
  - **Opening: the field becomes the input.** On click or Ctrl+K/Ctrl+Shift+P the
    field itself turns into the text box in place, widening symmetrically around its
    own centre to the palette width (about 120 ms, `QPropertyAnimation` on geometry;
    no animation when the platform asks for reduced motion if that is detectable),
    and the result list drops down directly under it, attached. Esc reverses it.
    Ranking, recency and behaviour of `ui/search.py` / `search_registry.py` are
    unchanged.
  - **Loop tab:** R6b let the diagram take all spare height, which put the block
    editor too low. Balance between R6b and before: give the diagram a stretch
    factor so it takes roughly the upper 45 % of the free height (minimum 150 px),
    the editor directly below, the rest below the editor.
  - **Scope Dock button:** inline with the scope's Export button on the scope
    toolbar row, not on its own line (`ScopeView`, R6).
  Tests: the field is centred in the title strip on every workspace and is client
  area; the fallback field when the integrated title bar is off; clicking or Ctrl+K
  turns it into the input with the list under it (final geometry); Esc restores it;
  no per-workspace fields remain; the Loop tab split; the Dock button shares the
  Export row; window minimum size unchanged.
  *Done 2026-11-19:* one `SearchField` (`ui/search_field.py`, a child of the main
  window, `MainWindow.search_field`) replaces the three; the context bar, Model
  canvas (`FloatingSearch`) and Console tab row lost theirs, as did the
  `#WorkspaceSearch` style. In the integrated title bar it sits at
  `TitleBar.search_rect()` (centred on the window, 24 px, at most 360 px, 16 px clear
  of the menus and the caption buttons, hidden under 140 px); the title text is
  elided before it, and the field and the open palette register with
  `TitleBar.add_client_overlay`, so `region_at` calls them client area. Without the
  integrated bar it floats top-centre over the central widget. At rest: 1 px ink
  frame at 55 % opacity, no fill, "Search…" and `keys.label("Ctrl+K")` in the mono
  face; hover and open: full strength, 2 px signal frame. `SearchPopup.open_with`
  takes an `anchor` (the field's rectangle): the input sits over the field and the
  plate widens about the field's centre to 560 px in 120 ms (a `QVariantAnimation`
  on the plate width, list attached below, signal-yellow frame), Esc or a choice
  narrows it back. `popup.animate` is False under the offscreen platform (the tests;
  a test of the animation sets it True) and `finish_animation()` jumps to the end;
  reduced motion is not detected (Qt has no portable query). Loop tab: the diagram
  has stretch 45 and a trailing stretch 55 sits below the editor
  (`LOOP_DIAGRAM_SHARE`). The scope's Dock/Undock button is a `QPushButton` on the
  scope's toolbar row after Export…; before a run (the message page) it sits on a
  row of that page instead, so it is always reachable. Check by eye on Windows: the
  field next to the menus at 1280 px and while the window is dragged narrow, the
  animation, and a click on the field and on the open palette over the caption.

- [x] **R6d — Simulations run off the UI thread.** *opus.* **M–L** Leon,
  2026-11-19: a long Model run freezes the window, and a click during it brings up
  "Not responding". Decision (asked and answered): **run in the background, model
  locked.** The run moves to a worker thread (`QThread` or a worker object; the
  solver and compile code are pure Python and must not touch widgets), so the window
  keeps repainting and stays usable. During a run the canvas, the block inspector and
  model edits are read-only (no moves, wiring, parameter edits, undo/redo of the
  model, quick insert), with a clear running state: the toolbar's Run becomes
  **Stop**, the bottom bar shows "Running" and progress if the solver reports it.
  Analyse and Console stay usable; console commands that touch the running model
  (`sim`, `set_param` and the like) wait or refuse with a clear message. Scopes
  update as now (results delivered by signal to the UI thread). Stop cancels
  cleanly between solver steps. Model scripts that run before a run (model scripts,
  0.26.0) still run on the console as now, before the worker starts. Closing the
  model or quitting during a run asks or stops it first. Tests: the UI thread stays
  responsive during a long run (an event posted during the run is processed), edits
  are refused while running and allowed after, Stop ends the run, results and scopes
  match a run made the old way, quit during a run, an error in the worker reaches
  the user as now.
  **Decided 2026-11-20: start with a diagnosis.** Step one is to profile a long run
  and find what freezes the window; the decided behaviour above then applies to
  whatever the diagnosis shows is left to build. Add a test for the cause found.
  *Found 2026-11-19 (documentation audit):* the solver already runs
  on a `QThread` (`SimTab.run_simulation` moves a `_Worker` to `self._thread`), with
  a progress bar and a Stop button, and has since before 2026-10-27; Run and Stop
  are already separate buttons. So the freeze is not the run sitting on the UI
  thread. Likely causes to measure first: the pure-Python solver holding the GIL so
  the UI thread rarely gets to run; `compile_model` and the before-run scripts,
  which run on the UI thread before the worker starts; or a flood of progress
  signals. The decided behaviour (model locked, Analyse and Console usable) still
  stands; what is left to build may be smaller.
  **Diagnosed 2026-11-23:** the cause is GIL starvation. The solver thread is pure
  Python and numpy; at the default 5 ms switch interval the UI thread waited up to
  2.6 s (7.4 s in a 3000 s run) for the GIL. The compile step, the progress signals
  (already throttled to 0.1 s) and drawing the result (10 to 30 ms) are not the
  cause on `course_loop()`. Fixed: `sim_tab.RUN_SWITCH_INTERVAL` (0.5 ms) is set
  while a run lasts and restored after; longest stall 80 ms.
  `tests/golden/test_run_responsive.py` tests only the setting (shortened for a
  run, restored after): a test of the stall itself did not fail at 5 ms on a 300 s
  run, and in the full suite its first heartbeat swallowed 13 to 18 s of work that
  earlier tests had left queued, so it was removed. Most of the starvation seen was at
  the start of a run (first UI gap 1.4 to 2.6 s at 5 ms); later gaps were 60 to 350 ms.
  **Built 2026-11-23: the lock** (`tests/golden/test_run_lock.py`). While
  `SimTab._thread` is set the canvas is read-only (`SimCanvas.locked`: no moves,
  wiring, delete, paste, quick insert, parameter dialogs, align; undo/redo refused
  by `_LockableStack`, Edit > Undo greyed in the main window), the inspector and the
  stop time / solver / step controls are read-only, and a refused edit says so in the
  bottom bar. The lock lifts in `_teardown_thread` (finish, Stop, error). Console:
  `sim`, `open_system`, `set_param`, `add_block`, `delete_block`, `add_line`,
  `delete_line` refuse with a message while a run is on (`lib_sim`). Replacing the
  model (New, Open, example, recent, console double-click, quit) asks "Stop it and
  continue?" via `SimTab.settle_run`, called from `settle_unsaved`. Run and Stop stay
  two buttons (decided: not reworked). Not checked: a heavy model, a stiff solver, and the lock by eye
  in the running app (tests only); R9's hardening pass covers the by-eye check.
