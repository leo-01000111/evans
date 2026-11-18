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

**Phase 8, the interface rework, was added 2026-11-16 and blocks 1.0.** It is at the end
of this file because it was planned last, not because it comes last.

Sizes: **S** is under a day, **M** a few days, **L** a week or more.

**Done means done.** A phase gets ✅ **DONE** only when it has no `[ ]` left, including
its "left over" and "found while doing this phase" lists. A phase whose planned core
is finished but still has open items is marked ◐ **Core done**, with the open items
counted in its heading. A ticked item whose note says part of it was not built gets
that part listed as its own `[ ]` item, so nothing open hides behind a tick.

---

## Phase 0 — Silent wrong answers ◐ **Core done 2026-10-27; 3 items open**

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
- [ ] Search the rest of the language for more of these, with a probe script of
      MATLAB lines run against known MATLAB answers (see Phase 6, reference
      corpus). **M** *2026-11-14: the answers exist now; the 32 silent wrong
      answers they found are listed under that Phase 6 item.* *Deferred to Phase 6:* the known answers need a MATLAB
      licence to produce.
- [ ] **Array writes, what is left** (from the in-place writes item above): growing
      (`a(end+1) = v`) still reallocates each time; a fill loop that passes the
      array to a function off the owned list copies once per call; a thread
      reading the workspace during a loop could see writes land. **M**
- [ ] **A cs-list mixed with other targets**, `[a, c{:}] = f()` (from the
      `varargout` item above). **S**

## Phase 1 — Everyday data work at the console (mostly wrapping) ◐ **Core done 2026-10-28; 2 items open**

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
      *Also `datenum`, `datevec`, `date`. `datetime` came with Phase 4
      (`console/lib_dates.py`).*
- [x] `dec2bin`, `bin2dec`, `dec2hex`, `factorial`, `nchoosek`, `primes`, `isprime`,
      `gcd`, `lcm`, `erf`, `gamma`, `beta`. *Also `hex2dec`, `dec2base`,
      `base2dec`, `erfc`, `erfinv`, `erfcinv`, `gammaln`, `betaln`, `nthroot`.*

Left over from this phase (parts of ticked items above that were not built):

- [ ] Several outputs from an anonymous function, so `[a, b] = cellfun(@(x) max(x), c)`
      works without a function file. **S–M**
- [ ] A `cftool` curve-fitting GUI over `fit`. **L**

## Phase 2 — Simulink for daily use ◐ **Core done 2026-10-30; 8 items open**

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
      - ~~**Ungroup / Expand Subsystem**, the inverse of Create Subsystem.~~ **S**
        *Done: `sim/edit.ungroup_subsystem`, right-click > Expand subsystem, one
        undo step. Inner blocks keep their place and names (suffixed on a clash);
        nested subsystems stay intact. Conditional subsystems are refused with a
        message, since the Enable/Trigger/Action condition has no home in the
        parent.*
      - **Masks:** a parameter dialog for a subsystem, with its own variables
        (`gain`, `Ts`) used by the blocks inside, an icon or text on the block, and
        a documentation line. This is what makes a subsystem reusable. **M–L**
      - **Block libraries and linked blocks:** save a subsystem to a library file,
        drag it into other models as a link, update every link when the library
        changes, and break a link. **M–L**
      - **Referenced models** (Model block): run another `.fmdl` as a block, with
        its own run settings and a normal-mode/accelerated choice. **L**
      - **Insert subsystem from `.evx`** (Leon's idea, 2026-11-11). Build a
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
- [ ] **Scope and graph overhaul in the Model tab** (`ui/sim/scope.py`). It is a basic
      pyqtgraph plot with a channel list and a CSV/`.mat` export today. Wanted:
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
      - **Scaling:** manual and auto axis limits, a per-channel offset/scale,
        log axes, linked time axes across scopes, zoom to a box, and a "fit" and
        "reset" button. **M**
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
      - **Look:** line width, colour and style per channel, markers, legend
        position, grid, and a title, saved in the model like Simulink's scope
        settings. Plain measurement readouts (cursors with a delta between two,
        min/max/mean/peak-to-peak over a time range). **M**
      - **Hand-off to the console:** send the plotted channels to the workspace as a
        `timeseries` or struct, and "open as a figure" to continue editing it with
        console plot commands. **S–M**
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
- [ ] **Buses**, cut on purpose and to be reconsidered after Goto/From, which is
      done; nobody has reconsidered them yet. Decide, then build or drop. **M**
- [ ] `sim` given a model object returns the Python result, not the
      `SimulationOutput`-like struct that `sim('name')` returns. **S**
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

## Phase 3 — Plotting ◐ **Core done 2026-11-03; 3 items open**

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

Left over from this phase:

- [ ] Handle graphics: `h = plot(...)` and `set(h, …)`/`h.Color = …`, `cb.Label.String`.
      Every plot function returns nothing; properties go in as name-value pairs. **L**
- [ ] `imread` (from the Images item above), into `uint8` arrays. **S**
- [ ] Nichols plot in the analysis tabs (`ui/tabs/frequency_tab.py`): a **K sweep**
      option (vary the loop gain and watch the curve shift up and down) and a
      **show M-circles** option (constant closed-loop magnitude contours). Added
      2026-11-13. **S–M**
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
- [ ] A Linux build (AppImage or a `.deb`). CI already tests on Ubuntu. **M**
- [ ] macOS notarisation, and an Intel build if anyone asks. **M** *Decided
      2026-11-11: not for 1.0.* There is no free route (Apple's programme is $99 a
      year). Until Evans has real users, the install page explains Open Anyway.
- [ ] Windows code signing (deferred on purpose until there are more users). *Decided
      2026-11-11: free only.* Leon applies to the SignPath Foundation (free for
      OSI-licensed public projects); then wire it into CI. **S–M** If declined,
      stay unsigned. Paid Certum signing only with real users.
- [x] Install page: step-by-step for an unsigned Windows installer (SmartScreen
      > More info > Run anyway) and an unnotarised Mac app (Privacy & Security >
      Open Anyway). **S** *Already there (checked 2026-11-11):*
      `site/pages/install.html` has `#smartscreen`, `#gatekeeper` and `#unsigned`.
- [ ] Auto-update on macOS (Windows has it). **M** *Done 2026-11-11: the update check now reads the `.dmg` asset on a Mac and the installer `.exe` elsewhere (`update.asset_pattern`), and the Mac prompt opens the `.dmg` download; self-update still waits on notarisation.* *State, 2026-11-09:* the Mac app
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
      **Blocks 1.0** (`docs/1.0-PROPOSAL.md`).
      *2026-11-14: the answers are in.* `tools/matlab_reference/evans_reference.mat`
      holds MATLAB R2023a Update 2's answers to the 496 probes in
      `evans_reference.m` (recorded 2026-11-13 on the school computer, with the
      Control, Signal and Optimization toolboxes). A one-off replay through
      `Interpreter.run_script` gave: 424 of 492 usable probes agree, 68 do
      not. Left out: probes 472, 476 and 477 (that computer has MOSEK on its
      path, and its `linprog`/`quadprog`/`intlinprog` answered instead of
      MATLAB's) and 488 (a datetime display format, not a real difference).
      - [ ] **The checker:** a test under `tests/golden/` that replays every
            probe in a fresh `Interpreter`, compares class, size and value
            (cells, structs and strings included; MATLAB saves whole-number
            doubles as small integer types, so cast by the recorded `cls`), and
            keeps a list of known differences by probe id that may only shrink.
            A probe that starts matching fails the test until it leaves the
            list. **M**
      - [ ] **Record again at the school computer:** probes 472, 476, 477 with
            MOSEK off the path (check with `which quadprog`); `filtfilt` (460)
            and `decimate` (470) with longer inputs, since MATLAB rejected the
            short ones; and run `which sum` to confirm the integer `sum` answer
            below is MATLAB's own. **S**
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
      - [ ] **Tolerances, not fixes (3):** `margin` (419), `stepinfo` (422) and
            `ode45` (378) differ by 0.1–1% because MATLAB's own answers are
            approximate (Evans's gain margin is the exact 8, MATLAB's 8.0011).
            The checker gives these probes a looser tolerance. **S**
      - [ ] **MATLAB answers, Evans raises an error (32).** **M**
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
      - [ ] **Found while dry-running the kit inside Evans (2026-11-14).** The
            harness is ordinary MATLAB, and Evans could not run it: **M**
            - Missing: `mfilename`, `tempdir`, `filesep`, `setappdata`/
              `getappdata`, `onCleanup`, `evalc`, `assignin`, `lastwarn`,
              `getReport`, `path`/`pathsep`, `matlabroot`, `zip`, `findall`,
              `allchild`, `version`, `ver`, `setdiff`.
            - `evalin` only reaches `'base'`, and `eval` inside a function
              cannot assign a variable.
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
- [x] A startup-time test and budget, and a size budget. The `dist/Evans` folder is
      343 MB. **S** *Done 2026-11-11:* `tests/test_startup_budget.py` (cold window
      build, median 9.3 s here, budget 20 s, `EVANS_STARTUP_BUDGET_S` to override);
      CI runs `tools/check_size.py` on `dist/Evans` (395 MB), the installer (140 MB)
      and the `.dmg` (126 MB): 0.24.0 plus 15%.
- [ ] A `CHANGELOG.md` in the repo; patch notes live only on the site now. A stated
      stability policy, and a 1.0 once Phases 1–2 land. **S**
      - [x] `CHANGELOG.md`, *done 2026-11-11:* every version from 0.9.0 to 0.20.0,
        a "before 0.9" entry and an Unreleased section. `tests/test_changelog.py`
        fails when the current `evans.__version__` has no section.
      - [ ] The stability policy and 1.0: proposal in `docs/1.0-PROPOSAL.md`,
        waiting for the owner's decisions. Leave open until then.
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
      a colleague's model open. Its PreLoadFcn/InitFcn callbacks map onto model
      scripts (Phase 2) when they only call scripts. **L**
- [ ] **Code-first models** (`m = Model(); m.add(…)`), round-tripping with the canvas
      (PLAN Part 6 backlog). **M–L**
- [ ] **A browser build** through Pyodide (PLAN Part 6 backlog). **L**
- [ ] **Stateflow-like state machines, code generation, MPC, H∞/μ, an App
      Designer equivalent.** Likely out of scope for the target users; recorded so
      the decision is explicit. **L each**
- [ ] **An extension mechanism:** user toolboxes on the path, and a place to share
      them. **L**

## Phase 8 — Interface rework before 1.0 **Blocks 1.0; 4 of 10 packages done**

Planned 2026-11-16 from a UI audit (research into comparable tools, a code inventory
and offscreen renders of every workspace) and two rounds of decisions with Leon. It
continues `docs/UI-PLAN.md` (UI-1 to UI-8, all built); where the two disagree, this
phase wins. It is written for a coding agent that has not seen the discussion, so it
spells out behaviour, files, traps and tests. **Read 8.0 to 8.2 before any package.**

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
  just dropped (`docs/1.0-PROPOSAL.md`, stability policy 3). Window layout keys live
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
- **Known traps** (from `docs/UI-PLAN.md`): a `str`-mixin enum comes back from
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

Order: R0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9. R6 touches only
`ui/sim/` plus one preference, so it may run beside R5 or R7.

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
  - New module `ui/loop_undo.py` with one command class:
    `ReplaceLoop(QUndoCommand)` holding `arch`, `before: dict`, `after: dict`
    (both from `core.session.session_dict(arch)`), a `text`, and an optional
    `merge_key: str`. `undo()` calls `load_session_dict(arch, before)`, `redo()`
    loads `after`; the first `redo()` (run by `QUndoStack.push`) does nothing,
    because the change has already been made. `id()` returns a fixed int when
    `merge_key` is set, and `mergeWith(other)` keeps this command's `before` and
    takes the other's `after` when both keys are equal: that is how a slider drag
    becomes one undo step. After undo or redo the command calls a `refresh`
    callable given at construction.
  - `MainWindow` gets `self._loop_undo = QUndoStack(self)` (limit 200) and one
    helper every change goes through:
    ```python
    def change_loop(self, text, mutate, *, merge_key=None):
        before = session_dict(self._arch)
        mutate()
        after = session_dict(self._arch)
        if after != before:
            self._loop_undo.push(ReplaceLoop(self._arch, before, after, text,
                                             self._after_loop_change, merge_key))
        self._after_loop_change()
    ```
    `_after_loop_change` does `self._diagram.build()`, `self._update_all_tabs()`,
    `self._refresh_status()`.
  - Route every place that changes the loop through it. They are, in
    `ui/mainwindow.py`: `_on_tf_edited` ("Edit G" and so on; the block editor has
    already written the block when the signal arrives, so capture `before` earlier:
    connect to the editor so the write itself happens inside `mutate`, or keep the
    last known `session_dict` in `self._loop_baseline` refreshed in
    `_after_loop_change` and use that as `before`), `_on_controller_designed`
    ("Apply controller"), `_load_preset_G` ("Load preset"), `_on_console_system`
    ("Load <name> as G"), `_on_linearised` ("Load linearised model"),
    `_on_modern_model_sent`, `_on_snapshot_restored` ("Restore snapshot"),
    `_open_session` ("Open loop"). `_new_session` replaces the architecture object
    itself: change it to keep the same object and load a default session dict into
    it, so the stack and every holder stay valid. The `_loop_baseline` approach is
    the simplest and covers changes made by widgets that write the architecture
    directly; prefer it.
  - **Not tracked:** changes typed at the console (`arch` is a live reference there).
    When the console finishes a command, compare `session_dict` with the baseline
    and, if it changed, push one "Console change" command. The hook is where the
    console reports a finished command (`ConsolePanel` in
    `ui/console/console_dock.py`; grep `finished` / `executed`).
  - **Edit menu**, placed after File: Undo, Redo, separator, (R4 adds Preferences).
    Use a `QUndoGroup`: add `self._loop_undo` and the canvas's stack
    (`self._sim_tab._canvas.undo_stack`; check how `SimTab` picks the stack when the
    user descends into a subsystem and follow it), create the two actions with
    `group.createUndoAction(self, "Undo")` / `createRedoAction`, shortcuts Ctrl+Z and
    Ctrl+Y (plus Ctrl+Shift+Z). In `_on_workspace_changed` call
    `group.setActiveStack(...)`: the loop stack on Analyse, the canvas stack on
    Model, `None` on Console. Remove `setShortcut("Ctrl+Z")` / Ctrl+Y from the Model
    toolbar's Undo and Redo actions (`SimTab._build_toolbar`, around the lines that
    call `self._canvas.undo_stack.undo()`), keep the buttons. On Console the text
    editors handle Ctrl+Z themselves; test that Ctrl+Z in the script editor still
    undoes typing.
  - The bottom bar shows "Undo: <text>" for three seconds after an undo.
  - Tests (`tests/golden/test_loop_undo.py`): edit G then undo restores the old
    transfer function and every pane; a preset load, a snapshot restore and a
    linearise are each one step; ten merged slider changes are one step; the menu's
    Undo acts on the canvas when Model is current; a console command that changes
    `arch` is undoable; a new session keeps the same architecture object.
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
  - **New widget `ui/side_panel.py`: `SidePanel(QWidget)`.** A tab bar at the top
    (sign font, like the Console's tab bar), a `QStackedWidget` below, each page
    inside a `QScrollArea` (frameless, widget-resizable). API: `add_tab(key, title,
    widget)`, `set_current(key)`, `current` (key), `set_open(bool)`, `is_open`,
    `toggled = Signal(bool)`, `tab_changed = Signal(str)`, `holder(key)` returning
    the page's container so a widget can be moved into it. Default width 320 px,
    minimum 240 px. A close button (the `x` icon from `ui/iconset.py`) at the right
    of the tab bar.
  - **Placement.** Each workspace page becomes a horizontal `QSplitter`:
    `[content | SidePanel]`, the content stretching. The splitter belongs to the
    page, so the panel cannot leak into another workspace and the rail stays at the
    window's left edge.
    - Analyse (`MainWindow._build_analyse`): content is today's column (context bar,
      snapshot bar, pane grid). Tabs: `loop` "Loop" holding the existing
      `FixedDiagramView` (keep its 150 to 260 px height cap) above the existing
      `BlockEditor`; `design` "Design" (an empty placeholder page saying "Design
      tools arrive here" until R3); `cedric` "Cedric". Closed by default.
    - Model (`ui/sim/sim_tab.py`, where `splitter.addWidget(side)` adds the
      inspector column): the right column becomes a `SidePanel` with `properties`
      "Properties" (the existing `BlockInspector` and the *Show global scope*
      button under it) and `cedric`. Open by default on Properties. `SimTab` exposes
      it as `self.side_panel`.
    - Console (`ConsolePanel.__init__` in `ui/console/console_dock.py`): today the
      Workspace and History tabs (`self._side`) sit inside the *Console* tab's
      splitter, so they vanish on the Script and Live tabs. Move them out: the
      Console workspace page becomes `[existing vertical splitter | SidePanel]` with
      `workspace` "Workspace", `history` "History", `cedric`. Open by default on
      Workspace. Keep `ConsolePanel.workspace` and `.history` attributes: other code
      uses them (`self._console.workspace.refresh()`).
  - **Cedric in every workspace.** There is one `AssistantPanel`
    (`ui/assistant/panel.py`). Delete `AssistantDock` and `_build_cedric`'s dock
    code; create the panel once as `self._cedric_panel`. In
    `_on_workspace_changed`, move it into the current workspace's `cedric` holder
    (`holder.layout().addWidget(self._cedric_panel)` reparents it; the conversation
    survives because it is the same object). Keep the wiring that exists:
    `panel.run_command → self._console.execute`, `panel.paste_command →
    self._console.recall`, `self._console.cedric_requested → self._ask_cedric`.
    `set_cedric_visible(True)` now opens the **current** workspace's side panel on
    the Cedric tab and no longer jumps to Console; `_ask_cedric` (Ask Cedric on a
    console selection or error) still switches to Console first because its context
    is there. Remove `_cedric_wanted`, `_cedric_syncing`, `_sync_cedric`,
    `_on_cedric_visibility` and replace their uses.
  - **What Cedric reads.** `panel.set_source(...)` takes a `Source`
    (`ui/assistant/sources.py`: `EditorSource`, `ConsoleSource`, `SwitchSource`). On
    Console keep `self._console.assistant_source`. Add two small read-only sources in
    the same file: `LoopSource` (describes the loop as text: G, K₁, K₂, H as transfer
    functions, the verdict and margins from `ContextBar.summary()`) for Analyse, and
    `ModelSource` (the model's name, its blocks with type and parameters, its wires,
    from the canvas's `root_model()`) for Model. Read `Source` first to see which
    methods a read-only source must implement; they must refuse edits the way a
    source with nothing editable does. Set the source on workspace change.
  - **Toggle and shortcuts.** View ▸ *Side panel* (Ctrl+\\, checkable) opens or
    closes the current workspace's panel; it replaces View ▸ *Model panel*.
    Ctrl+Shift+A opens it on Cedric. The context bar's button becomes **Edit loop**
    and opens the Analyse panel on Loop (`ContextBar._edit_btn`, signal
    `edit_requested`; update its tooltip and `MainWindow.toggle_model_panel`, which
    becomes `toggle_side_panel` plus `show_loop_editor`). Clicking a block in the
    diagram selects it in the editor as now (`_on_block_selected`).
  - **Rail foot.** `NavigationRail` (`ui/workspace.py`) ends with one `CedricButton`
    wired to `help_requested`. Make it two controls: the shrimp opens Cedric (new
    signal `cedric_requested`; tooltip "Ask Cedric (Ctrl+Shift+A)"; accessible name
    "Cedric"), and under it a small text button **Docs** (tooltip "Documentation
    (F1)") that emits `help_requested`. The shrimp's "need help?" caption goes.
  - **Persistence.** Per workspace, in the layout settings
    (`MainWindow._settings()`): `side/<workspace>/open`, `side/<workspace>/tab`,
    `side/<workspace>/width`. Save in `save_layout`, restore in `restore_layout`,
    reset in `reset_layout` (Analyse closed on Loop; Model open on Properties;
    Console open on Workspace). Remove the `modelPanel` and `cedricPanel` keys; on
    restore, if `modelPanel` was true open Analyse's panel on Loop, if `cedricPanel`
    was true open Console's on Cedric, then delete both old keys. Switch to
    `saveState(2)` / `restoreState(state, 2)` (8.2).
  - **Remove** `self._model_dock`, the `ModelDock` object name, `_act_model`, and
    their uses in `reset_layout` and `_sync_view_menu`.
  - Tests: extend `tests/golden/test_ui_layout.py` (minimum size unchanged with
    every panel open at 1280×720; the rail's x position is 0 in every workspace with
    any panel open; a panel opened on Analyse is not visible on Model); rewrite
    `tests/golden/test_cedric_ui.py` for the panel (same conversation object after
    switching workspace twice; Ask Cedric on a console error opens Console's panel
    on Cedric); layout round trip of the three `side/...` keys and the migration of
    the two old keys.
  Traps: `restoreState` used to bring dock visibility back, and `_sync_view_menu`
  re-synchronised the check marks after it; the new toggle must be synchronised on
  every workspace change instead. The Console page's `figure_area_wanted` signal
  hides the figure strip on the Live tab; keep it working after the re-parenting.
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
  - **Design tab** (`ui/design_panel.py`, new): a `QWidget` with a three-way
    segmented control at the top, **Gain · Compensator · PID**, and a
    `QStackedWidget` under it.
    - *Gain* and *Compensator* reuse `ControlSystemDesigner`
      (`ui/apps/designer_app.py`). Give it a constructor flag `compact=True` that
      builds `_build_controls()` and only the **root locus** plot from
      `_build_plots()` (it is the drag surface: the draggable closed-loop pole
      target, `_install_target`, `_move_target`), not its Bode and step plots,
      because the pane grid shows those. In compact mode the layout is vertical:
      locus on top (fixed 220 px high), controls below. *Gain* shows the gain
      spin box, slider, *Set K for ζ* and *Set K for overshoot*; *Compensator*
      shows the zeros and poles fields and the *+ Integrator* / *+ Lead* buttons.
      Both pages are views of the same designer object.
    - *PID* reuses `PIDTuner` (`ui/apps/pid_tuner.py`) with `compact=True`:
      `_build_controls()` only (kind, Tf, the two sliders, the result text, *Reset
      sliders*), no plots.
  - **Live apply.** In compact mode a change does not wait for an Apply button: it
    sets K₂ at once through `MainWindow.change_loop("Design: gain", ...,
    merge_key="design-gain")` (and `"design-compensator"`, `"design-pid"`), so the
    panes are the display and one drag is one undo step. Throttle: while a slider
    or the pole target is being dragged, apply at most every 50 ms with a
    single-shot `QTimer`; on release apply once more. The designer already
    separates moving from settling (`_on_target_moved`, `_on_drag_settled`,
    `_on_target_released`): preview on move, commit on settle. Remove *Apply as
    K₂* in compact mode and add **Reset** ("Back to the controller from before this
    tab was opened"), which restores the K₂ remembered when the tab was shown.
  - **The plant changes under it.** When the loop changes from elsewhere (undo, a
    preset, the Loop tab), the Design tab must re-read the plant, sensor and K₂:
    call `designer.set_plant(G, H)` / `set_compensator(Compensator.from_tf(K2))` and
    `tuner.set_plant(G, K2, sensor=H, feedforward=K1)` from `_after_loop_change`,
    guarded against the feedback loop where the tab's own apply triggers a re-read
    that moves its sliders (a `self._applying` flag, checked first).
  - **Several systems in one pane (LTI Viewer dissolves).** A plot pane is already
    an `LTIViewer` in compact mode (`AnalysisPane` in `ui/panes.py`), and the viewer
    already draws a `SystemCollection`. Add to each plot pane's header a **Compare**
    menu button (text "Compare", checkable entries): the other loop sources (the
    `Source` enum's members other than the pane's own), every snapshot in
    `MainWindow.snapshots`, and any systems handed over by `ltiview(...)`. Checked
    entries are added to the pane's collection as extra curves with their names in
    the legend; the pane's own source stays the first, solid curve. The metrics
    pane and the workflow panes have no Compare button. State is per pane and is
    not persisted.
  - **Console commands keep working** (`console/apps.py`, `MainWindow.open_app`):
    - `sisotool(G)` → switch to Analyse, load the plant if one was named (through
      `change_loop`), open the side panel on Design ▸ Compensator.
    - `pidtuner(G)` / `pidtuner(G, 'PID')` → same, Design ▸ PID with that kind.
    - `ltiview(G1, G2, ...)` → switch to Analyse, and in the first plot pane set
      the named systems as its Compare set (keep the pane's kind; with no plot pane
      in the grid, set pane 1 to *Step response* first).
    Update the three help pages (`ltiview.md`, `sisotool.md`, `pidtuner.md`) to say
    where each now opens, and check `tests/test_help.py`.
  - **Snapshot bar's Compare** (`_compare_snapshots`) ticks the snapshots in every
    plot pane's Compare menu instead of opening the viewer.
  - **Delete:** the Apps menu, `_APP_DOCKS`, `_show`, `_app_docks`, `_apps`,
    `_open_lti_viewer`, `_default_viewer_systems`, the dock branches of
    `_open_designer` and `_open_pid_tuner`, and the three Ctrl+Shift+L/D/T
    shortcuts. Keep `ui/apps/lti_viewer.py` (it is the pane renderer) and the
    non-compact modes of the designer and tuner only if a test still needs them;
    otherwise delete the dead branches.
  - The *Design* workflow pane kind (`PaneKind("design", ...)`, `ui/tabs/`
    `design_tab.py`) stays for now. Removing a pane kind changes the README's
    pane-kind count (`tests/golden/test_packaging.py`).
  - Tests: rewrite `tests/golden/test_apps_ui.py` and adjust `test_apps.py`: each
    console command lands on the right tab; a gain slider drag changes K₂, updates
    a pane, and is one undo step; Reset restores the earlier K₂; an undo from the
    Edit menu moves the Design tab's widgets back without re-applying; ticking a
    snapshot in a pane's Compare menu adds one curve; the window's minimum size is
    unchanged.
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

- [ ] **R4 — Menus, preferences, bottom bar, a slimmer context bar.** *sonnet.* **M**
  Needs R2 and R3.
  - **Menu bar: File · Edit · View · Help.** Rebuild `MainWindow._build_menus`:
    - *File:* New ▸ (R7 fills it; until then *New loop*), Open… (Ctrl+O), Open
      recent ▸, Examples ▸, separator, Save (Ctrl+S), Save as… (Ctrl+Shift+S),
      separator, **Export ▸** (the six items of today's Export menu, unchanged;
      *Export current tab as PNG…* becomes *Export pane as PNG…* and moves from
      Ctrl+Shift+P to Ctrl+Shift+E, because R5 gives Ctrl+Shift+P to search),
      separator, Quit (Ctrl+Q).
    - *Edit:* Undo, Redo, separator, *Send loop to the console* (today's View ▸
      *Send current plant to the console*), separator, **Preferences…** (Ctrl+,;
      give the action `QAction.PreferencesRole` so macOS puts it in the app menu).
    - *View:* Side panel (Ctrl+\\), Cedric (Ctrl+Shift+A), separator, Analyse,
      Model, Console (Ctrl+1/2/3), separator, Snapshot bar (checkable, from the old
      Settings menu), Block palette (Ctrl+B, if not already a window action),
      separator, Reset layout.
    - *Help:* Documentation (F1), Keyboard shortcuts (Ctrl+/, R5 builds the
      dialog; until then omit), Check for updates…, About.
    - Gone: the Export, Apps, Presets and Settings menus; View ▸ Theme, Classic
      block boxes and Integrated title bar (they move to Preferences); File ▸
      Autosave (moves to Preferences); Help ▸ Check for updates automatically
      (moves to Preferences).
  - **Presets** move to a **Plant** menu button in the context bar, left of *Edit
    loop*: the seven presets (`_preset_first_order` … `_preset_satellite`) and, at
    the bottom, *From the console workspace…* listing the systems in the console's
    namespace (it does what double-clicking one in the Workspace tab does,
    `_on_console_system`). `ContextBar` gets a `set_plant_menu(QMenu)` method; the
    main window builds the menu.
  - **Preferences dialog** (`ui/preferences.py`, a `QDialog`, non-modal `open()`
    from the menu and a `preferences_dialog()` factory the tests can drive without
    `exec()`). One page, grouped, each control bound to the existing persist
    function, applied at once (no OK/Cancel, one Close button):
    - *General:* On launch (Start page / Reopen what was open; used from R8, key
      `startup/show`); Autosave for crash recovery on/off and interval (today's
      `_build_autosave_menu` and `set_autosave`); Check for updates automatically
      (`persist.update_auto_check`).
    - *Appearance:* Theme System/Day/Night (calls `MainWindow.choose_theme`, which
      asks for the restart); Integrated title bar (Windows only, disabled
      elsewhere; `set_integrated_title_bar`); Classic block boxes
      (`ui/sim/shapes.set_classic`); Snapshot bar (`set_snapshot_bar_visible`).
    - *Model:* Scope opens in (Its own window / The side panel; key
      `model/scopeOpensIn`, default `window`; R6 uses it).
    Tests that read `_act_classic_boxes`, `_act_title_bar`, `_act_snapshots` and
    `_theme_actions` (`test_block_shapes.py`, `test_title_bar.py`, `test_theme.py`,
    `test_ui_layout.py`) move to the dialog's controls or to the underlying
    function.
  - **Bottom bar per workspace** (`_build_status_bar`, `_sync_model_status`,
    rename the latter `_sync_status_bar`). Add permanent widgets on the right,
    shown only on their workspace:
    - Analyse: the `StatusBadge` verdict and the three `MetricLabel`s (PM, GM, ωc)
      that today live in `ContextBar` (`_badge`, `_pm`, `_gm`, `_wc`). Move the
      widgets and their refresh code (`_refresh_verdict`, `_refresh_margins`) into
      a new small class `LoopStatus` in `ui/context_bar.py` with `refresh(arch)`,
      `verdict` and `summary()`; `ContextBar.verdict`/`summary()` delegate to it so
      existing callers keep working. The verdict's explanatory note (`_note`)
      becomes the badge's tooltip.
    - Model: unchanged (`self._sim_tab.status_widgets()`).
    - Console: a label "Idle" / "Running" driven by `self._console.running` (find
      the signal that marks a run's start and end in `ConsolePanel`).
    Use `addPermanentWidget` so `showMessage` does not hide them.
  - **Context bar** then holds only: G(s), K₂(s), a stretch, *Plant ▾*, *Edit
    loop*. It should be one text line high when both transfer functions fit on a
    line beside each other at 1280 px, two lines otherwise (as now).
  - Tests: the four menu titles and nothing else; every removed action's function
    is reachable from the dialog, the Plant menu or the File menu; the lamp is
    visible on Analyse and hidden on Model and Console; a transient
    `showMessage` leaves the lamp visible.

- [ ] **R5 — Search: the command palette, and the shortcut sheet.** *sonnet.* **M–L**
  Needs R4.
  - **Qt-free core, `ui/search.py`:**
    - `@dataclass Entry`: `id: str` (stable, e.g. `"file.save"`,
      `"block.Gain"`, `"preset.so_under"`), `title: str`, `section: str` (shown
      muted: "Analyse", "Model", "Console", "File", "Help", "Blocks", "Examples",
      "Recent"), `workspace: Workspace | None` (None = global), `shortcut: str`
      (already through `keys.label`), `keywords: tuple[str, ...]`, `run:
      Callable[[], None]`.
    - `score(query, text) -> float | None`: case-insensitive subsequence match;
      None when the letters of `query` do not appear in order. Higher for: a match
      at the start of the text, matches at word starts, consecutive letters,
      shorter text. An empty query matches everything with score 0.
    - `rank(entries, query, current, recent_ids) -> list[Entry]`: best of the
      title's and keywords' scores; then **group order**: entries of the current
      workspace, then global entries, then entries of other workspaces; inside a
      group by score, then by recency (`recent_ids`, newest first), then by title.
      With an empty query show recent entries first, then the current workspace's.
      Return at most 50.
    Unit tests in `tests/test_search.py` (no Qt): ordering by group, by score, by
    recency; "bod" finds "Bode"; "svas" finds "Save as"; no match returns `[]`.
  - **The registry** (`ui/search_registry.py`, Qt): `collect(window) ->
    list[Entry]`, built fresh each time the palette opens (it is cheap and never
    stale):
    - every enabled `QAction` reachable from the menu bar, walked recursively;
      title "Save as…" with section from the top menu; `&` stripped; the action's
      workspace read from `action.property("workspace")` (set it in
      `_build_menus` for the workspace-specific ones, e.g. Export ▸ Model diagram…
      is Model);
    - Analyse: one entry per pane kind ("Show Bode" sets the kind of the **active
      pane**; add `PaneGrid.active_index`, updated when a pane is clicked, default
      0), the three layouts, the seven presets, the Design tabs, Take snapshot;
    - Model: one entry per block type ("Add block: Gain", from the block library
      the palette already lists, `ui/sim/palette.py`; runs
      `canvas.add_block(type_name)` at the view's centre), the toolbar actions
      (Run, Stop, Linearise, Scripts…), every example;
    - Console: one entry per help page ("Help: bode", opens the page with
      `help.open_help(name)`; check that function's signature), the open scripts;
    - global: go to each workspace, recent files, Preferences, Reset layout,
      Documentation.
    An entry whose workspace is not the current one first calls
    `window.show_workspace(...)`, then runs.
  - **The popup** (`ui/search_popup.py`): a frameless child widget of the main
    window (not a top-level window, so it needs no focus-stealing), 560 px wide (or
    the window's width minus 32 px if smaller), centred horizontally, its top 48 px
    under the window's top. A `QLineEdit` (placeholder "Search actions, blocks,
    commands, help") over a `QListView` showing at most ten rows without
    scrolling; each row: title left, section in the muted colour after it, shortcut
    right in the mono face. The row under the cursor uses the signal-yellow
    selection the tab bars use. Keys: Up/Down move, Enter runs and closes, Esc
    closes, typing filters (re-rank on every `textChanged`). Clicking outside
    closes. Frame and shadow as the design system's plates (2 px frame, hard 4 px
    offset shadow, no blur).
  - **Opening it:** a window-level action *Search…* with Ctrl+K and Ctrl+Shift+P
    (View menu, top). And a field in the title strip: `TitleBar`
    (`ui/titlebar.py`) lays out plate, menu bar, title (stretch), caption buttons;
    put a flat, read-only-looking button styled as a field ("Search   Ctrl K")
    between the menu bar and the title, at most 280 px wide, hidden when the
    window is narrower than 900 px. It must be reported as a client area, not as
    caption, by `TitleBar.region_at` (the integrated Windows title bar asks that
    function what is draggable; see how the menu bar is excluded) or it will not
    receive clicks. `tests/golden/test_title_bar.py` covers `region_at`.
  - **Recency:** `persist` key `search/recent`, the last 20 entry ids.
  - **Keyboard shortcuts sheet:** Help ▸ Keyboard shortcuts (Ctrl+/), a dialog
    built from the same registry: every entry with a shortcut, grouped by section,
    two columns, plus a short fixed list of the keys that are not actions (canvas:
    Delete, Esc, Ctrl+wheel; console: Up/Down, Tab, Ctrl+Space; editor: F5, F10,
    F11). The same content is added to the documentation.
  - Tests (`tests/golden/test_search_ui.py`): Ctrl+K opens the popup with focus in
    the field; on Model, "gain" + Enter adds a Gain block (one undo step); on
    Analyse the same query lists the block under a later group and choosing it
    switches to Model first; "bode" + Enter on Analyse changes the active pane;
    Esc closes and restores focus; every menu action appears exactly once.

- [ ] **R6 — Canvas quick insert; scope dock option.** *sonnet.* **M** Needs R2 (for
  the side panel) and R4 (for the preference); may run beside R5 or R7.
  - **Quick insert popup** (`ui/sim/quick_insert.py`): a small frameless child of
    the canvas viewport, 220 px wide, a `QLineEdit` over a list of at most eight
    block types, ranked with `ui/search.score` (copy nothing; import it. If R5 has
    not landed, build `ui/search.py`'s `score` first, with its tests). Enter
    inserts the highlighted type, Esc closes, clicking elsewhere closes.
  - **Three ways in** (`ui/sim/canvas.py`):
    1. **Double-click on empty canvas.** Block items handle their own double-click
       (`BlockItem.mouseDoubleClickEvent` in `ui/sim/items.py`: parameters, or the
       scope's plot). Add `SimCanvas.mouseDoubleClickEvent`: if `itemAt(pos)` is
       None, open the popup at the cursor and insert at that scene position with
       `self.add_block(type_name, scene_pos)`; otherwise call `super()`.
    2. **Typing with the canvas focused.** In `keyPressEvent`, a printable
       character with no Ctrl/Alt/Meta held, while no wire is being drawn and no
       text item is being edited, opens the popup at the last mouse position (or
       the view's centre) with that character already typed. Existing keys (Esc,
       Delete, Backspace, copy, paste, select all) keep their meaning; check the
       order of the tests in `keyPressEvent` so letters do not swallow them.
    3. **A wire dropped on empty canvas.** Today releasing a drag-wire on nothing
       cancels it (`mouseReleaseEvent` → `_cancel_wire`). Instead, unless Alt is
       held, keep the rubber wire on screen, open the popup at the drop point
       listing only block types that have a port of the needed direction (an
       input, if the wire started at an output; an output otherwise). On Enter:
       `undo_stack.beginMacro("Add connected block")`, add the block so that its
       first matching port sits on the drop point (use the port offsets the
       block's shape reports; `port_snap` / `PortCandidate` in `ui/sim/items.py`
       show how ports are located), connect with the same command `_finish_wire`
       uses (`Connect` in `ui/sim/commands.py`), `endMacro()`. On Esc: cancel the
       wire as today.
  - The standing wiring hint on the canvas gains "double-click or type to add a
    block".
  - **Scope: dock or window.** `SimTab.open_scope_window(key)` opens a
    `ScopeWindow` (`ui/sim/scope_window.py`) per Scope block. Add:
    - a **Dock** button in the scope window's toolbar: the window closes and the
      same scope widget appears as a tab "Scope: <block name>" in the Model side
      panel (`self.side_panel.add_tab(f"scope:{key}", ...)`), with an **Undock**
      button that does the reverse. Either way it is one widget, moved, so its
      curves, ticked channels and compare setting survive;
    - the preference `model/scopeOpensIn` (R4): `window` (default) or `panel`
      decides where a double-click on a Scope block opens it;
    - docked scopes are closed with the model, as windows are
      (`close_scope_windows`), and redraw after each run, as windows do.
    Tests: extend `tests/golden/test_scope_windows.py` (dock, undock, the
    preference, redraw after a run in both places, closed on model replace) and
    `tests/golden/test_canvas.py` (the three ways in; Alt keeps the old cancel; one
    undo step removes block and wire together).

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
    with a visible focus frame; the glyphs from R0.
  - **Contrast and colour.** Measure text contrast for `ink_muted` on `ground` and
    on `surface` in both themes (target 4.5:1) and the plot line colours against
    the plot background (3:1); check that curves in a Compare set differ by line
    style as well as colour. Fix in `ui/theme.py` only with Leon's agreement,
    since it is the design system.
  - **Sweep for leftovers** (haiku): the strings "Model panel", "Edit model",
    "Apply as K", "Apply to Architecture", "Send to analysis", "Apps" (as a menu),
    "LTI Viewer" as a window or dock, "session" where "loop" or "project" is meant;
    in `src/`, `site/`, `README.md`, `src/evans/help/pages/` and docstrings.
  - **Documentation:** the site's pages that describe the window (screens,
    workflow, shortcuts), a new page on projects, the README's description of the
    interface and any count it states (`tests/golden/test_packaging.py`),
    `docs/CODEMAP.md` (new modules under "Where to look for"), `docs/UI-PLAN.md`'s
    status table gets a closing line pointing here, and new screenshots
    (`docs/theme-day.png`, `docs/theme-night.png`, the site's).
  - **Release notes:** a section in `CHANGELOG.md` and in
    `site/pages/patch-notes.html` (`tests/test_changelog.py`), with a *Changed*
    list a returning user needs: where the three apps went, the new menu layout,
    the moved shortcuts (Export PNG is Ctrl+Shift+E; Ctrl+Shift+L/D/T are gone;
    Ctrl+K and Ctrl+Shift+P search; Ctrl+\\ is the side panel; Ctrl+0 is Start),
    Cedric on every workspace, projects.
  - **`docs/1.0-PROPOSAL.md`:** add this phase to the must-have list and state
    that, from 1.0, the project file format and the settings keys introduced here
    fall under the stability policy.

### 8.4 After 1.0 (recorded so they are not lost)

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
