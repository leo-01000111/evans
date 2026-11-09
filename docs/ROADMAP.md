# Evans roadmap — from a control-course workbench to a free MATLAB + Simulink

Written 2026-10-27 from four audits of the code (MATLAB language, Simulink, toolboxes,
and workflow/interop), each gap checked against the source rather than from memory.
`docs/PLAN.md` is the history of what was built; this file is what is left.

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

Sizes: **S** is under a day, **M** a few days, **L** a week or more.

---

## Phase 0 — Silent wrong answers ✅ **DONE 2026-10-27**

These gave a wrong value without any error, the failure `PLAN.md` Part 5 ranks worst.
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

Left over from this phase:

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
- [ ] The same for numeric arrays: `a(k) = v` copies the array, about 0.4 s for
      10⁴ writes and quadratic past that. **M** An ndarray cannot carry the
      mark, and NumPy views share memory (`b = a(:)` may be a view), so
      in-place writes need their own tracking and tests.
- [ ] Search the rest of the language for more of these, with a probe script of
      MATLAB lines run against known MATLAB answers (see Phase 6, reference
      corpus). **M** *Deferred to Phase 6:* the known answers need a MATLAB
      licence to produce.

## Phase 1 — Everyday data work at the console (mostly wrapping) ✅ **DONE 2026-10-28**

Needed for any "process my logged data" job, whether coursework, a hobby project or test
data at work. All of it is in numpy and scipy already.

The functions live in `src/evans/console/lib_*.py`, one mixin of `_Library` per group
below, with tests in `tests/golden/test_lib_*.py`. **Left to do:** `fitlm` below. *Every
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
      *Also `datenum`, `datevec`, `date`. `datetime` waits for Phase 4.*
- [x] `dec2bin`, `bin2dec`, `dec2hex`, `factorial`, `nchoosek`, `primes`, `isprime`,
      `gcd`, `lcm`, `erf`, `gamma`, `beta`. *Also `hex2dec`, `dec2base`,
      `base2dec`, `erfc`, `erfinv`, `erfcinv`, `gammaln`, `betaln`, `nthroot`.*

## Phase 2 — Simulink for daily use ✅ **DONE 2026-10-30**

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
- [x] **Compare runs:** overlay the last N runs in a scope (deferred in PLAN Part 6).
      **M** *The last five are kept; "Compare with earlier runs" draws up to
      five, dashed and fading. The ticked channels survive a rerun. An XY
      Graph block gets its own view in the scope.*
- [x] **Sample models:** a few `.fmdl` files from the courses (DC motor, cruise control,
      inverted pendulum, PID loop with saturation), reachable from File ▸ Examples.
      There are none in the repo now. **S** *`src/evans/examples/`, rebuilt by
      `tools/build_examples.py`. The PID example builds its anti-windup loop
      from blocks: see the PID limit below.*
- [ ] **Later:** MIMO `linearize`, live parameter sliders during a run, and a user
      block API (S-function equivalent). **M each**
- [ ] **Subsystems, what is left.** Create Subsystem from Selection, descending into
      one, nested subsystems and conditional (enabled, triggered, action)
      subsystems exist (`sim/blocks/subsystem.py`, `compile.flatten`). Not done:
      - **Ungroup / Expand Subsystem**, the inverse of Create Subsystem. **S**
      - **Masks:** a parameter dialog for a subsystem, with its own variables
        (`gain`, `Ts`) used by the blocks inside, an icon or text on the block, and
        a documentation line. This is what makes a subsystem reusable. **M–L**
      - **Block libraries and linked blocks:** save a subsystem to a library file,
        drag it into other models as a link, update every link when the library
        changes, and break a link. **M–L**
      - **Referenced models** (Model block): run another `.fmdl` as a block, with
        its own run settings and a normal-mode/accelerated choice. **L**
      - **Atomic subsystems** and a subsystem-level sample time, which Simulink
        has and Evans flattens away. **M**
      - **Variant subsystems** and **function-call subsystems.** **M each**
      - **Port handling:** name the ports from the Inport/Outport blocks, reorder
        them, show the names on the block, and keep the wires when a port is added
        or removed. **S–M**
      - **Stable signal names across a subsystem edit** (renaming or moving
        a block inside it keeps the wire names; wire names already pass through
        flattening since 2026-11-09). **S**

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
- [ ] **Better block shapes.** Every block is a rectangle today (`BlockItem` in
      `ui/sim/items.py`). Some should look like what they are, as in Simulink's
      library: a triangle for Gain, a circle or rounded Sum with its signs at the
      ports, a round Product, a rounded Integrator box with 1/s, a Saturation and
      a Switch drawn with their characteristic, a Step, Ramp and Sine showing the
      waveform, a narrow bar for Mux/Demux, a flag shape for Goto/From and port
      blocks, and a distinct outline for Subsystem. The ports must stay where the
      router expects them and the hit area must follow the shape. Rotate and flip
      must work, and the shapes must read in both themes and in exports. Keep the
      rectangle as a fallback and add a "classic boxes" setting. **M**
- [ ] **Scope and graph overhaul in the Model tab** (`ui/sim/scope.py`). It is a basic
      pyqtgraph plot with a channel list and a CSV/`.mat` export today. Wanted:
      - **Copy straight from the plot:** Ctrl+C or a right-click menu entry copies
        the plot as an image (and the visible data as tab-separated text) to the
        clipboard, to paste into a report or a spreadsheet. **S**
      - **Better exports:** PNG at a chosen size and DPI, SVG, and PDF/EPS through
        the matplotlib path the console figures already use, with the theme either
        as on screen or on a white page for papers; the same for XY graphs. **S–M**
      - **Scaling:** manual and auto axis limits, a per-channel offset/scale,
        log axes, linked time axes across scopes, zoom to a box, and a "fit" and
        "reset" button. **M**
      - **Undock:** pop a scope out into its own window (and several at once, one
        per Scope block), keep it live over the next run, and dock it back. **M**
      - **Look:** line width, colour and style per channel, markers, legend
        position, grid, and a title, saved in the model like Simulink's scope
        settings. Plain measurement readouts (cursors with a delta between two,
        min/max/mean/peak-to-peak over a time range). **M**
      - **Hand-off to the console:** send the plotted channels to the workspace as a
        `timeseries` or struct, and "open as a figure" to continue editing it with
        console plot commands. **S–M**
- [ ] **Script pre-run for a model.** Link one or more `.m` files to an `.fmdl`, run
      in order when the model opens and/or before each run, so a model's
      parameters (`Kp`, `Ts`, plant matrices) are set up by the script that
      defines them, as a Simulink model's PreLoadFcn/InitFcn do. Wanted:
      - A "Model scripts" dialog on the Model tab: an ordered list of `.m` files
        (relative to the `.fmdl` where possible), each ticked for *on open*,
        *before every run*, or both, with move up/down and a Run now button. **M**
      - The paths and flags saved in the `.fmdl`; a missing file is a warning that
        names it, not a failed open. **S**
      - Scripts run in the console workspace, so block parameters that name
        workspace variables see them at compile time (`sim/workspace.py`); output
        and errors go to the console with the script's name and line, and an error
        in a pre-run script stops the run and says which one. **S–M**
      - A guard against surprises: ask before running scripts from a model that was
        just opened from a file the user did not create (like MATLAB's callback
        warning), with a "trust this model" choice remembered per path. **S**
      - MATLAB-side parity: the `set_param(model, 'PreLoadFcn', …)` and
        `'InitFcn'` forms in `console/lib_sim.py`, and loading a `.slx`'s
        callbacks once import exists (Phase 7). **S**

Found while doing this phase, not fixed in it:

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

## Phase 3 — Plotting ✅ **DONE 2026-11-03**

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
      `imread` is still to do; `imshow` of doubles is black at 0 and white at 1, as in
      MATLAB, so 0–255 data needs `imshow(I, [])` until there is `uint8`.*
- [x] A data cursor and a hover readout in `ui/console/figure_view.py`. **M**
      *Every 2-D curve, marker, bar, contour and reference line reads out on hover
      (the analysis tabs' `HoverReadout`); an image reads out its pixel. A click
      pins a data tip, a click on the tip removes it, and the plot menu has
      Remove data tips. 3-D axes show matplotlib's coordinate line instead; data
      tips on them are not done.*
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

Left over from this phase:

- [ ] Handle graphics: `h = plot(...)` and `set(h, …)`/`h.Color = …`, `cb.Label.String`.
      Every plot function returns nothing; properties go in as name-value pairs. **L**
- [ ] `figure(n)` going back to figure `n`, and `gcf` following the selected tab. **S–M**
- [ ] Data tips on 3-D axes, and the live colour map of a mesh after a theme switch
      without a redraw. **S each**
- [ ] `histogram` and `stem` pages, and the rest of the plotting commands that still have
      none (`stairs`, `semilogy`, `loglog`, `saveas`, `print`, `sgtitle`, `close`,
      `clf`, `gcf`). **S**

## Phase 4 — Running other people's MATLAB code

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
      surplus arguments (`matlab.py` ~1357). Repros R-A to R-E are in the writeup;
      are tests in `tests/golden/test_lib_lang.py`. **M** *Done 2026-11-09: the
      translator splices `c{:}` into argument lists and matrix rows
      (`cell_list` in the runtime), and `@(a, varargin)` lambdas take any number
      of arguments. `[varargout{1:nargout}] = f(...)` was not checked.*
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
      keep an integer input's class only when MATLAB's do (`sum`, `max`,
      `abs`, `sort`, `reshape` …); the rest hand back doubles. Display is
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

## Phase 5 — Hardware, identification, symbolic leftovers

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

## Phase 6 — Platform and trust

Professional users need this before Evans can be used for paid work.

- [ ] **Autosave and crash recovery.** Nothing is saved on its own today. Write a
      recovery copy of every unsaved document (editor scripts, live scripts, Model
      tab diagrams, console history, the workspace) to a folder under the user's
      app data every minute or so and after each edit pause, never over the real
      file. On the next start after a crash, offer to restore them. Add a setting
      for the interval and for turning it off, delete the copy on a normal save or
      close, and keep the last few versions of a model. Test with a simulated kill
      mid-edit. **M**
- [ ] **Rename the model file extension `.fmdl`** (FauxMatlab model, a leftover of the
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
- [ ] A Linux build (AppImage or a `.deb`). CI already tests on Ubuntu. **M**
- [ ] macOS notarisation, and an Intel build if anyone asks. **M**
- [ ] Windows code signing (deferred on purpose until there are more users; a Certum
      cloud certificate is the plan). **S** once bought.
- [ ] Auto-update on macOS (Windows has it). **M** *State, 2026-11-09:* the Mac app
      already checks GitHub at launch (`update.is_packaged`) and offers the release
      page, because it cannot replace itself; the prompt now says to download the
      disk image (`ui/updater.py`). That reads the Windows `.exe` asset's
      presence and checksum, so a release whose Windows build were missing would
      hide the update from Macs too: make the Mac check read the `.dmg` asset.
      Real self-update (a helper that waits for Evans to quit, swaps the `.app`,
      relaunches) needs notarisation first: with the ad hoc signature CI uses,
      Gatekeeper quarantines a downloaded replacement. Order: notarisation, then
      the helper, then the `.dmg` checksum check.
- [ ] A reference corpus of real MATLAB outputs (inputs and saved results, run once
      on a MATLAB licence) checked in CI, beside the closed-form golden tests. **M**
- [ ] A startup-time test and budget, and a size budget. The `dist/Evans` folder is
      343 MB. **S**
- [ ] A `CHANGELOG.md` in the repo; patch notes live only on the site now. A stated
      stability policy, and a 1.0 once Phases 1–2 land. **S**
- [x] Fix the `pyproject.toml` comment that still says "432 tests". **S**
- [ ] A profiler (`profile on/off/viewer`), `publish` for plain `.m` files to HTML/PDF,
      and git status in the file browser. **M each**
- [ ] The `B905` audit (`zip(..., strict=True)`), deferred in PLAN Part 4. **S**

## Phase 7 — Scope decisions before any large build

Each of these is a project of its own. Decide whether each is in scope before starting it.

- [ ] **Physical (acausal) modelling.** This is the one large gap that keeps the Model tab
      from replacing Simulink at work. Options: embed OpenModelica through FMI, write
      a small Simscape-like electrical/mechanical library on the existing DAE
      solver, or leave it out and say so. **L**
- [ ] **FMU import/export (FMI 2/3).** FMU import would let Modelica plants run on the
      canvas. **L**
- [ ] **`.slx`/`.mdl` import.** Even a partial import of the common blocks would let
      a colleague's model open. **L**
- [ ] **Code-first models** (`m = Model(); m.add(…)`), round-tripping with the canvas
      (PLAN Part 6 backlog). **M–L**
- [ ] **A browser build** through Pyodide (PLAN Part 6 backlog). **L**
- [ ] **Stateflow-like state machines, code generation, MPC, H∞/μ, an App
      Designer equivalent.** Likely out of scope for the target users; recorded so
      the decision is explicit. **L each**
- [ ] **An extension mechanism:** user toolboxes on the path, and a place to share
      them. **L**
