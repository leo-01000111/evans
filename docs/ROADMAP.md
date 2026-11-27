# Evans roadmap

What is still open, the decisions that stand, and the order of work. What was built,
and why, is in `docs/HISTORY.md`; where the code is, in `docs/CODEMAP.md`.

Written 2026-10-27 from four audits of the code (MATLAB language, Simulink, toolboxes,
workflow/interop). Cut down to open work only on 2026-11-19 (0.30.1); everything
finished before then, with its notes, moved to `docs/HISTORY.md`, part 4 and part 6.

**How this file is kept.**
- **Only open work lives here,** as `[ ]` items. When an item is done, its text and
  notes move to the matching part of `docs/HISTORY.md` and it leaves this file.
- **Nothing open hides behind a tick.** A finished item whose note says part of it was
  not built leaves that part here as its own `[ ]` item.
- **Every phase heading counts its `[ ]` items.** ◐ means the phase's planned core is
  done and items are left; ○ means the phase has not started. A phase with no items
  left moves to the history whole (Phase 4 still has the gaps its done items left).
- **Decisions are marked *Decided* with a date** and are not reopened in a coding
  session. Questions waiting for Leon are in the last section.

Sizes: **S** under a day, **M** a few days, **L** a week or more.

## At a glance (2026-11-19)

| Section | Open | Next |
|---|---|---|
| 1.0 | 1 | the tag, after the corpus checker and Phase 8's R7 to R9 |
| Phase 0, silent wrong answers | 2 | `struct2table`, then `fzero`'s outputs |
| Phase 1, data work at the console | 6 | |
| Phase 2, Simulink for daily use | 28 | the `pid_saturation` restarts, then the quick speed wins |
| Phase 3, plotting | 6 | TeX text in labels (after the hold) |
| Phase 4, other people's MATLAB code | 14 | |
| Phase 5, hardware, identification, symbolic | 4 | not started |
| Phase 6, platform and trust | 15 | the corpus checker (blocks 1.0) |
| Phase 7, scope decisions | 7 | nothing decided yet |
| Phase 8, interface rework | 5 | R7 (blocks 1.0) |
| Phase 8.4, after 1.0 | 16 | eight items, one of them with seven parts |

---

## 1.0

### What blocks it

1.0 ships when these have landed: readiness, not a date (*Decided 2026-11-11*; Phase 8
added 2026-11-16). The first two are tracked where they live; only the tag is an item
here.

- **The MATLAB reference corpus checker** (Phase 6, "The checker"). *Decided
  2026-11-11:* Leon runs the input scripts on a school computer with MATLAB; Evans
  prepares the scripts and the checker. *Changed 2026-11-20:* the recorded results
  are **not** checked in: they come from an academic licence, so
  `evans_reference.mat` and `verif/` stay on Leon's machine (git-ignored). The checker
  skips when the `.mat` is absent, so it guards 1.0 only where the results exist.
- **Phase 8's open packages:** R7 (projects; *Decided 2026-11-16: before
  1.0*), R8 (Start page), R9 (hardening, documentation, release).
- [ ] **Tag 1.0,** after which versions follow the policy below.

Already landed: the stability policy, stated in the README's and the site's
"Stability" sections, with the `.evx` round-trip test
(`tests/golden/test_model_compat.py`, frozen fixtures in `tests/fixtures/models/`);
numeric array writes in place (Phase 0); the startup-time and size budgets; the Mac
update path. History: `docs/HISTORY.md`, part 5.

### Decided 2026-11-11 (do not reopen)

- **Windows code signing: free only.** Leon applies to the SignPath Foundation (free
  signing for OSI-licensed public projects; the publisher shown is the Foundation;
  Cedric's all-rights-reserved licence may be an obstacle). If they decline, 1.0 ships
  unsigned and the install page explains SmartScreen's "More info > Run anyway". Paid
  Certum signing only if Evans gets real users.
- **macOS notarisation: not for 1.0** (no free route; Apple's programme is $99 a year).
  The install page explains System Settings > Privacy & Security > Open Anyway. Mac
  self-update waits for notarisation; the Mac keeps offering the download page. No
  Intel build unless someone asks.
- **Linux build: not for 1.0**, maybe 2.0. 1.x runs from source on Linux.
- **`.fmdl` reading is guaranteed for all of 1.x.**
- **The Python-side API (`evans.*`) is not part of the promise;** only the
  MATLAB-compatible console, the model files and the settings are.

### The stability policy (from 1.0)

1.0 says: *you can build on Evans without it breaking under you.* It is not a claim
that Evans does everything MATLAB does (the "Not in Evans" help page says what it does
not).

**1. Model files (`.evx`, `.fmdl`).**
- Any file Evans 1.x has written opens in every later 1.x. Any `.fmdl` written
  by 0.9 or later opens in every 1.x. Reading old files never gets dropped inside
  1.x.
- The file carries a format `version` (`sim/model.py`, `VERSION`). A change that
  older readers cannot understand raises it; a newer Evans refuses a file from a
  newer format with a message, never a silent misread. Additive changes (a new
  block type, a new optional field) do not raise it.
- `.fmdl` keeps opening for good. Only `.evx` is written by default; Save As
  keeps offering `.fmdl` for as long as the format version allows it.
- The `"format"` tag stays as it is.

**2. The console's MATLAB-compatible behaviour.**
- A script that gives MATLAB's answer in 1.x keeps giving it. A change that
  alters a result is a bug fix only when the old result differed from MATLAB's;
  those go in the changelog under *Changed* with the old and new answer (0.13.0
  did this for the Unit Delay).
- New commands and new options may appear in any 1.x. A command that is in the
  help index stays, with its argument order. Where Evans differs from MATLAB on
  purpose, the help page says so, and that difference is part of the promise too.
- Not promised: the exact wording of error messages and warnings, plot
  appearance (colours, fonts, layout), Python-side internals, and anything the
  "Not in Evans" page lists. The Python console features (`evans.*`) are
  best effort until the API is documented.

**3. Saved settings.**
- Settings written by any 1.x are read by every later 1.x. A renamed or removed
  key is migrated on first start, as the settings from before 0.9 were. A setting that can no
  longer be honoured falls back to its default; it never stops Evans starting.
- Autosave recovery folders are not an archive: they are only promised to restore
  across a crash of the same version.

**4. Versioning after 1.0.** Semantic versioning, applied to the things above:
- **Patch (1.0.x):** fixes, including MATLAB-compatibility fixes, and new help.
- **Minor (1.x.0):** new commands, blocks, panes and file-format *additions*.
  Behaviour the policy promises does not change.
- **Major (2.0):** the only place a promise above may break, announced in the
  changelog's *Changed* section one minor release earlier where possible.
- Releases that are tagged but fail CI and never ship (0.12.0, 0.17.0, 0.27.0,
  0.28.0, 0.30.0) keep their changelog entry, marked as not released.

The project file (`.evproj`, Phase 8 R7) and the settings keys Phase 8 introduces fall
under rules 1 and 3 from 1.0, as model files and settings do.

---

## Phase 0 — Silent wrong answers ◐ **Core done 2026-10-27; 2 open**

Tests: `tests/golden/test_confident_liars.py`. The search for more silent wrong
answers became the reference corpus (Phase 6), which found 32; all were fixed
2026-11-18.

- [ ] **Array writes, what is left** (from the in-place writes, 2026-11-11): growing
      (`a(end+1) = v`) still reallocates each time; a fill loop that passes the array
      to a MATLAB function, or to a library function off the owned list, copies once per
      call (correct, but quadratic again); a thread reading the workspace while a loop
      runs could see writes land. **M**
- [ ] **Silent wrong answers found while writing help pages, what is left** (2026-11-24;
      the rest fixed 2026-11-27). Each page describes today's behaviour and must be
      revised when its item is done. **S–M**
      - `ode45` (page `ode45`): the `Events`, `Mass` and `Jacobian` options are not
        supported. Since 2026-11-27 a set option is named in a warning instead of being
        dropped silently; supporting `Events` is a new feature.
      - `fzero` (page `fzero`): `exitflag` is always 1, `TolX` has no effect, `output`
        has only `algorithm`.
      - `struct2table` (page `struct2table`): `s=struct('a',{1,2}); T=struct2table(s);
        istable(T)` gives 0 and `class(T)` is `'double'`; `T.a`, `T.Properties`,
        `table2struct`, `table2cell`, `table2array` and `summary` all fail, and
        `T(1,:)` returns every row. It returns the legacy display-only `Table` class
        (`matlab_runtime.py` about lines 810 and 4102) instead of a `ColumnTable` as
        `table` does (`lib_tables.py`). The `'AsArray'` and `'RowNames'` options fail
        with a Python `TypeError`. **M**

## Phase 1 — Everyday data work at the console ◐ **Core done 2026-10-28; 6 open**

The functions live in `src/evans/console/lib_*.py`, tests in
`tests/golden/test_lib_*.py`.

- [ ] `nextpow2` (listed in *Not in Evans*; `lib_signal.py` has a private `_nextpow2`
      that a console command can wrap). Found 2026-11-24 by the lab-report session, which
      used `2^ceil(log2(N))` instead. A new command, so after the 2026-11-26 hold. **S**

- [ ] A `cftool` curve-fitting GUI over `fit`. **L**
- [ ] `fit` with custom equations (`fittype('a*exp(b*x)')`); refused today. **M**
- [ ] `cellfun`/`arrayfun` with `'ErrorHandler'`; refused today. **S**
- [ ] `rng` seeds the generator, but the streams are not MATLAB's, so `rand` after
      `rng(0)` differs (the verification kit records MATLAB's streams). **M**
- [ ] `cd` lasts one run (noted with the file I/O work). Check against MATLAB, where it
      lasts until changed; R7 touches `cd` and `pwd` too. **S**

## Phase 2 — Simulink for daily use ◐ **Core done 2026-10-30; 28 open**

Tests: `tests/golden/test_sim_workspace.py`, `test_sim_library.py`,
`test_sim_editing.py`.

**Engine and blocks**

- [ ] **Buses,** cut on purpose and to be reconsidered after Goto/From, which is
      done; nobody has reconsidered them yet. Decide, then build or drop. **M**
- [ ] `sim` given a model object returns the Python result, not the
      `SimulationOutput`-like struct that `sim('name')` returns (still so on
      2026-11-19, `lib_sim.f_sim`). *Found 2026-11-23: this is documented (help page
      `sim`) and relied on (`test_console_ui`, `test_sim_workspace`), so changing it
      breaks `r.t` and `r.trace('G')`. Decide first: keep it and say so in the
      "Not in Evans" page, or return the struct and keep the Python attributes on it.* **S**
- [ ] MIMO `linearize`. **M**
- [ ] Live parameter sliders during a run. **M**
- [ ] A user block API (an S-function equivalent). **M**
- [ ] The Fcn / MATLAB Function block: `persistent` gives no memory (it would update at
      every solver stage). **S–M**
- [ ] Memory needs its sample time stated; Simulink's inherits it. **S**
- [ ] Signal Builder takes typed points, not a graph editor. **M**
- [ ] Counter is Counter Limited only (no Counter Free-Running). **S**
- [ ] Data stores allow one writer per store, so a read feeding its own write is
      reported as an algebraic loop. **M**
- [ ] One control port per conditional subsystem (no enabled-and-triggered). **M**
- [ ] **Retry with the obvious fix instead of failing (Excel-style
      correction).** A block parameter that does not parse should be retried
      with the likely repair, the run should go on, and the Model tab should
      say what was changed. Seen 2026-11-18: a Repeating Sequence with
      `0, T_PWM/2, T_PWM` stopped the run with `CompileError ... not a MATLAB
      expression (expected ')', found ',')`; `[0, T_PWM/2, T_PWM]` was meant.
      Start with vector parameters (`kind="vector"`: bare comma or space list
      gets brackets) in `sim/workspace.py`, then see which other errors have
      one clear fix. Keep it narrow: only a repair with a single reading,
      and never one that changes a value. Show the correction in the bottom
      bar or the block's tooltip, and write the corrected text back only if
      the user accepts it, so a saved model stays as typed. A failure with no
      clear fix must still name the block and parameter, as now. Tests next to
      `tests/golden/test_sim_workspace.py`. **S–M**

**Speed.** Profiled 2026-11-27 on the four shipped examples, 10 s of
simulated time each, RK45: `dc_motor` 0.30 s, `cruise_control` 0.36 s,
`inverted_pendulum` 0.56 s, `pid_saturation` 2.95 s. Simulink runs models this
size in tens of milliseconds, so Evans is about 10–100× slower. The maths is
not the cost. Every block evaluation costs about 13 µs whatever the block does,
because each signal is a 1-element numpy array and numpy's ~1 µs per call
dominates: `np.atleast_1d` runs 650k times in one `pid_saturation` run,
`_Evaluator._inputs` (`sim/solver.py`) allocates `np.zeros` on every call,
`PortRef.__hash__` runs 590k times for the `_values` dict, and Saturation's
nested `np.where` costs ~9 µs to clip one number. Fcn blocks cost ~27 µs, since
they go through the full interpreter (`console/matlab_runtime.py`); in the
pendulum the one Fcn block is ~60% of the run. Each of the 2000 output points
is a full diagram sweep, which in the pendulum is most of the run (440 RHS
calls against ~2000 recording sweeps). Cython alone would not help: the cost is
thousands of tiny calls, not slow arithmetic.

- [ ] **Check `pid_saturation`'s 51 solver restarts.** It makes 10,400 RHS
      calls and restarts `solve_ivp` 51 times for a 7-state linear loop with
      one step input, so the fixed-step `ode4` (1.8 s) beats RK45 (2.95 s).
      This looks like chattering at the anti-windup Saturation's zero crossings.
      Find out whether the restarts are real mode changes; if not, it is a bug. **S**
- [ ] **A benchmark to measure against:** `tools/profile_sim.py`, which times
      each example and counts block evaluations, sweeps and solver restarts, so
      every speed change below has a before and after. **S**
- [ ] **Quick wins in plain Python (expect 2–4×).** At compile time, give
      every signal a slot in one flat float array and give each block plan
      the indices of its inputs, so a sweep stops building lists, hashing
      `PortRef`s and allocating zeros. Drop the repeated
      `atleast_1d`/`asarray` where the block contract already guarantees
      arrays, and give scalar signals a float fast path in the hot blocks
      (Sum, Gain, Saturation, PID, TransferFcn, Integrator). Results must not
      change: the sim golden tests and `test_model_compat.py` are the check. **S–M**
- [ ] **Accelerator mode (expect 10–50×).** Compile the flattened diagram
      into one generated function per model: merge the linear blocks into one
      `dx = A @ x + B @ u`, translate Fcn expressions to numpy once instead of
      interpreting them on every step, and run the result under Numba with a
      solver loop that never returns to Python. Blocks that cannot be compiled
      (MATLAB Function, interpreted callbacks) fall back to today's path. Run
      it as a choice in the run settings, as Simulink does, until it matches the
      normal mode on every test. Needs a design pass on *opus* and its own
      session; do the quick wins first. **L**

**Subsystems.** Create Subsystem from Selection, Expand Subsystem, descending into one,
nested and conditional (enabled, triggered, action) subsystems exist
(`sim/blocks/subsystem.py`, `compile.flatten`). Not done:

- [ ] **Masks:** a parameter dialog for a subsystem, with its own variables (`gain`,
      `Ts`) used by the blocks inside, an icon or text on the block, and a
      documentation line. This is what makes a subsystem reusable. **M–L**
- [ ] **Block libraries and linked blocks:** save a subsystem to a library file, drag
      it into other models as a link, update every link when the library changes, and
      break a link. **M–L**
- [ ] **Referenced models** (Model block): run another `.evx` as a block, with its own
      run settings and a normal-mode/accelerated choice. **L**
- [ ] **Insert subsystem from `.evx`** (Leon's idea, 2026-11-11). Build a
      subsystem in its own `.evx` file, then insert it into other models
      (e.g. *Insert ▸ Subsystem from file…*). It arrives **read-only**: it
      runs and can be opened to look inside, but editing it is blocked. The
      first attempt to change it (a parameter, a block, a wire inside) shows
      a popup with two choices:
      - **Modify in place:** the inserted copy becomes this model's own
        subsystem, cut loose from the file, and the edit goes ahead.
      - **Overwrite original `name.evx`:** the edit goes back to the source
        file, so every model that uses it picks it up.

      *Decided 2026-11-11:*
      - **Live link.** A change to the source `.evx` reaches every model
        that uses it the next time that model is opened.
      - **Warn when editing a source.** Opening the source `.evx` itself and
        changing it shows "This model is a subsystem in `name.evx`,
        `name2.evx`, … Are you sure you want to change it?". That needs Evans
        to know who uses a file: keep an index of links (written whenever a
        model with linked subsystems is saved, in app data), since a source
        file cannot know its users by itself. Say "used by models Evans has
        seen" if the list may be incomplete.
      - **Missing source.** The block shows a large, unmistakable "Subsystem
        source missing" error (the model refuses to run), and its
        properties give the full path it was last found at and the file's
        name, so it can be found or relinked.

      Saving the model keeps the link by path, relative to the model where
      possible, as script links will. Show the source file's name on the
      block. This is a simpler,
      file-based take on the two items above (linked library blocks,
      referenced models), so build it with them in mind, or instead of the
      library half. **M–L**
- [ ] **Atomic subsystems** and a subsystem-level sample time, which Simulink has and
      Evans flattens away. **M**
- [ ] **Variant subsystems** and **function-call subsystems.** **M each**
- [ ] **Port handling:** name the ports from the Inport/Outport blocks, reorder them,
      show the names on the block, and keep the wires when a port is added or removed.
      **S–M**
- [ ] **Stable signal names across a subsystem edit** (renaming or moving a block
      inside it keeps the wire names; wire names already pass through flattening since
      2026-11-09). **S**

**Editor and scope**

- [ ] **Automatic block layout that is genuinely good.** Added 2026-11-18 by Leon:
      block placement is one of the biggest complaints of Simulink users, so
      this should be a reason to pick Evans. Today the canvas has only manual
      helpers (`ui/sim/arrange.py`: Fit, Align row, Align column, Space) and a
      wire router (`route` in `ui/sim/items.py`). Wanted:
      - **Arrange model** (one command, one undo step) that lays a diagram out
        the way an engineer would draw it: signal flow left to right, the
        forward path on one straight line, feedback paths routed below it
        and back, sources at the left and sinks (Scope, To Workspace, Out) at
        the right, few wire crossings and few bends, aligned ports so that
        straight wires are straight, even spacing that leaves room for
        labels. A layered (Sugiyama-style) layout with the feedback edges
        reversed is the likely start; judge it on the shipped examples and
        the course models, not on random graphs.
      - **Arrange selection**: the same for selected blocks only, leaving the
        rest where it is.
      - **Gentle placement while editing:** a block added from the palette,
        quick insert (R6) or a dropped wire lands where it belongs next to
        what it connects to, without moving anything the user placed.
      - **Models built without positions** (console `add_block`, code-first
        models, a later `.slx` import) get a good layout automatically.
      - Subsystems are laid out per level; their port order follows the
        layout.
      Must never move a block the user has pinned or placed unless they asked
      for an arrange. Tests: crossings, bends and overlap counts on the
      examples (no overlaps, no more crossings than a hand-drawn reference),
      and stability (arranging twice changes nothing). Worth a design pass on
      *opus* first; it touches `sim/model.py` positions, `ui/sim/canvas.py`
      and the router. **L**
- [ ] **Scope scaling** (`ui/sim/scope.py`): manual and auto axis limits, a
      per-channel offset/scale, log axes, linked time axes across scopes, zoom to a
      box, and a "fit" and "reset" button. **M**
- [ ] **Scope look:** line width, colour and style per channel, markers, legend
      position, grid, and a title, saved in the model like Simulink's scope settings.
      Plain measurement readouts (cursors with a delta between two, min/max/mean/
      peak-to-peak over a time range). **M**
- [ ] **Scope hand-off to the console:** send the plotted channels to the workspace as
      a `timeseries` or struct, and "open as a figure" to continue editing it with
      console plot commands. **S–M**

## Phase 3 — Plotting ◐ **Core done 2026-11-03; 6 open**

Plot functions: `console/lib_plot.py`; 2-D drawn by pyqtgraph
(`ui/console/figure_view.py`), 3-D, pies, PDF/EPS by matplotlib
(`console/figure_mpl.py`). Tests: `tests/golden/test_lib_plot.py`, `test_plot_ui.py`.

- [ ] Handle graphics: `h = plot(...)` and `set(h, …)`/`h.Color = …`,
      `cb.Label.String`. Every plot function returns nothing useful (`h = plot(1:3)` is a
      `double` on 2026-11-19); properties go in as name-value pairs. **L**
- [ ] `imread`, into `uint8` arrays. **S**
- [ ] Nichols plot in the analysis tabs (`ui/tabs/frequency_tab.py`): a **K sweep**
      option (vary the loop gain and watch the curve shift up and down) and a **show
      M-circles** option on the Nichols view. Added 2026-11-13. **S–M** *Found
      2026-11-19:* the Frequency tab's "M-circles / M-contours" checkbox, on the Nyquist
      sub-tab, already draws the M-contours on the Nichols chart as well; what is left is
      a control on the Nichols view itself and the K sweep. (The Design tab's Gain view
      has *Set K for peak of T*, 0.29.1, and the console has `mtune`, 0.29.0.)
- [ ] `[az, el] = view` does not read the mouse's angle back on 3-D axes. **S**
- [ ] `legend` honours only the four corners of `'Location'`. **S**
- [ ] **TeX text in labels.** MATLAB's default text interpreter is `'tex'`, so
      `ylabel('\alpha (rad)')` shows a Greek α and `legend('\alpha_c')` a subscript c.
      Evans prints the string as typed, in both the saved figures
      (`console/figure_mpl.py`: titles, axis labels, legend, `_Painter._text`) and the
      on-screen ones (`ui/console/figure_view.py`; not yet checked). Needs one TeX
      subset to matplotlib-mathtext translator (`\alpha`…, `_x`, `^x`, `\it`, `\bf`)
      shared by both paths, and the `'Interpreter'` option (`'tex'`, `'latex'`, `'none'`).
      Found 2026-11-24 by the lab-report session (workaround: plain-text labels).
      A fix to the output of existing commands, but it touches both renderers, so the
      2026-11-26 hold applies until Leon says it is a bug fix. **M**

## Phase 4 — Running other people's MATLAB code ◐ **Core done 2026-11-09; 14 open**

Everything planned here was built 2026-11-09 to 2026-11-11 (history, part 4). These
are the parts the done items left out. Names that are simply missing are listed on the
"Not in Evans" help page (`console/matlab_names.py`), and the corpus's list is in
Phase 6.

- [ ] `eval` inside a function reads variables but cannot set them, and `evalin` takes
      `'base'` only (the verification kit needs both). **M**
- [ ] `nargin(fn)` is not reachable inside a function, where `nargin` is the call's own
      count. **S**
- [ ] `run('file.m')`, including scripts named with dots (`C.3.2.m`). **S**
- [ ] Integer types: `typecast` (also in the corpus list, Phase 6), integer-valued `containers.Map` keys (still stored as
      doubles), integer N-D arrays. **S–M**
- [ ] `containers.Map`: `copy`, `Map` arrays, key types other than text and double. **S**
- [ ] Tables and dates: time zones, `categorical` (also in the corpus list), `stack`/`unstack`,
      `retime`/`synchronize`, matrix-valued variables, `fitlm` interactions, a
      datetime's two-line display, `plot` of a datetime axis. **L**
- [ ] String arrays: assigning into one keeps cell rules; `missing`, `<missing>` and
      `strings(n)`; string `.^`/`*` errors only name the operator. **S–M**
- [ ] N-D arrays: most functions outside the list built for N-D see the `A(:,:)` view.
      **M**
- [ ] `classdef`: arrays of objects, `subsref`/`subsasgn`, property validation,
      `dynamicprops`, `@Class` and `+pkg` folders. **L**
- [ ] Sparse: function handles as `A` in the iterative solvers and `eigs`; `lsqr`,
      `ilu`, `ichol`. **M**
- [ ] `.mat` v7.3: tables, function handles and classes in a MATLAB-written file are
      skipped with a warning. **M**
- [ ] Open the `.mat` v7.3 files and `.mlx` files Evans writes in MATLAB itself; both
      writers follow MATLAB's documented layout and are untested there (the
      verification kit covers both, Phase 6). **S**
- [ ] `msgbox` waits until closed, unlike MATLAB's. **S**
- [ ] **Crashes and raw Python errors found while writing help pages** (2026-11-24,
      batch 1; nothing fixed). Pages describe today's behaviour and must be revised
      when each is fixed. **S–M**
      - `[A,B,C,D] = butter(2,0.2)` (pages `butter`, `cheby1`, `ellip`): `ValueError:
        'ss' is not a valid output form`, expected the state-space matrices. Cause:
        `_iir` passes `output='ss'` to scipy; go through `zpk` and `zpk2ss`.
      - `save` of a string, function handle or table (page `save`): says "Variable 'f'
        not found." instead of that the type cannot be saved.
      - Missing arguments give Python errors instead of "Not enough input arguments":
        `fft()`, `freqz()`, `findpeaks()`, `butter(2)`, `ode45(f,[0 1])`, `fzero(f)`,
        `fminsearch(f)` (pages of the same names). `fft('a')` shows a numpy
        `DTypePromotionError`; `filter(1,[1 -0.5],[1 2 3],[1 2])` shows `ValueError:
        Unexpected shape for zi` (page `filter`); `fzero(@(x) x^2+1, 1)` shows
        `(34, 'Result too large')` (page `fzero`).
      - Batch 2 (pages `cd`, `all`, `ceil`, `log10`, `log2`, `gt`, `addpath`):
        `cd ..` and `cd .` as commands fail with "unexpected text after the statement";
        `all(x,'all')` and a text `dim` fail with `ValueError: invalid literal for
        int()`, and a fractional `dim` is accepted; `ceil` of char, string or complex
        input, `log10('a')` and `log2('a')` show a numpy `TypeError`; `ceil({1})`,
        `log10({1})` and `gt({1},{2})` return a number instead of an error;
        `gt(2+3i,1)` and `gt(1+3i,1+2i)` raise a Python `TypeError`; `gt([1 2 3],[1 2])`
        gives numpy's broadcast message instead of "Arrays have incompatible sizes for
        this operation."; wrong argument counts (`log10(1,2)`, `gt(1)`, `ceil(1,2)`,
        `cd('a','b')`, `pwd(1)`) give Python errors; `class(log10(single(100)))` is
        `'double'`; `addpath` silently ignores a folder that does not exist, a cell
        array and a number; `genpath`, `path`, `pathsep`, `tempdir` and `tempname`
        are not there.
      - A variable assigned and then cleared in the same command or script
        (page `nan`): `x = 1; clear x; x` and `pi = 3; clear pi; pi` fail with
        `NameError: name 'x' is not defined`, expected "Unrecognized function or
        variable 'x'." and `3.1416`. The translator reads a name the script assigns
        as a plain Python name, so `clear` leaves it undefined; separate commands
        work. Found 2026-11-27 (the roadmap had it as a lost constant).

## Phase 5 — Hardware, identification, symbolic leftovers ○ **Not started; 4 open**

These cover a large share of private use (Arduino, motors, drones) and of small-firm control
work.

- [ ] `serialport`, `readline`, `write`, `flush`, `configureTerminator` over pyserial
      (a new dependency), with a live-plot recipe. **S–M**
- [ ] System identification from measured data to a model and then to `pidtune`:
      `iddata`, `tfest`, `arx`, `ssest`, `compare`, `procest`. Start with `tfest`
      from step and frequency data by least squares. **M** for that, **L** for the
      rest.
- [ ] Symbolic: `dsolve` and symbolic functions (`syms y(t)`), `ztrans`/`iztrans`,
      `fourier`/`ifourier`. Symbolic functions are the hard part. **M**
- [ ] Simulink hardware blocks (serial in/out) and real-time pacing of a run. **L**

## Phase 6 — Platform and trust ◐ **Core done 2026-11-11; 15 open**

**Distribution** (see the 1.0 decisions above)

- [ ] A Linux build (AppImage or a `.deb`). CI already tests on Ubuntu. **M**
      *Decided 2026-11-11: not for 1.0.*
- [ ] macOS notarisation, and an Intel build if anyone asks. **M** *Decided 2026-11-11:
      not for 1.0.*
- [ ] Windows code signing through the SignPath Foundation (free only, decided
      2026-11-11): Leon applies, then wire it into CI. If declined, stay unsigned. **S–M**
- [ ] Mac self-update: a helper that waits for Evans to quit, swaps the `.app` and
      relaunches. Needs notarisation first (with CI's ad hoc signature Gatekeeper
      quarantines a downloaded replacement). Order: notarisation, then the helper, then
      the `.dmg` checksum check. **M**

**Autosave leftovers** (`ui/recovery.py`)

- [ ] Recovery does not cover the workspace (a `save` of it can be large and not every
      value can be written), does not copy on an edit pause (only on the timer), and the
      dialog cannot restore the earlier model copies it keeps. **M**

**The MATLAB reference corpus.** `tools/matlab_reference/evans_reference.mat` holds
MATLAB R2023a's answers to the 496 probes in `evans_reference.m`; 424 of 492 usable
probes agreed on 2026-11-14 and the 32 silent wrong answers among the rest were fixed
2026-11-18 (history, part 4).

- [ ] **The checker:** a test under `tests/golden/` that skips when
      `evans_reference.mat` is not on the machine (the file is not in git), and
      otherwise replays every
      probe in a fresh `Interpreter`, compares class, size and value
      (cells, structs and strings included; MATLAB saves whole-number
      doubles as small integer types, so cast by the recorded `cls`), and
      keeps a list of known differences by probe id that may only shrink.
      A probe that starts matching fails the test until it leaves the
      list. **M**
- [ ] **Record again at the school computer:** probes 472, 476, 477 with
      MOSEK off the path (check with `which quadprog`); `filtfilt` (460)
      and `decimate` (470) with longer inputs, since MATLAB rejected the
      short ones; and run `which sum` to rule out a shadowing `sum` on that
      machine (the integer `sum`/`prod` fix of 2026-11-18 was settled from the
      recording; history, part 4). **S**
      *2026-11-14: kit built, waiting to be run.* One run covers all of
      this and much more: `tools/matlab_reference/verif/build_verif.py`
      writes `~/Desktop/EvansVerif` (README inside; `run_evans_verify`,
      hours, resumable, skips anything that hangs, takes everything
      outside matlabroot off the path, ends in `EvansVerif_results.zip`).
      It records ~34,700 probe groups (the 496 above, follow-ups to all
      68 differences, every help-page example, ~1,400 snippets harvested
      from `tests/`, and grids: elementwise functions x inputs, class
      combination table, reductions x dims/flags, sprintf/num2str/display
      formats, text functions, 35 systems x ~100 control calls, signal,
      optimisation/ODE, dates/tables/JSON, files on fixtures, plots with
      axes limits/ticks and PNGs, rng streams), each step's printed text,
      error id/message, warning and every variable it changed; `which
      -all`/nargin for ~1,200 names; 102 Simulink models (every block
      type, solver settings, conditional subsystems, the examples) saved
      as .slx/.mdl with logged signals and library block defaults; .mat
      in v4/v6/v7/v7.3 both ways and .mlx both ways. The Evans side of
      each Simulink case is in `verif/built/cases_evans.json`. A
      self-check at the start falls back to a simpler recorder if the
      main one misbehaves on that MATLAB. Not testable here beyond a dry
      run inside Evans (no MATLAB on this machine).
      *Decided 2026-11-20:* `evans_reference.mat` and the whole `verif/` folder stay
      local and out of git (recordings from an academic MATLAB licence); both are in
      `.gitignore`. Back them up yourself, since git no longer holds them.
- [ ] **Tolerances, not fixes (3):** `margin` (419), `stepinfo` (422) and
      `ode45` (378) differ by 0.1–1% because MATLAB's own answers are
      approximate (Evans's gain margin is the exact 8, MATLAB's 8.0011).
      The checker gives these probes a looser tolerance. **S**
- [ ] **MATLAB answers, Evans raises an error (32).** **M** *(A different 32 from
      the silent wrong answers, which were all fixed 2026-11-18: of the 68
      differences, 32 were silent wrong answers, 32 are these, 3 are the tolerances
      below, and 1 is `single(1) + int8(1)`.)*
      - Missing functions: `xor`, `rot90`, `typecast`, `complex`,
        `ismatrix`, `strtok`, `setdiff`, `intersect`, `union`, `normest`,
        `covar`, `categorical`.
      - Missing outputs: `[r, c] = find(...)`, `[u, i, j] = unique(...)`.
      - Python errors reaching the user: `'abc' + 1`, `fliplr('abc')`,
        `str2num('[1 2 3]')`, `str2double('abc')` (should be NaN),
        `str2double` of a cell, `mean(A, 'all')`, `norm(tf, 2)` and
        `norm(tf, Inf)`, `zeros(3,0) * zeros(0,2)`.
      - Signatures MATLAB accepts: `ss2tf(A, B, C, D)`, `tf2ss(num, den)`,
        `lqr(A, B, Q, R)`, `weekday` of a `datenum`, `zeros(2, 'logical')`,
        `allmargin`'s field names (`GainMargin`, …), `s(2).x = 1` on
        `struct()`.
      - Time delays (`'InputDelay'`, `'OutputDelay'`): a known gap.
- [ ] **Evans should raise an error:** `single(1) + int8(1)` (62). **S**
- [ ] **Char matrices, what is left** (from the silent-wrong-answers fixes,
      2026-11-18): `char(a, b)` (raises a Python `TypeError` on 2026-11-19), `strvcat`,
      and char matrices inside other functions. **S–M**
- [ ] **Found while dry-running the kit inside Evans (2026-11-14).** The harness is
      ordinary MATLAB, and Evans could not run it: **M**
      - Missing: `mfilename`, `tempdir`, `filesep`, `setappdata`/`getappdata`,
        `onCleanup`, `evalc`, `assignin`, `lastwarn`, `getReport`, `path`/`pathsep`,
        `matlabroot`, `zip`, `findall`, `allchild`, `version`, `ver` (and `setdiff`,
        above).
      - `evalin` beyond `'base'` and `eval` assigning inside a function (Phase 4).
      - `save` inside a function does not see the function's variables
        ("Variable 'recs' not found").
      - `toc(t0)` as an argument fails ("got multiple values for argument
        'nargout'").
      - `[c{:}]` over a cell of structs gives a cell, not a struct array.
      - `fread(fid, Inf, '*uint8')` is refused.
      - `d.bytes / 1e6` on an empty `dir` result raises a Python error.
      - `save` of a string, function handle, table, datetime, duration,
        map or LTI model fails with "Variable 'x' not found" instead of
        saying the type cannot be saved (`verif/built/interop_build_report.json`).

**Help coverage**

- [ ] Help pages for the remaining callable names (216 on 2026-11-24) that have none (found 2026-11-24 by
      comparing the runtime's `f_*` methods and `api._GROUPS` with `help.topics()`):
      rank 1, 25 names the site or README advertises (`fft`, `filter`, `butter`,
      `ode45`, `fzero`, `save`, `load`, `cd`, `pwd`, `addpath`, `findpeaks`…); rank 2,
      116 course and teaching staples (elementary maths, types and tests, errors,
      strings, filters, ODE and optimisation, control plots); rank 3, 75 others
      (operator forms, colormaps, constants, dates). Full ranked list by category in
      [`docs/HELP_GAPS.md`](HELP_GAPS.md) (released as 0.30.4). Docs only, in batches of 15, each page verified by running
      its example. **M** *Batches 1 and 2 done 2026-11-24: all 25 rank-1 pages (batch 1: `fft`, `ifft`,
      `filter`, `freqz`, `findpeaks`, `butter`, `cheby1`, `ellip`, `interp1`, `trapz`,
      `ode45`, `fzero`, `fminsearch`, `save`, `load`; batch 2: `cd`, `pwd`, `addpath`,
      `all`, `ceil`, `log10`, `log2`, `gt`, `nan`, `struct2table`). 191 names left:
      rank 2, 116; rank 3, 75.*

**Tools**

- [ ] A profiler (`profile on/off/viewer`), `publish` for plain `.m` files to HTML/PDF,
      and git status in the file browser. **M each**
- [ ] The `B905` audit (`zip(..., strict=True)`, switched off in `pyproject.toml`): a
      per-site check of about fifteen calls, mostly in the solver, where a length
      mismatch between ports and widths would be a real bug. **S**

## Phase 7 — Scope decisions before any large build ○ **Nothing decided; 7 open**

Each of these is a project of its own. Decide whether each is in scope before starting
it.

- [ ] **Physical (acausal) modelling.** This is the one large gap that keeps the Model tab
      from replacing Simulink at work. Options: embed OpenModelica through FMI, write
      a small Simscape-like electrical/mechanical library on the existing DAE
      solver, or leave it out and say so. **L**
- [ ] **FMU import/export (FMI 2/3).** FMU import would let Modelica plants run on the
      canvas. **L**
- [ ] **`.slx`/`.mdl` import.** Even a partial import of the common blocks would let
      a colleague's model open. Its PreLoadFcn/InitFcn callbacks map onto model
      scripts (Phase 2) when they only call scripts. **L**
- [ ] **Code-first models** (`m = Model(); m.add(…)`), round-tripping with the canvas
      (from the v2 plan's backlog, after bdsim). **M–L**
- [ ] **A browser build** through Pyodide: the Qt-free core in a web page, nothing to
      install (from the v2 plan's backlog). **L**
- [ ] **Stateflow-like state machines, code generation, MPC, H∞/μ, an App
      Designer equivalent.** Likely out of scope for the target users; recorded so
      the decision is explicit. **L each**
- [ ] **An extension mechanism:** user toolboxes on the path, and a place to share
      them. **L**

## Phase 8 — Interface rework before 1.0 ◐ **R0 to R6d done; 5 open (R7, R8, R9 and two leftovers); blocks 1.0**

Planned 2026-11-16 from a UI audit and two rounds of decisions with Leon; the audit
and the finished packages R0 to R6c, with the decisions taken while building them, are
in `docs/HISTORY.md`, part 6. What the audit found and is still open: no start screen
(R8), and nothing ties a model, its scripts and its figures together on disk (R7). The
packages are written for a coding agent that has not seen the discussion, so they spell
out behaviour, files, traps and tests. **Read 8.1 and 8.2 before any package.**

### 8.1 Decisions (Leon, 2026-11-16). Do not reopen these in a coding session.

1. **Analyse, Model and Console stay three separate workspaces** on the rail, so each
   stays uncrowded on a laptop. No merged single shell.
2. **Every workspace gets one right-hand side panel with tabs, and Cedric is always
   its last tab.** Analyse: *Loop · Design · Cedric*. Model: *Properties · Cedric*.
   Console: *Workspace · History · Cedric*.
3. **The loop editor moves from the left dock into the Analyse side panel** as the
   *Loop* tab, and is called "Loop" everywhere. "Model" means only the block-diagram
   workspace.
4. **The Apps menu is deleted.** Control System Designer and PID Tuner become the
   *Design* tab. **LTI Viewer dissolves into the panes**: a plot pane can show several
   systems. `ltiview`, `sisotool` and `pidtuner` typed at the console keep working.
5. **Fewer menus.** The menu bar becomes File · Edit · View · Help.
6. **Stability lamp and margins move to the bottom bar.** The bottom bar is
   per-workspace: Analyse shows the lamp and PM/GM/ωc, Model shows solver and file
   status (it does already), Console shows idle or running.
7. **Search (command palette) is context-sensitive by ranking, not by filtering:** the
   current workspace's actions first, then global ones, then a "Go to" section for the
   other workspaces' actions, which switch workspace when picked.
8. **Scope:** opening in its own window stays the default. Add a Dock/Undock button on
   the scope and a preference for which is the default.
9. **Projects are folders** of ordinary files (models, scripts, figures, data) with a
   small project file. Built **before 1.0**. Working without a project stays possible.
10. **Design system is untouched:** colours, shapes and fonts come from `ui/theme.py`
    and `ui/design.py` (the Holding Point system). No new colours, no rounded corners,
    no gradients.

Still open, ask Leon before building (none of them blocks packages R0 to R9):

- The project file's extension. This plan uses `.evproj`; Leon may prefer another.
- Whether the script editor should sit above the command window instead of on its own
  tab. Not in this phase.
- Removing the *Compute* buttons on the Time and Frequency workflow panes so they
  update live. Not in this phase.
- Requirement regions (overshoot, settling time) shaded on the panes. After 1.0.
- Dragging poles and zeros directly on the pane grid's root locus and Bode. After
  1.0; until then the Design tab keeps its own small root locus as the drag surface.

### 8.2 Rules for every package

- **One package per session, one at a time,** in the order below unless a package
  says it can run beside another. Each ends with: the area's tests, `ruff check .`,
  then the full suite once in the background (`python -m pytest`, about 26 minutes),
  then a commit. Tick the package here and add what was found under it.
- **Model to use** is named per package (see the `model-routing` skill): *sonnet* for
  a clear spec, *opus* where structure or judgement is involved, *haiku* for searches.
- **Read first:** `docs/CODEMAP.md`, then only the files the package names.
  `ui/mainwindow.py` (1,550 lines) is searched, not read whole; the method names
  given below are grep targets.
- **Qt tests run offscreen** and fail at once on a modal dialog nobody answers
  (`tests/conftest.py`). Anything that asks the user goes through a small method the
  tests can patch, as `MainWindow._ask_theme_restart` does.
- **Persisted settings** go through `ui/persist.py` (one getter and one setter per
  key, the pattern already there). A renamed key is migrated on first start, never
  just dropped (stability policy rule 3, in the 1.0 section above). Window layout keys live
  in `MainWindow._settings()` and are cleared by *Reset layout*; preferences live in
  `persist.settings()` and are not.
- **`saveState` version.** R2 removes docks. From R2 on call
  `self.saveState(2)` and `self.restoreState(state, 2)` so a layout saved by an older
  build is ignored instead of half-applied.
- **Text and shortcuts:** sentence case, no emoji and no pictogram characters in
  labels (a test enforces it), every shortcut shown through `keys.label(...)` so a Mac
  sees ⌘. Give every new control an accessible name.
- **Colours and spacing** only from `theme.tokens()` and the constants in
  `ui/design.py` (`TIGHT`, `NORMAL`, `SECTION`, `PANEL`). Panels that compute use
  `GuardedPanel` (`ui/guard.py`) so an error shows as a banner, not a traceback.
- **Known traps** (from the UI redesign, `docs/HISTORY.md` part 3): a `str`-mixin enum comes back from
  `QComboBox.currentData()` as a plain `str`; a widget lives in one parent only;
  word-wrapped text gets taller as it gets narrower, so new side-panel content goes
  in a `QScrollArea`; a test that changes the shared window must put it back (see the
  reset fixture in `tests/golden/test_ui_layout.py`).
- **Minimum window size must not grow.** `tests/golden/test_ui_layout.py` asserts the
  budget (the window must fit 1280×720). Run it after every layout change.
- **Never hold a stale `CourseArchitecture`.** `MainWindow._new_session` shows every
  holder that must be handed the new one.
- **Tests that will need updating** as docks and menu actions go: `tests/golden/`
  `test_apps.py`, `test_apps_ui.py`, `test_cedric_ui.py`, `test_ui_layout.py`,
  `test_title_bar.py`, `test_block_shapes.py`, `test_lib_files.py`, and
  `tests/test_theme.py`. Update a test to the new behaviour; never delete one to get
  green, and say in the commit which assertions changed and why.
- **Docs travel with the code:** a changed command behaviour updates its help page
  (`src/evans/help/pages/`), and `docs/CODEMAP.md` gets a line for any new package.
  The README's counts are asserted by `tests/golden/test_packaging.py`.

### 8.3 Packages

Order: R7 → R8 → R9 (R6d, added 2026-11-19 after R6c, is done: `docs/HISTORY.md`, part 6).

- [ ] **R7 — Projects as folders.** *opus for the core and the decisions, sonnet for
  the rest.* **L** Needs R4.
  - **What a project is.** A folder containing one project file,
    `<name>.evproj`, and ordinary files. *New project* creates:
    ```
    MyProject/
      MyProject.evproj
      loop.json        the Analyse loop (core/session.py's session dict)
      models/          .evx block diagrams
      scripts/         .m and .mlx
      figures/         exported figures
      data/            .mat, .csv
    ```
    Only the project file and `loop.json` are required; the subfolders are a
    starting layout, and files anywhere in the folder belong to the project.
    The project file is JSON:
    `{"format": "evans-project", "version": 1, "name": "MyProject",
      "loop": "loop.json"}` and nothing else. Window state, open tabs and the like
    are **not** stored in it (they would make every project dirty in git); they go
    in `QSettings` under `projects/<key>/...`, where `<key>` is the same path key
    `persist._key(path)` builds for recent files.
  - **Qt-free core, `evans/project.py`** (top-level module, so no new package and
    no CODEMAP package line; add it to the "Where to look for" list instead):
    `Project` dataclass (`root: Path`, `name`, `loop_file`), `create(folder, name)
    -> Project` (refuses a folder that already holds a `.evproj`, creates the
    layout, writes a default loop), `load(path) -> Project` (accepts the folder or
    the `.evproj`; a newer `version` is refused with a message naming both
    versions, as `sim/model.py` does for models; unknown keys are kept on save),
    `save(project)`, `find(path) -> Path | None` (walks up from a file to the
    nearest folder holding a `.evproj`), `files(project) -> list[Path]` (models,
    scripts, live scripts, data and figures, skipping dot-folders, `__pycache__`
    and anything over 5,000 entries). Writes go through a `.part` file swapped in,
    as model saves do. Tests in `tests/test_project.py`, with a frozen fixture
    project under `tests/fixtures/projects/v1/` that must keep loading (same rule
    as the model fixtures).
  - **Opening a project** (`MainWindow.open_project(path)`): settle unsaved work
    first (`confirm_quit`'s helpers: `_settle_model`, `_settle_live`, the script
    tabs); load `loop.json` into the architecture through `change_loop` and clear
    the loop undo stack; set the console's folder to the project root and put
    `scripts/` on its search path (the runtime's `folder` and `path`,
    `console/matlab_runtime.py` around `self.path`; `MainWindow._build_console`
    shows how they are read); reopen what this project had open last time (scripts,
    the model, the workspace, pane layout) from `projects/<key>/...`; set the
    window title to "<name> — Evans"; add the project to recent files.
    `open_recent` and the file-drop handler route a `.evproj` or a folder holding
    one here.
  - **Closing and saving.** With a project open, Save on Analyse writes
    `loop.json` in place without asking (and marks the loop saved); Save as…
    still exports a copy anywhere. File dialogs for models, scripts, figures and
    data start in the matching subfolder if it exists. On quit and on
    *Close project* the per-project window state is written.
  - **A loop "unsaved" mark.** There is none today. Keep the session dict written
    at the last save or load and compare (the same idea as `SimTab.mark_saved` /
    `is_unsaved`); show `●` after the project name in the title while the loop
    differs, and include the loop in `confirm_quit` when a project is open.
    Without a project the loop is scratch and is never asked about, as now.
  - **Files tab.** The Console side panel gains a first tab **Files** (a
    `QTreeView` over `QFileSystemModel` rooted at the project folder, name column
    only, dot-folders hidden); on Model and Analyse there is no Files tab (the
    palette and R8's Start page reach files from there). Double-click opens a file
    where it belongs (`open_recent`). Context menu: Open, Reveal in the file
    manager, Rename, Delete (to the recycle bin where the platform has one; ask
    first), New script, New model, New folder. With no project open the tab shows
    an empty state: "No project open" and a *New project…* and an *Open
    project…* button.
  - **File menu:** New ▸ Project…, Script, Model, Loop; Open project…; Close
    project. The palette (R5) lists the project's files under a "Project" section.
  - **Without a project** everything behaves as before this package. Old session
    `.json` files keep opening through Open… on Analyse.
  - **Console commands:** `cd`, `pwd` and relative paths in `load`, `save`,
    `open_system` must agree with the project root; test `open_system('name')`
    finds `models/name.evx` (see `find_model_file` in `sim/model.py`; add the
    project's `models/` to where it looks).
  - **Installer and bundle:** register `.evproj` beside `.evx`
    (`packaging/evans.iss`, task `modelassoc`; the macOS bundle's document types in
    `packaging/evans.spec`), and make `app.py`'s file arguments and the macOS
    FileOpen handler (`_file_arguments`, `_finder_files` in `evans/app.py`) open
    it.
  - **Recovery:** `ui/recovery.py` already saves unsaved scripts and the model;
    add the loop when a project is open.
  - Tests (`tests/golden/test_project_ui.py`): create, close, reopen restores the
    loop, the open script and the workspace; Save on Analyse writes `loop.json`;
    the unsaved mark; opening a project with unsaved work asks; a file dropped on
    the window; `open_system` by name; the fixture project loads.

- [ ] **R8 — Start page.** *sonnet.* **M** Needs R7.
  - **Where it lives.** A fourth page in the `WorkspaceStack`, reached from a
    **Start** button at the top of the rail (house icon; add `workspace-start` to
    `ui/iconset.py`'s SVGs) with shortcut Ctrl+0. Implement it by adding
    `START = "Start"` as the **first** member of `Workspace` and replacing the
    index arithmetic in `Workspace.shortcut` with an explicit table (Start Ctrl+0,
    Analyse Ctrl+1, Model Ctrl+2, Console Ctrl+3). Then grep for every
    `list(Workspace)`, `for ... in Workspace` and `Workspace(saved)` and check each
    (the rail builds buttons in enum order, which is what is wanted; the View menu
    lists them; `restore_layout` reads a saved name). Start has no side panel, no
    undo stack and an empty bottom bar.
  - **Content** (`ui/start_page.py`), one scrollable column, at most 880 px wide,
    centred:
    - a title row: the Evans plate and the version (`evans.__version__`, read, not
      copied);
    - **Begin with a transfer function:** two fields, numerator and denominator
      (the same parser the Loop tab's block editor uses in *Coefficients* mode),
      and an *Analyse* button that sets G through `change_loop` and goes to
      Analyse. A parse error shows under the field in the hold colour, saying what
      is wrong and giving an example (`1` and `1 2 4`);
    - **Projects:** *New project…*, *Open project…*, then up to eight recent
      projects (name, folder in the muted colour, a mark if the folder is gone);
    - **Recent files:** up to eight models and scripts (`RecentFiles`);
    - **Examples:** one card per example model (`evans.examples.examples()`):
      title, the one-line summary, and a small picture of the diagram. Render the
      picture once per example with the canvas's existing diagram export
      (`ui/sim/export.py`) into a `QPixmap` at 240×120 in the current theme, cached
      in memory; if rendering fails show the card without a picture. Clicking
      opens the example as *File ▸ Examples* does (`open_example`);
    - **Preset plants:** the seven presets as a row of buttons; each loads the
      plant and goes to Analyse;
    - a line of links: Documentation, Keyboard shortcuts, What is new (the
      changelog's section for this version).
    Cards are rectangles with the 2 px frame; nothing floats, nothing is centred
    except the column itself. It must fit 1280×720 without horizontal scrolling
    and stack to one column under 900 px.
  - **Turn the *On launch* preference back on:** it is hidden until this package
    (`ui/preferences.py`, `SHOW_STARTUP_CHOICE = False`, set 2026-11-19 for the
    0.28.0 release); set it to True and drop the test that asserts it is hidden.
  - **When it shows.** At launch: if `startup/show` is `start` (default), or
    nothing was open last time, show Start; with `reopen`, reopen the last project
    or the last workspace. Files given on the command line skip it.
    `evans/app.py` decides after `restore_layout`.
  - Tests (`tests/golden/test_start_ui.py`): a valid and an invalid transfer
    function; every example card opens its example; a missing recent project is
    marked and removed when clicked; Ctrl+0 to Ctrl+3; the startup preference both
    ways; `tests/test_startup_budget.py` still inside its budget (render the
    example pictures lazily, after the window is shown, if it is not).

- [ ] **R9 — Hardening, documentation, release.** *sonnet; haiku for the sweeps.* **M**
  - **Hand check on a real screen,** Windows first, Day and Night, at 1280×720 and
    at 150 % scaling. Walk this list and write what was seen under this item:
    every workspace with its side panel open on each tab; Cedric's conversation
    survives two workspace switches; drag the gain slider and the locus target
    (panes follow, one undo step); undo and redo across a preset, a snapshot and a
    console change; Ctrl+K on each workspace; quick insert all three ways; scope
    dock and undock during and after a run; create a project, quit, reopen; drop a
    `.evx`, a `.m` and a project folder on the window; every Preferences control;
    Tab reaches every control of the side panels, the palette and the Start page,
    with a visible focus frame; the glyphs from R0. Also the by-eye checks the
    finished packages left that Leon's reviews of R2 to R6 (2026-11-18 and
    2026-11-19) did not cover: the run lock on a long run of a heavy model, and a
    stiff solver, in the real window (R6d); the Docs button under the shrimp (R2); the Live
    toolbar's overflow arrow at narrow widths (R2); dragging a side panel wider,
    then closing and reopening it (R2); the Design tab at the panel's 240 px
    minimum, where the Gain page may scroll sideways (R3); the Compare menus and
    their legends in a small pane, and the shortened pane-header combos at 1280 px
    (R3); the context bar going from one line to two as the window narrows, and
    Ctrl+, and Ctrl+Shift+E from each workspace (R4); the quick-insert popup near
    the view's edges and with the mouse outside the canvas, and docking a scope
    with curves on screen, then widening the panel (R6); the vertical Properties
    tab on a short canvas (R6b); the search field beside the menus at 1280 px and
    while the window is dragged narrow, its opening animation, and a click on the
    field and on the open palette over the caption (R6c).
  - **Contrast and colour.** Measure text contrast for `ink_muted` on `ground` and
    on `surface` in both themes (target 4.5:1) and the plot line colours against
    the plot background (3:1); check that curves in a Compare set differ by line
    style as well as colour. Fix in `ui/theme.py` only with Leon's agreement,
    since it is the design system. *Measured 2026-11-23:* text passes everywhere
    (`ink_muted` 6.7 to 7.8:1 on both grounds in both themes). Plot lines on the
    plot background pass except **Day's highlight amber `#b8900a`, 2.73:1** (target
    3:1); a darker amber (about `#a17f09`) would clear it. Curves 1 to 5 of a
    Compare set differ by colour only; the dash style starts at the sixth
    (`plots.STYLES`). Both are Leon's call.
  - **Sweep for leftovers** (done 2026-11-23, nothing to change): "Model panel",
    "Edit model", "Apply as K", "Apply to Architecture" and "Send to analysis" no
    longer appear in `src/`, `site/`, `README.md`, the help pages or docstrings.
    "LTI Viewer" is the `ltiview` app's name and "Apps" a command-index group, both
    meant; "session" means a console session or a recovery session, as intended.
    Run it again before the release in case a package adds strings.
  - **Documentation:** the site's pages that describe the window (screens,
    workflow, shortcuts), a new page on projects, the README's description of the
    interface and any count it states (`tests/golden/test_packaging.py`),
    `docs/CODEMAP.md` (new modules under "Where to look for"), Phase 8's finished
    packages moved to `docs/HISTORY.md` part 6 (as R0 to R6c were), and new screenshots
    (`docs/theme-day.png`, `docs/theme-night.png`, the site's).
  - **Release notes:** a section in `CHANGELOG.md` and in
    `site/pages/patch-notes.html` (`tests/test_changelog.py`). The 0.28.0 notes
    already told a returning user where the three apps went, the new menu layout,
    the moved shortcuts and Cedric on every workspace; this section adds what came
    after: projects, the Start page (Ctrl+0) and R6d.
  - **The stability policy:** check that its line on the project file and the new
    settings keys (the 1.0 section above, written 2026-11-19 in place of adding
    this phase to the old 1.0 proposal) still matches what R7 built.

**Left over from earlier UI work** (not packages; batch them with R9 or before):

- [ ] **The classic analysis tabs onto the shared design system** (`ui/tabs/*.py` still
      style themselves; `ui/design.py`'s primitives are used by everything newer). The
      last item of the UI redesign's UI-8 (history, part 3), and the README's "one item
      is left". **M**
- [ ] **Reduced motion** is not detected for the search field's animation (R6c; Qt has
      no portable query). Decide whether a preference is wanted. **S**

### 8.4 After 1.0 (recorded so they are not lost; 16 open)

- [ ] **A command line for scripts and for AI tools** (recorded 2026-11-24; a new
      feature, so not before the 2026-11-26 hold lapses). Evans's engine already runs
      without a window: `Interpreter.run(source)` returns a `Result` (output, value,
      error), `SimModel.load` and `solver.simulate` run `.evx` models, and
      `--check` runs offscreen. What is missing is the packaging. In this order, one
      session each; the first two are one PR. **M** then **L**
      1. `evans run script.m`, `evans eval "expr"`, `evans sim model.evx --stop T --out
         result.json`: JSON output, exit codes, `--save-figs dir/` (PNG/PDF through
         `figure_mpl`). A console entry point in `pyproject.toml`, since the Windows exe
         is windowed. Find out first which `lib_*` commands assume a window (the hooks
         `close_figures`, `figure_open` and `simulink` default to `None`).
      2. A help page, tests, the README counts, `CHANGELOG.md` and the patch notes.
      3. A persistent session (`evans serve`: one `Interpreter` behind a local socket or
         stdio loop, so numpy/scipy/control load once) with a thin client.
      4. An MCP server over the same session: tools `eval`, `load_model`, `simulate`,
         `get_workspace`, `help`; the help pages double as tool docs.
      5. Optional, last: drive the running window (a `QLocalServer` in the GUI process,
         commands moved onto the Qt thread). Skip unless someone wants to watch the canvas.
      Cost guess, 2026-11-24: 1+2 about 20-40% of one 5 h window, 3+4 as much again.
      Prompted by the ECN lab report, which a throwaway runner covers without this.

- [ ] **A visual marker for the active pane** (`PaneGrid.active_index`, R5); *Show
      Bode* only says "Pane 2: Bode" in the status bar. *Decided 2026-11-23: not now.*
      With several panes up the user is working in all of them, so a mark is not
      needed yet. No date set; revisit if someone asks which pane a command went to. **S**
- [ ] Poles, zeros and gain dragged directly on the pane grid's root locus and Bode
      panes, replacing the small locus inside the Design tab. **L**
- [ ] Design requirements (overshoot, settling time, damping, margins) entered in
      the Design tab and drawn as shaded regions on every pane they apply to. **M–L**
- [ ] The script editor above the command window in one view. **M**
- [ ] The Time and Frequency workflow panes update live; their *Compute* buttons
      go. **S–M**
- [ ] Snapshots saved in the project (an optional `"snapshots"` list in
      `loop.json`; additive, so no format version change). **S–M**
- [ ] A check, with a few real students, of what they try first on the Start page
      and where they get stuck. **S**
- [ ] Limits tuning (0.30.0) follow-ups, in this order. **S–M** each.
  - [ ] An **undershoot** limit: a zone below 0 at the start of the step plot, for
        plants with an inverse response.
  - [ ] A **peak control effort** limit |u|: needs the control signal's own plot (or an
        overlay on the step pane), and is the practical limit for actuator saturation.
  - [ ] Delay time (50 %) and peak time limits (a vertical zone before that time).
  - [ ] Peak sensitivity Ms and peak of T as limits, drawn as an M-contour on the
        Nichols view (reuses `mtune`).
  - [ ] Disturbance rejection (largest output deviation after a load step) and a
        noise-gain / bandwidth cap that keeps the derivative term sane.
  - [ ] Run the search on a worker thread: it takes 3–4 s and freezes the window.
  - [ ] Remember the ticked limits in the project file.

---

## Questions for Leon

1. **Does any of the corpus's open findings block 1.0?** The 32 silent wrong
   answers were all fixed 2026-11-18. Still open: the separate 32 probes where Evans
   raises an error, the three tolerances, and the dry-run gaps (Phase 6). Do they have
   to land before 1.0, or can they follow in 1.x?

*Answered 2026-11-20 and moved into the items:* R6d starts with a diagnosis; the
reference results stay local and are git-ignored (academic licence).
