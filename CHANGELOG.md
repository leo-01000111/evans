# Changelog

Every release of Evans, newest first. The same notes, with links, are on the
site's patch notes page. The layout follows [Keep a Changelog](https://keepachangelog.com/);
versions are not yet [semantic](https://semver.org/) (see `docs/1.0-PROPOSAL.md`).

A release adds its section here and to `site/pages/patch-notes.html`. Work that
is on `main` but not released yet goes under Unreleased.

## Unreleased

### Changed
- **Writing into a numeric array no longer copies it.** `a(k) = v`, `A(i,j) = v`,
  `A(:,k) = col` and `A(i,j,k) = v` change the array in place when no other
  variable, container, function or view holds it, so filling a pre-allocated
  array in a loop takes time in proportion to its length: 10⁵ writes went from
  about 16.5 s to 1.9 s. The array is still copied whenever MATLAB's value
  semantics need it (`b = a`, `c = {a}`, `s.f = a`, function arguments,
  anonymous-function captures, `ans`, `for v = a`, maps, tables, object
  properties, and views such as `a(:)`, `a'` and `reshape(a, …)`). Growing past
  the end, deleting with `= []` and a change of class still make a new array.

## 0.23.0 - 2026-11-11

A window for every Scope.

### Added
- **A Scope block opens in its own window.** Double-click a Scope block on the
  Model tab and its signals, and only those, are plotted in a window of their
  own, titled after the block and the model. Several can be open side by side;
  each redraws when a run finishes, and double-clicking the block again brings
  its window forward. Copy (Ctrl+C), Export… and "Compare with earlier runs"
  work there as in the scope below the canvas. The windows close when another
  model is opened. A Scope block's parameters are in the inspector.

### Changed
- **The scope below the canvas is now the global scope**, with every logged
  signal, and is folded away behind a **Show global scope** button. Whether it
  is open is remembered.

## 0.22.0 - 2026-11-11

Blocks that look like what they do.

### Added
- **Blocks on the Model tab look like what they are.** Gain is a triangle
  pointing along the signal, Sum a circle with its signs at the ports, Product a
  circle with × or ÷, Integrator a rounded box with 1/s. Saturation and Switch
  show their characteristic, Step, Ramp and Sine their waveform. Mux and Demux
  are a narrow bar, Goto and From flags, Inport and Outport pills, and a
  Subsystem has its name on a plate across the top. Ports stay where they were,
  so wiring and existing models are unchanged; rotate, flip, selection and the
  diagram exports all follow the shape. **View ▸ Classic block boxes** brings
  back the plain rectangles and is remembered.

## 0.21.0 - 2026-11-11

No more lost work on quit, and a new licence.

### Changed
- **Evans is now licensed under the GNU GPL, version 3 or later** (it was MIT).
  You can still use, share, change and sell it; anything distributed that is
  built on Evans must stay open under the same licence. Releases up to 0.20.0
  remain available under MIT. Cedric stays all rights reserved.
- **Evans asks before quitting or replacing an unsaved model or live script.**
  The Model tab and the Live editor now show an unsaved mark (the live script's
  file name; a file label at the Model tab's bottom right). Quit settles script
  tabs, the live script and the model in turn with Save / Discard / Cancel; a
  Save whose file dialog is cancelled counts as Cancel. Open, Open Recent,
  File > Examples and double-clicking a workspace model ask before replacing
  unsaved content. Running cells or a simulation does not count as a change.

## 0.20.0 - 2026-11-11

A new model file, and a crash fixed.

### Changed
- **Models are saved as `.evx`.** New models get the new extension. Your `.fmdl`
  files keep opening as before. The first time you press Save on one, Evans asks
  once whether to save it in the new format; if you say yes it writes `name.evx`
  beside it and never touches the original. Save As offers both types, so you
  can still save a `.fmdl` for someone on an older Evans.
- **Older versions of Evans cannot open `.evx` files.** If you share a model
  with someone who has not updated yet, use Save As > `.fmdl`.
- **The Model tab remembers its file.** Save writes to the file the model came
  from, and Save As asks where. A model is written to a temporary file first and
  swapped in, so a failed save leaves the old file whole.
- Opening a model by name (`open_system`, `sim`, recent files) looks for `.evx`
  first, then `.fmdl`. Double-clicking either type opens Evans.

### Fixed
- **A crash after closing a 3-D figure.** Closing or redrawing a 3-D plot or pie
  right after clicking a data tip, turning it or switching theme could make
  Evans close without warning a little later. A redraw meant for a figure that
  is gone is now skipped.

## 0.19.0 - 2026-11-10

Your unsaved work survives a crash.

### Added
- **Autosave for crash recovery.** Every minute, Evans keeps a copy of any script
  tab, live script or model diagram with unsaved changes, in its own folder,
  never over your files. If Evans closes without being asked to, the next start
  offers them back: Restore, Discard, or ask next time. Restored documents come
  back unsaved, so nothing is written to your files until you save. The last few
  versions of the model are kept.
- **File > Autosave for crash recovery** turns it off, or sets it to every 30
  seconds, 1, 2 or 5 minutes.

### Known issues
- Quitting does not yet ask about an unsaved model or live script, only about
  script tabs. Save them before you quit.

## 0.18.0 - 2026-11-09

Editing and plotting polish.

### Added
- **Expand Subsystem.** Right-click a subsystem on the canvas to put its blocks
  back in the parent diagram, the inverse of Create Subsystem. One undo step.
  Subsystems with an enable, trigger or action port are refused.
- **Blocks snap by port.** While you drag a block, its ports line up with the
  ports they are wired to, with a guide through the pair. Hold Alt to turn it off.
- **Copy and export from the scope.** Ctrl+C or the right-click menu copies the
  plot as an image and the visible data as tab-separated text. Export now writes
  PNG, SVG, PDF and EPS, with a chosen size, resolution and theme.
- **Data tips on 3-D axes.** Click a point on a 3-D plot to pin its X, Y and Z,
  and click the tip to remove it.
- **Eleven help pages** for plotting commands that had none: `histogram`, `stem`,
  `stairs`, `semilogy`, `loglog`, `saveas`, `print`, `sgtitle`, `close`, `clf`
  and `gcf`.

### Changed
- **Figures have numbers.** `figure(n)` goes back to figure `n` (or opens it),
  `gcf` follows the tab you select, and `clf` empties the current figure in place.
- **`close` with no argument closes the current figure,** as in MATLAB. It used
  to close all of them; `close all` still does.
- **Switching theme no longer redraws a 3-D figure.** The view angle, pinned tips
  and colour map stay as they were.

## 0.17.2 - 2026-11-09

The first installable release of the 0.17 series. Versions 0.17.0 and 0.17.1
were tagged but never published: the build stops when any platform's tests
fail, and one Mac-only test did. Everything in those two entries is in this
release.

### Fixed
- **The Mac test suite passes again.** A check on the title of a message box
  assumed a title bar, which Mac alerts do not have. It was the test that was
  wrong, not the dialogs.

## 0.17.1 - 2026-11-09

A wording fix for Mac users. Tagged, never published (see 0.17.2).

### Fixed
- **The Mac update prompt says what to do.** It used to say the copy "runs from
  source". It now says the Mac app cannot update itself yet, and to download the
  new disk image from the release page and drag Evans to Applications.

## 0.17.0 - 2026-11-09

The rest of the language work for running other people's MATLAB code: real
types, tables, classes, more than two dimensions, and errors that point at the
right line. Tagged, never published (see 0.17.2).

### Added
- **Integer and single types.** `int8` to `uint64` and `single`, with saturation
  and MATLAB's mixing rules, plus `cast`, `intmax`, `intmin`, `idivide`, the
  `bit*` functions and `zeros(..., 'int8')`.
- **String arrays.** `"abc"` is a string, separate from `'abc'`: `numel("abc")`
  is 1, `+` joins, and `strlength`, `string` and `isstring` exist.
- **N-D arrays.** `zeros(2,2,2)`, indexing with any number of subscripts, `cat`,
  `permute`, `squeeze`, `reshape`, `repmat`, `meshgrid` and `ndgrid` in 3-D,
  reductions along a dimension, and display as `ans(:,:,k)` pages.
- **Tables, dates and times.** `table` with brace indexing, assignment,
  `sortrows`, `join`, `groupsummary` and more; `datetime`, `duration`,
  `timetable`, and `fitlm` with its summary.
- **`classdef`.** Value and handle classes, properties with attributes, `get.`
  and `set.` methods, inheritance, operator overloading, events and enumerations.
- **Sparse matrices and iterative solvers** (`sparse`, `pcg`, `gmres`, `eigs`),
  **MAT-files in v7.3 format**, saving live scripts back to `.mlx`, and the
  dialog functions (`uigetfile`, `inputdlg`, `questdlg`, `waitbar`, `ginput`,
  `input`).
- **`inputParser`** and **nested functions** that share their parent's variables.

### Changed
- **Errors in your own functions read like MATLAB's.** `Error using f (line 2)`,
  then `Error in g (line 5)` with the source line, for every caller down to the
  script. Too many or too few arguments say so. A script named with dots, such
  as `C.3.2.m`, explains why it cannot be called by name.

### Known issues
- Not yet: arrays of objects, `subsref` overloading, time zones, categorical
  arrays and datetime axes in plots.

## 0.16.2 - 2026-11-09

A crash fix in the Model tab, and signal names that carry through to the scope.

### Added
- **A named signal is its name in the scope.** Name a wire and the scope's
  legend, channel list, cursor readout and XY labels show that name instead of
  `G.out`. Names set inside a subsystem, or on its output, are kept when the
  model is flattened for a run.

### Fixed
- **Selecting a wire no longer crashes the app.** Clicking the movable middle
  part of a wire and releasing without dragging raised an error inside the
  canvas, which closed Evans. The click now just selects the wire, and Delete
  removes it.

## 0.16.1 - 2026-11-09

Functions that pass their extra arguments on, such as the `ore` helper from a
signal-processing lab, now run.

### Fixed
- **`c{:}` and `varargin{:}` expand into separate arguments.** `f(a, b,
  varargin{:})`, `f(c{:})`, `[c{:}]` and `{c{:}, 4}` now pass or join each
  element, and an empty cell adds nothing. Before, the whole list arrived as one
  value and the call failed with a Python `TypeError`.
- **`@(varargin)` and `@(k, varargin)` accept any number of arguments.**
- **Huge matrices no longer freeze the window.** A matrix with more than 10 rows
  or 100 columns prints its corners and a size line, and a live script's output
  box stops at 500 lines. A stereo `audioread` without a semicolon used to print
  over a million rows.

### Known issues
- Errors from your own functions still show Python wording and no function
  name (fixed in 0.17.0).

## 0.16.0 - 2026-11-09

The first part of running other people's MATLAB code: scripts that build code
from text, keep lookup tables, or name a function Evans does not have.

### Added
- **A clear error for MATLAB functions Evans lacks.** Typing `accumarray` or
  `histcounts` now says it is a MATLAB function Evans does not have yet, so
  nobody hunts for a typo. The new *Not in Evans* help page lists them.
- **`eval`, `evalin('base', ...)`, `feval`, `str2func`, `func2str` and
  `nargin(fn)`.** `func2str` returns an anonymous function as MATLAB prints it.
  `eval` inside a function can read its variables but stops with an error
  rather than silently lose an assignment.
- **`containers.Map`.** Text or numeric keys, `m(key) = value`, `keys`,
  `values`, `isKey`, `remove`, `Count` and the `m.keys()` method form. A map is
  a handle, so two names for it share one table.
- **`validateattributes`, `magic` and `fileread`.** `magic` gives MATLAB's own
  squares. The operators are also functions now, so `@plus` and
  `feval('minus', a, b)` work.

### Fixed
- **A function handle held in a variable can be passed as an argument at the
  prompt.** `cellfun(h, a, b)` used to call `h` with no inputs when `h` had been
  made on an earlier line.
- **A handle shows as MATLAB writes it,** `@(x,y)x.^2+y`, instead of a Python
  function address.

### Known issues
- Not yet: `inputParser`, nested functions, integer types, string arrays,
  `table` sorting and joining, N-D arrays, `classdef`, `sparse` and the dialog
  functions (all added by 0.17.0).

## 0.15.1 - 2026-11-04

Two layout fixes in the analysis panes.

### Fixed
- **Frequency analysis no longer scrolls as a page.** Only its control column
  scrolls now, so the Bode, Nyquist and Nichols plots fill the pane instead of
  growing to fit the controls.
- **Pane dropdowns fit their text.** The view and system pickers in a pane
  header are as wide as the name they show, instead of clipping long names with
  room to spare beside them.

## 0.15.0 - 2026-11-04

The console draws the closed-loop grids of the frequency charts, the Nichols
chart's gain contours are drawn right, and the analysis panes warn you off views
that do not mean anything for the system you picked.

### Added
- **M-circles and the Nichols grid in the console.** `grid on` after `nyquist`
  draws the M-circles of constant closed-loop gain, labelled in dB; after
  `nichols`, or with the new `ngrid`, it draws the Nichols chart's closed-loop
  gain and phase contours. `ngrid('new')` starts held axes for the plot that
  follows, and `nyquistoptions`' `Grid` is honoured.
- **Warnings in the analysis panes.** The system picker marks the combinations
  that make no practical sense, such as a Nyquist plot or root locus of the
  closed loop T, or the step response of the open loop L. They still draw; the
  tooltip says why the result means nothing.
- **More room for the panes.** The pane count buttons sit at the right of the
  top pane's header instead of on a row of their own, and Settings > Show
  snapshot bar hides the snapshot row.

### Fixed
- The Nichols chart's gain contours above 0 dB were drawn as open arcs, only
  their upper half. They are the closed loops round the critical point they
  should be, on the Frequency tab as well as in the console.

## 0.14.0 - 2026-11-03

Figures go well beyond lines and bars: 3-D surfaces you turn with the mouse,
images and colour maps, scatter, error bars, pies, contours, tiled layouts and a
second y axis. Hover reads a figure out, a click pins a data tip, and figures
save as PDF and EPS for papers. Two changes alter how existing scripts look;
they are listed first.

### Changed
- **Line colours are honoured.** `plot(x, y, 'r--o')` draws a red line, and
  `'Color'`, `'LineWidth'`, `'MarkerSize'` and `'DisplayName'` take effect.
  Before, the colour letter was ignored for the theme's colours, which are still
  used when a script gives none. Line specs can also be written in any order,
  `'o-r'` as well as `'r-o'`.
- **The prompt keeps the last figure, as MATLAB does.** A `title`, `legend`,
  `xlabel` or `hold on` typed on a later line reaches the figure drawn last,
  which is redrawn in its tab. Before, it had to be on the plot's own line. Once
  you close the figure, the next plot starts afresh.

### Added
- **More kinds of plot.** `scatter`, `errorbar`, `area`, `fill`, `patch`, `pie`,
  `quiver`, `contour` and `contourf`; stacked bars with `bar(..., 'stacked')`,
  and `barh` now really draws its bars sideways.
- **3-D axes.** `plot3`, `scatter3`, `surf`, `mesh` and `quiver3`, with `view`,
  `zlabel`, `zlim` and `shading`. Drag to turn the axes, right-drag to zoom.
- **Images and colour.** `imagesc`, `image` and `imshow`, with `colormap`
  (`jet`, `turbo`, `hot`, `gray` and the rest), `colorbar` and `caxis`. `parula`
  is MathWorks' own map, so Evans shows viridis, the open map closest to it.
- **Layouts and annotation.** `tiledlayout` and `nexttile`, a second y axis with
  `yyaxis`, `text`, `xline`, `yline`, `annotation` and `colororder`. An axes from
  `nexttile`, `subplot` or `gca` can be passed first to `plot`, `title` and the
  rest.
- **Reading a figure.** Hover over a curve, a marker, a contour line or an image
  for its values; click to pin a data tip there, and click the tip to remove it.
- **PDF and EPS.** `exportgraphics`, `saveas`, `print` and the figure's Save
  write PDF and EPS drawn for print, dark on white, as well as PNG, JPEG, TIFF
  and SVG. `'Resolution'` and `print -r300` set a picture's resolution.
- **36 new help pages**, one for each of these commands and for `bar`.

### Known issues
- Plot handles: `h = plot(...)` followed by `set(h, ...)` or `h.Color = ...`.
  Give the properties as name-value pairs in the plot call instead.
- Colour (m-by-n-by-3) images and `imread`, which need N-D arrays (N-D arrays
  arrived in 0.17.0).

## 0.13.0 - 2026-11-03

Every known bug from 0.12 is fixed, Excel workbooks open at the console, and
every console command has a help page. Two of the fixes change what existing
models compute; they are listed first.

### Changed
- **A Unit Delay is one sample late, as in Simulink.** Fed by a continuous
  signal, it showed the sample it had just taken, so it acted as a zero-order
  hold. It now shows the sample before, from any kind of signal.
- **Discrete blocks in a chain add no extra delay.** When several discrete
  blocks act at the same instant, each now sees the new output of the ones
  feeding it, as Simulink orders them. A Zero-Order Hold feeding a Discrete
  Transfer Fcn, or a Discrete-Time Integrator, used to hand over the sample
  before. A discrete loop with no delay in it, which Simulink refuses, now runs
  with a warning.

### Added
- **Excel workbooks.** `readmatrix`, `readtable`, `writematrix` and `writetable`
  read and write `.xlsx` files, with the `'Sheet'` and `'Range'` options.
  `xlsread`, `xlswrite` and `sheetnames` are new. The old `.xls` format is not
  supported; save it as `.xlsx`.
- **A help page for every console command.** The 93 functions that had none,
  from `fread` and `designfilt` to `gamma` and `datenum`, now have one with a
  runnable example. The special functions have a group of their own in the index.
- **`designfilt` filters work everywhere.** `filter(d, x)`, `freqz(d)`,
  `impz(d)` and `grpdelay(d)` take a designed filter, as `filtfilt` already did.

### Fixed
- **A PID block with *Limit output* stalled the run** once its output reached the
  limit and the integrator had to ride it. It now finishes in about a second,
  and the output never passes the limit.
- **A fixed-step run (`ode1` to `ode5`) stopped one output step short** of the
  stop time. It now logs the last instant.
- **An anonymous function read its variables when it was called, not when it was
  made.** After `k = 2; f = @(x) k*x; k = 10;`, `f(1)` gave 10; it gives 2, as
  in MATLAB.
- **Growing a cell or struct in a loop was slow.** `c{end+1} = k` copied the
  whole cell each time, so 10,000 of them took 3.5 seconds. A cell or struct no
  other variable holds is now written in place, so the same loop takes under a
  tenth of a second.

## 0.12.1 - 2026-10-30

The first download of everything listed under 0.12.0, which was tagged but never
built: its tests failed on newer libraries, so no installer was made.

### Fixed
- `logm` and `sqrtm` stopped with an error under SciPy 1.18 and later. They work
  with old and new SciPy alike.

## 0.12.0 - 2026-10-30 (not released, see 0.12.1)

The Model tab and the console now work together the way Simulink and MATLAB do,
the block library has most of what everyday models use, and the console gained
the functions logged data needs.

### Added on the Model tab
- **Parameters from the workspace.** Any numeric block parameter takes a MATLAB
  expression: a Gain of `Kp`, a frequency of `2*pi*f`, a denominator of
  `[1 2 1]`. It is evaluated in the console's workspace each time the model
  runs, so changing `Kp` at the prompt and pressing Run uses the new value. A
  missing variable stops the run with the block, the parameter and the text that
  failed.
- **Simulink commands at the console.** `sim('model')` runs a model by name, from
  the canvas or from `model.fmdl`, and returns `out.tout`, `out.yout` (from
  top-level Outports) and one field per To Workspace block. `new_system`,
  `load_system`, `open_system`, `save_system`, `get_param`, `set_param`,
  `add_block`, `add_line`, `delete_block` and `find_system` build and change
  models from a script, with Simulink's names for blocks and parameters. A loop
  that sets `Kp` and calls `sim` is a parameter sweep.
- **Runs reach the workspace.** Pressing Run leaves the output in the console as
  `out`. To Workspace saves as a timeseries, a structure with time, or an array;
  From Workspace reads `[t, u]` or either structure. Stop time, solver and step
  are saved with the model.
- **MATLAB code in a block.** The Fcn block applies an expression such as
  `u(1)*sin(u(2))`; the MATLAB Function block runs a whole function, its
  arguments and outputs becoming its ports.
- **Conditional subsystems.** An Enable, Trigger or Action Port block inside a
  subsystem makes it run only while enabled, once per trigger edge, or when an
  If or Switch Case block picks it. States are held or reset, outputs held or
  reset while it does not run. The Integrator has a reset port.
- **Twenty-nine new blocks in all.** Besides those above: Relational and Logical
  Operator, Compare To Constant and To Zero, Bitwise Operator, Memory,
  Discrete-Time Integrator, Discrete FIR and Filter, Counter, Repeating
  Sequence, Signal Builder, 2-D Lookup Table, Prelookup, XY Graph, Goto/From,
  and Data Store Memory, Read and Write.
- **Editing.** From the right-click menu: rotate and flip a block, add a text
  note, name a signal on its wire, drag a wire's bend, and Create Subsystem from
  Selection. Each is one step of undo.
- **Export and compare.** The diagram exports as SVG, PDF or PNG, or prints; the
  scope's signals export as CSV or `.mat`. The scope keeps the last five runs and
  can draw them under the new one, and an XY Graph gets its own view.
- **Examples.** File > Examples opens a DC motor speed loop, cruise control, an
  inverted pendulum, and a PID with a saturating actuator (windup and
  anti-windup side by side).

### Added at the console
- **Data files.** `readmatrix`, `readtable`, `writematrix`, `writetable` and the
  older `csvread` and `dlmread`, with a header row skipped; `fopen`, `fprintf`
  to a file, `fgetl`, `fscanf`, `textscan`; `jsondecode` and `jsonencode`; a
  small `table`.
- **Statistics and linear algebra.** `var`, `cov`, `corrcoef`, `prctile`,
  `movmean`, `smoothdata`, `detrend`, `normcdf`, `ttest`, `regress`; `svd`,
  `qr`, `lu`, `chol`, `pinv`, `expm` and the rest; `randi`, `randperm`, `rng`.
- **Text, cells and structs.** `strsplit`, `strjoin`, `regexp`, `regexprep`,
  `contains` and their kin; `cellfun`, `arrayfun`, `cell2mat`, `struct2cell`,
  `isequal`, `ismember` on text.
- **Signals, fitting and optimisation.** `filtfilt`, `fir1`, `designfilt`,
  `pwelch`, `spectrogram`, `resample`, `xcorr` and the windows; `lsqcurvefit`,
  `fsolve`, `fmincon`, `linprog`, `integral`, `spline` and `fit`.
- **The system.** `who`, `whos`, `dir`, `exist`, `system`, dates (`datestr`,
  `datenum`), and number functions from `nchoosek` to `dec2bin`.

### Fixed
- **Answers that were silently wrong.** `{1,'a';2,'b'}` is 2x2, not 1x4;
  `struct('a',{1,2})` is a 1x2 struct array; `error('my:id', ...)` keeps its
  identifier; `persistent` and `global` work; and copying a cell or struct no
  longer shares it, so changing the copy leaves the original alone.

## 0.11.0 - 2026-10-27

### Added
- **Symbolic maths.** `syms s t` makes symbolic variables, and from then on
  formulas stay exact and print the way MATLAB prints them. `laplace` and
  `ilaplace` transform both ways, `simplify`, `expand`, `factor`, `partfrac` and
  `subs` work on formulas, and `diff`, `int`, `limit`, `taylor` and `solve` do
  the calculus and the equations. Symbolic matrices work too, so
  `C*inv(s*eye(2) - A)*B` gives a transfer function by hand. `numden` and
  `sym2poly` turn a formula into a `tf`, `double` and `matlabFunction` turn it
  into numbers, and `fplot` draws it. Each has a help page.

### Fixed
- A Model-tab simulation without discrete blocks showed its progress bar at 0 %
  until the run was over, and Stop waited for the end. Both now work while it
  runs.

### Known issues
- Symbolic functions such as `syms y(t)`, and so `dsolve`, are not supported yet.

## 0.10.1 - 2026-10-23

Commands that printed a wrong number without any warning now give MATLAB's
answer, or stop with an error that says why.

### Fixed
- **Discrete models.** `damp` maps each pole to the s-plane before giving its
  damping and frequency, `dcgain` is the gain at `z = 1`, `errconst` takes its
  limits there too, `freqresp` evaluates on the unit circle, and `bode` stops at
  the Nyquist frequency.
- **Building models.** `ss(A, B, C, D, Ts)` keeps the matrices as the discrete
  ones, as MATLAB does, instead of discretising them again. `zpk(z, p, k, Ts)`
  is discrete. `tf(..., 'InputDelay', T)` no longer builds a discrete model with
  sample time `T`; Evans has no exact delays yet, so it stops and suggests
  `pade`.
- **Analysis.** `routh` handles a row of zeros and reports roots on the
  imaginary axis as marginal, not stable. `stepinfo` of an unstable system gives
  `NaN`, with `Peak` and `PeakTime` `Inf`. The delay margin is right for a
  negative phase margin. `dcgain` gives the whole matrix for several inputs and
  outputs, and cancels the common factor in `s*H`. `rlocus(G, k)` uses the gains
  in `k`, and `sisotool(G, C)` opens on the compensator `C`.
- **Arrays.** `sum`, `mean`, `cumsum`, `max`, `min` and the rest return MATLAB's
  shape along a dimension: `sum(A, 2)` is a column, `sum([1 2 3], 1)` the row
  itself. `sort(A, 2)` sorts rows, and complex values sort by magnitude.
  `logspace(a, pi)` ends at pi. `clear K*` and `clear -regexp` remove what they
  match. `zeros(2, 3, 4)` and `repmat('ab', 2, 1)` stop with an error instead of
  a smaller answer: N-D arrays and multi-row text are not supported yet.

## 0.10.0 - 2026-10-22

### Added
- **Help inside Evans.** F1, Help > Documentation and Cedric on the rail open a
  help window of its own instead of the website: a page for every console
  command and the MATLAB basics scripts use, each with the ways it is called,
  what it does, an example you can run in the console with one click, and links
  to related pages. The index on the left is searchable.
- **Several scripts at once.** The Script tab holds each script in a tab of its
  own, Untitled until it is first saved. A dot marks a tab with unsaved changes,
  and closing it or quitting Evans asks whether to save first. The tabs that
  were open come back the next time Evans starts, each at the line you left it
  on. Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S and Ctrl+W act on scripts while a
  script has the keyboard.
- **Hover for syntax, Ctrl+click to go.** Resting the mouse on a function name
  shows how it is called; for one you wrote, its `function` line and the comment
  under it. Holding Ctrl underlines a name that leads somewhere, and Ctrl+click
  goes there: a local function's line, a `.m` file in a new tab, a built-in's
  help page. It works in scripts, live scripts, the console prompt and its output.
- **The debugger follows into function files.** Breakpoints work in any open tab.
  A run pauses inside a function file, Step in opens the file's tab, Stop works
  inside one, and a pause shows the Script tab at the paused line.
- **Cedric answers questions.** A side panel asks a free AI model on OpenRouter
  about the code at hand: the selection or the current `%%` section, the names
  and sizes of your variables (never their values) and the last error. He can
  propose an edit, shown as a change you apply or ignore, or a console command,
  which runs only when you click Run. Select some code or an error and an *Ask
  Cedric* button offers to explain or fix it. He needs a free OpenRouter key in
  the `OPENROUTER_API_KEY` environment variable; Evans never saves it.

### Fixed
- `step` on a state-space model, `lsim` without an initial state, and
  `poly(roots(p))` no longer fail.
- Before a run, open `.m` files with unsaved changes are offered for saving,
  since the run calls them from disk.

## 0.9.8 - 2026-10-21

### Added
- **A Mac app.** `Evans-0.9.8-macos-arm64.dmg` is on the release, for Macs with
  Apple Silicon on macOS 13 or newer: open it and drag Evans onto Applications.
  It is not notarised by Apple yet, so the first launch needs *Open Anyway* in
  System Settings > Privacy & Security. An Intel Mac or an older macOS can still
  run Evans from source.
- On a Mac, `.fmdl` models open in Evans from Finder, tooltips show shortcuts
  the Mac way, Control-C stops the console as it does in MATLAB, Control-` opens
  the command window, TeX from MacTeX or Homebrew is found for PDF export even
  when Evans is opened from Finder, and `sound()` plays.
- The Mac app checks for a newer release once a day and offers the download
  page. It cannot update itself yet.

### Changed
- **The lessons are gone**: the Lessons menu, the lesson panel and the lessons
  page on the site. The self-test still checks the same closed-form results
  (exact margins, the critical gain of 8 at w = sqrt(3), second-order overshoot,
  the waterbed integral), now directly.
- A release is published only once both the Windows and the Mac build have
  passed their own self-test.
- Cedric, the shrimp on the splash and the rail, is not under the MIT licence:
  he is all rights reserved (`LICENSE-CEDRIC`). The code stays MIT. Both
  licences now ship inside the build.

## 0.9.7 - 2026-10-21

0.9.6 was tagged but never published: the new macOS test run stopped it. This
release carries everything listed under 0.9.6, plus the two fixes below.

### Fixed
- On macOS, settings saved under the old FauxMatlab name were never carried
  over, because the check for an empty settings store also saw the system-wide
  preferences.
- On macOS, a double pole such as `(s+1)^2` was sketched in the Bode asymptotes
  as two -20 dB/decade corners a hair apart, with a sliver of a phase ramp
  between them, instead of one -40 dB/decade corner. Corners within a relative
  1e-4 of each other are now one corner on every system.

### Changed
- The tests now run on macOS as well as Windows and Ubuntu. There is still no
  Mac installer; on a Mac, Evans runs from source.

## 0.9.6 - 2026-10-21

Tagged, never published (see 0.9.7).

### Added
- **The console speaks MATLAB.** Lines typed at the prompt go through the Script
  tab's translator, so `sys = tf(K, [T 1])`, `s^2` and `x(end)` work as written.
  A `for`, `if` or `while` stays open until its `end` (Escape drops it), and a
  bare variable echoes as `x = 5`. Python still runs: a line with `import`,
  `def`, `**` or `x[0]` goes to Python as before.
- MATLAB is the default elsewhere too: Auto in the Script tab picks MATLAB for a
  script that reads as both, console completion offers MATLAB's keywords.
- **Simulink's solver names.** The model toolbar offers `ode45`, `ode23`,
  `ode15s`, `ode23s`, `ode23t` and `ode113`, mapped to the closest method Evans
  has, and the fixed-step `ode1` to `ode5`. `ode2`, `ode3` and `ode5` are new.
  The scipy names (RK45, BDF, ...) are still there.
- **Any number of algebraic loops.** A model with several loops, or two loops
  sharing a block, is solved loop by loop, upstream first. The warning names
  every loop, and a loop that does not converge is named on its own.
- **Discontinuities are handled as Simulink does.** Saturation, dead zone,
  relay, switch, backlash, Coulomb friction, abs, sign and min/max hold their
  mode between switches; the solver stops exactly at each switch and restarts
  from there. A model that switches back and forth endlessly (a relay on an
  integrator, friction at rest) now finishes with a warning instead of hanging.
  Fixed-step solvers update the modes after every step.

### Fixed
- A relay with hysteresis switched off at its on-point: its memory never updated.
- Between two discrete sample times, the continuous state was carried over from
  the last plotted point instead of the true end of the interval, so an
  integrator could lose part of its value when the sample time did not line up
  with the plot grid.
- The last instant of a continuous run was never logged.
- An unknown solver name now gives a clear error, instead of failing late or
  being silently accepted by a model with no continuous states.

### Changed
- The default solver is shown as `ode45`; it is the same method as the old RK45
  default. With discontinuities in the model and no maximum step set, the step
  is capped at one fiftieth of the run, Simulink's default, so a short excursion
  cannot be stepped over.

## 0.9.5 - 2026-10-21

### Added
- **A splash screen while Evans starts.** The name, the version and Cedric
  appear as soon as Evans is launched, with a line saying what is loading and a
  bar for how far it has got, instead of nothing for several seconds.
- The first release delivered by the automatic updater: if you have 0.9.4, Evans
  offers this one by itself.

## 0.9.4 - 2026-10-21

### Added
- **Automatic updates.** Once a day, a few seconds after launch, Evans checks
  GitHub for a newer release and offers Update now, Update when I close Evans,
  or Later. The installer is checked against its published SHA-256 before it
  runs. Help > Check for updates asks on demand, and the same menu turns the
  daily check off. This is the last version you need to install by hand.
- **Completion everywhere you type code or LaTeX.** One popup in the console
  prompt, the Script editor and both kinds of live-script cell. It opens as you
  type and narrows as you go; Up and Down pick, Tab or Enter accept, Escape
  closes, Ctrl+Space opens it on demand. Each row shows the call form
  (`step(sys, t)`, `lqr(A, B, Q, R)`) and a one-line description.
- Candidates come from your workspace variables and their attributes, the
  console's commands, the MATLAB runtime's built-ins, Python keywords and the
  `.m` files in the folder.
- In LaTeX text cells it completes commands after a backslash, closes
  `\begin{...}` with its `\end`, and offers your figure labels after `\ref{` and
  `\eqref{`.
- Accepting a function inserts its brackets with the cursor between them, or
  after them if it takes no arguments.
- **Cedric**, the shrimp at the foot of the workspace rail, opens this
  documentation when clicked. So does Help > Documentation (F1).

### Fixed
- Save on the Live tab did nothing. It now saves back to the file the script
  came from, in that file's format, so an `.mlx` stays an `.mlx`. A new script
  goes to Save as, which offers `.mlx` and `.m`, and warns before an `.mlx`
  would drop figure captions, labels or the report template.
- The demo model drew loops between neighbouring blocks because they sat too
  close together. Forward wires now go straight, and the demo blocks are spaced
  out.
- Folding the block palette left a thin strip behind with a second Blocks
  button. It now folds away completely.

## 0.9.3 - 2026-10-20

### Added
- **PDF preview for live scripts.** Preview (Ctrl+Alt+P, next to Export) splits
  the Live tab: the script on the left, its PDF on the right. It rebuilds in the
  background when you run; the last good PDF and your scroll position stay put,
  and a failed build shows TeX's error line.
- **Report templates.** Page, font, title page, header and footer, numbering,
  whether code and output are shown, and extra preamble, taken from the script,
  your settings or the default. The preview and Export report both use it.
- Every figure in a report is a proper figure with a caption and a label you can
  `\ref`. Text cells are LaTeX in the report, and the Markdown marks and
  `{{expr}}` placeholders still work.

### Fixed
- `sound()` and `soundsc()` play in the Windows build. They used to say no audio
  output was available.

## 0.9.2 - 2026-10-20

### Changed
- The Model toolbar puts Open and Save first, so they never disappear when the
  window is narrow. Fit, Align and Space moved to a small panel in the canvas's
  corner, and hidden entries sit behind a labelled **More** button.
- The Edit-model panel always shows the whole loop, fitted; it no longer zooms,
  pans or scrolls.
- On the site, the Download button downloads the installer on Windows and points
  to running from source on macOS and Linux.

### Fixed
- Wiring on the Model canvas works again, by clicking port then port or by
  dragging. The preview wire was catching the second click.
- Right-click on a wire or block selects it first, so Delete wire and Delete
  block act on the thing under the cursor.
- Changing the theme could leave the window not responding. A theme change now
  asks to restart Evans, and applies on the next start.
- Right-clicking the empty title bar opens the Windows system menu again.

## 0.9.1 - 2026-10-20

### Added
- **A Windows installer** beside the portable zip. It installs for your account
  only, needs no administrator rights, adds a Start-menu shortcut and an
  uninstaller, and opens `.fmdl` models on double-click.
- **One title bar on Windows**, with the menus, the window title and the window
  buttons in it. Snap, edge resizing and Snap Layouts work as usual. View >
  Integrated title bar turns it off.
- **The documentation site**, with the command and block pages generated from
  the code so they cannot drift from it.
- Evans opens files given on the command line: models on the Model canvas,
  scripts in the Console.
- The taskbar shows Evans's own icon, even when run from source.

### Fixed
- `bandwidth(sys)` measured a closed loop around `sys` rather than `sys` itself.
  It now matches MATLAB, including the optional dB drop.
- A maximised window leaves a 2-pixel gap at an auto-hiding taskbar, so the
  taskbar can still be revealed.
- Windows 10 lost the top edge of the window frame; the title bar draws it now.
- The window title no longer repeats itself.

## 0.9.0 - 2026-10-20

First public release, and the first under the name Evans, after Walter R. Evans,
who invented the root locus. Before this it was a private project called
FauxMatlab; models and settings saved under that name still open.

### Added
- **The Holding Point icon set** on the workspace rail, the Model toolbar, the
  run controls, the figure controls and the pane picker, drawn in the current
  theme.
- Middle-button drag pans the Model canvas, as in Simulink.
- MIT licence, and a quick start in the README from clone to running app.

### Fixed
- Re-running a script numbers its figures from 1 again, as MATLAB does after
  `close all`. Split keeps the newer figure on the right, and Move swaps the two
  shown figures instead of emptying a side.
- On the Live tab the Console's figure strip is hidden, since live scripts draw
  their figures inline; "Open in window" pops one out larger.
- PDF report export works with MiKTeX. It also looks in MiKTeX's and TeX Live's
  default folders, tries the next engine if one fails, and shows TeX's own error
  line.
- Several fixes for current numpy, scipy and PySide6, including SVG figure
  export and algebraic loops that the solver had wrongly reported as not
  converging.

## Before 0.9 - as FauxMatlab, September and October 2026

Private builds, called FauxMatlab at the time (Evans was named in 0.9.0).
Everything here is part of 0.9.0. In short:

- **23 September, the first build.** Classical and modern control over one live
  model, a block-diagram simulator, and a MATLAB-shaped command window with a
  workspace browser and docked figures. Closed loops solved exactly from the
  block diagram, an LTI Viewer, a Control System Designer and a PID Tuner, and
  `--check`, a headless self-test.
- **23 to 24 September, the interface rework.** Three workspaces on a rail
  (Analyse, Model, Console) instead of eight tabs, a grid of one, two or four
  views of the same live model, and a context bar showing the loaded model with
  its stability and margins.
- **24 to 30 September, panes and the simulator.** Analyse became panes only,
  with hover readouts, Bode asymptotes, the minimum-phase split (`mpsplit`),
  alignment snapping and Tune... on PID blocks in the simulator.
- **3 to 5 October, Day and Night.** The concrete Day and asphalt Night themes;
  plots, diagrams and the canvas follow the theme.
- **16 October, MATLAB scripts and live scripts.** The Script tab runs MATLAB as
  written (matrices, indexing with `end`, control flow, local functions, cells,
  structs), with a real editor and debugger; the Live tab opens and saves `.mlx`
  and live `.m`, with LaTeX, PDF and HTML export.
