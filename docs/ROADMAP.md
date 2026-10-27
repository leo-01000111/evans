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

- [ ] Struct arrays are always rows: `struct('a',{1;2})` is 1×2, not 2×1. **S**
- [ ] A `for` loop whose variable is a `global` does not write it back. **S**
- [ ] `clear all`, `clear global` and `clear functions` do not reset globals or
      persistents. **S**
- [ ] `numel("hello")` is 5 and should be 1 (string arrays, Phase 4). **S–M**
- [ ] Writing one element of a cell, struct or array copies it, so growing one in a
      loop is quadratic. `c{end+1} = k` for 10⁴ elements takes about 3.5 s, against
      about 0.5 s before cells were copied; numeric arrays already behaved this way.
      Copy only when the value is shared, for example by marking it at `b = c` and at
      function calls. **M**
- [ ] Search the rest of the language for more of these, with a probe script of
      MATLAB lines run against known MATLAB answers (see Phase 6, reference
      corpus). **M**

## Phase 1 — Everyday data work at the console (mostly wrapping)

Needed for any "process my logged data" job, whether coursework, a hobby project or test
data at work. All of it is in numpy and scipy already.

**File I/O** **M**
- [ ] `readmatrix`, `writematrix`, `csvread`, `csvwrite`, `dlmread`, with a header row
      skipped.
- [ ] `readtable` and `writetable` with column names, together with a real `table`
      (see Phase 4). Pandas is excluded from the bundle, so it is built on numpy.
- [ ] `fopen`, `fclose`, `fgetl`, `fgets`, `fprintf(fid, …)` to a file, `fscanf`,
      `textscan`, `fread`, `fwrite`.
- [ ] `jsondecode` and `jsonencode`.
- [ ] `xlsread`/`readtable` on `.xlsx`. This needs openpyxl, a new dependency, so
      decide first. **M**

**Statistics and linear algebra** **S**
- [ ] `var`, `mode`, `cov`, `corrcoef`, `prctile`, `quantile`, `skewness`,
      `kurtosis`, `movmean`, `movmedian`, `smoothdata`, `detrend`.
- [ ] `normpdf`, `normcdf`, `norminv`, `ttest`, `regress`. `fitlm` with its summary
      table is **M**.
- [ ] `svd`, `qr`, `lu`, `chol`, `pinv`, `null`, `orth`, `expm`, `logm`, `sqrtm`,
      `cross`, `dot`, `cond`, `trace`, `triu`, `tril`, `circshift`, `sub2ind`,
      `ind2sub`.
- [ ] `randi`, `randperm`, `rng`.

**Strings** **M**
- [ ] `strsplit`, `strjoin`, `strtrim`, `strrep`, `regexp`, `regexprep`, `contains`,
      `startsWith`, `endsWith`, `split`, `join`, `upper`, `lower`, `pad`.
- [ ] `sprintf` and `num2str` over cell arrays. Decide how far `"…"` string arrays go
      beyond `char` (Phase 4).

**Cells and structs** **S**
- [ ] `cellfun` and `arrayfun` (with `'UniformOutput', false`), `cell2mat`,
      `struct2cell`, `cell2struct`, `rmfield`, `orderfields`, `isequal`,
      `ismember` on cells of text.

**Signal processing for measured data** **M**
- [ ] `filtfilt`, `fir1`, `fir2`, `designfilt` (the common forms), `pwelch`,
      `periodogram`, `spectrogram`, `resample`, `decimate`, `interp`, `xcorr`,
      `impz`, `grpdelay`.
- [ ] Windows: `hann`, `hamming`, `blackman`, `kaiser`, `window`.
- [ ] Start from the `_iir`/`freqz` code in `matlab_runtime.py`.

**Fitting, optimisation, integration** **S–M**
- [ ] `lsqcurvefit`, `lsqnonlin` (on `scipy.optimize.least_squares`), `fsolve`,
      `fminunc`, `fmincon` (on `minimize`), `linprog`, `intlinprog` (`milp`),
      `quadprog`.
- [ ] `integral`, `integral2`, `quadgk`, `polyder`, `polyint`, `spline` and `pchip`
      as functions, `interp2`, `griddata`.
- [ ] `fit` with the common `fittype` names (poly1…poly9, exp1, exp2, power1, sin1).
      A `cftool` GUI is **L** and waits.

**Workspace and system helpers** **S**
- [ ] `who`, `whos`, `which`, `exist` with a type, `dir`, `ls`, `delete`, `copyfile`,
      `movefile`, `mkdir`, `system`, `getenv`.
- [ ] `clock`, `now`, `datestr`, `datetime` (Phase 4), `pause` that honours Stop.
- [ ] `dec2bin`, `bin2dec`, `dec2hex`, `factorial`, `nchoosek`, `primes`, `isprime`,
      `gcd`, `lcm`, `erf`, `gamma`, `beta`.

## Phase 2 — Simulink for daily use

The engine is ahead of the editor and of its links to the console. The first five items
change daily use the most.

- [ ] **Block parameters take workspace expressions.** `Kp`, `2*pi*f` and `[1 2 3]`
      instead of a `QDoubleSpinBox` (`ui/sim/params.py`), evaluated in the console
      workspace at compile time, with a clear error naming the block and the
      parameter. This opens model variables and parameter sweeps. **M**
- [ ] **To Workspace output reaches the console.** `SimResult.workspace` is filled
      but dropped in `ui/sim/sim_tab.py` `_on_finished`. Add a From Workspace block
      too. **S**
- [ ] **`sim`, `open_system`, `load_system`, `set_param`, `get_param` in MATLAB
      syntax,** returning a `SimulationOutput`-like struct (`out.tout`, `out.yout`,
      logged signals). **M**
- [ ] **A Fcn / MATLAB Function block** whose body is a MATLAB expression or a
      function, run through the same translator. Watch the per-step cost. **M**
- [ ] **Logic blocks:** Relational Operator, Logical Operator, Compare To Constant,
      Compare To Zero, Bitwise Operator. **S**
- [ ] **Missing common blocks:** Memory, Discrete-Time Integrator, Discrete FIR/Filter,
      Repeating Sequence, Signal Builder, Counter, Data Store Read/Write, XY Graph,
      2-D Lookup Table, Prelookup. **M**
- [ ] **Conditionally executed subsystems:** enabled, triggered, If/Switch Case
      action, and an Integrator reset port. **M–L**
- [ ] **Goto/From.** Buses were cut on purpose; reconsider them after Goto/From. **M**
- [ ] **Diagram editing:** rotate and flip, text annotations, signal labels on wires,
      Create Subsystem from Selection, draggable wire bends. **M**
- [ ] **Export:** the diagram to SVG/PNG/PDF and to the printer, and scope data to CSV
      and `.mat`. **S**
- [ ] **Compare runs:** overlay the last N runs in a scope (deferred in PLAN Part 6).
      **M**
- [ ] **Sample models:** a few `.fmdl` files from the courses (DC motor, cruise control,
      inverted pendulum, PID loop with saturation), reachable from File ▸ Examples.
      There are none in the repo now. **S**
- [ ] **Later:** masks and block libraries, referenced models, MIMO `linearize`, live
      parameter sliders during a run, and a user block API (S-function
      equivalent). **M each**

## Phase 3 — Plotting

Plotting stops at 2-D lines and bars, and figures are a large share of what people use
MATLAB for.

- [ ] `scatter`, `errorbar`, `area`, `fill`, `patch`, `pie`, `text`, `xline`, `yline`,
      `yyaxis`, `tiledlayout`/`nexttile`, `annotation`, `colororder`. **M**
- [ ] 3-D: `plot3`, `surf`, `mesh`, `contour`, `contourf`, `quiver`, `meshgrid` (check
      it exists), `view`, `zlabel`, rotate with the mouse. **L**
- [ ] Images: `imagesc`, `image`, `imshow`, `colormap`, `colorbar`, `caxis`. **M**
- [ ] A data cursor and a hover readout in `ui/console/figure_view.py`. **M**
- [ ] Export figures to PDF and EPS alongside PNG/SVG, and `exportgraphics`. **S**
- [ ] Let annotations typed at a later prompt reach the current figure (`title`,
      `legend` on a separate line), as MATLAB allows. Today they must be on the
      plot's line. **M**

## Phase 4 — Running other people's MATLAB code

This is what decides whether a colleague's `.m` file runs.

- [ ] An error for an unknown name that says when the function is a MATLAB one Evans
      does not have yet, so the user knows they haven't mistyped it, with a link to
      a "not in Evans" list. **S**
- [ ] `eval`, `evalin`, `feval`, `str2func`, `func2str`, `exist`, `inputParser`,
      `validateattributes`, `nargin(fn)`. **M**
- [ ] Nested functions that share the parent's variables. **M**
- [ ] Integer and single types: `int8`…`uint64`, `single`, `logical()`, `double()`,
      with saturation. Images and hardware data depend on them. **M**
- [ ] `containers.Map`. **S–M**
- [ ] A real `table`: constructor, `T.col`, row filtering, `height`, `width`,
      `sortrows`, `join`; then `datetime`, `duration`, `timetable`. **L**
- [ ] String arrays as their own type (`numel("abc") == 1`, `["a" "b"]`), distinct
      from `char`. **M**
- [ ] N-D arrays (`zeros(2,2,2)`, `cat(3,…)`, `permute`, `squeeze`). The 2-D
      assumption runs through the runtime, so this is a large change. **L**
- [ ] `classdef` (properties, methods, constructors, handle classes). **L**
- [ ] `sparse`, `speye`, `nnz` and the iterative solvers, on `scipy.sparse`. **M**
- [ ] `.mat` v7.3 (HDF5) through h5py, a new dependency. **M**
- [ ] Save live scripts back to `.mlx`, not only to plain live `.m`. **M**
- [ ] `uigetfile`, `uiputfile`, `inputdlg`, `msgbox`, `questdlg`, `waitbar`, `ginput`,
      and `input` at the console prompt. **M**

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

- [ ] A Linux build (AppImage or a `.deb`). CI already tests on Ubuntu. **M**
- [ ] macOS notarisation, and an Intel build if anyone asks. **M**
- [ ] Windows code signing (deferred on purpose until there are more users; a Certum
      cloud certificate is the plan). **S** once bought.
- [ ] Auto-update on macOS (Windows has it). **M**
- [ ] A reference corpus of real MATLAB outputs (inputs and saved results, run once
      on a MATLAB licence) checked in CI, beside the closed-form golden tests. **M**
- [ ] A startup-time test and budget, and a size budget. The `dist/Evans` folder is
      343 MB. **S**
- [ ] A `CHANGELOG.md` in the repo; patch notes live only on the site now. A stated
      stability policy, and a 1.0 once Phases 1–2 land. **S**
- [ ] Fix the `pyproject.toml` comment that still says "432 tests". **S**
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
