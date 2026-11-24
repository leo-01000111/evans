# Help-page gaps

Callable names (the runtime's `f_*` methods and `api._GROUPS`) with no page in `src/evans/help/pages/`,
found 2026-11-24 by comparing `Interpreter` library names with `help.topics()`; names in
`not_in_evans.md` are excluded. **216 of 762 callable names have no page.**

Rank 1: named in `site/pages/compatibility.html` or `README.md` (code spans). Rank 2: common in
MATLAB teaching code or a signal-processing / control course. Rank 3: the rest. `(p)` marks a name
that only the patch notes mention. Pages are registered in a group of `help.GROUPS` (index tree).

| Rank | Names |
|---|---|
| 1 | 25 |
| 2 | 116 |
| 3 | 75 |

## Rank 1: advertised on the site or README, no page

- **Files, folders, session** (5): `addpath`, `cd`, `load`, `pwd`, `save`
- **Types and tests** (1): `all`
- **Signal and filters** (10): `butter`, `cheby1`, `ellip`, `fft`, `filter`, `findpeaks`, `freqz`, `ifft`, `interp1`, `trapz`
- **Elementary maths** (3): `ceil`, `log10`, `log2`
- **ODE and optimisation** (3): `fminsearch`, `fzero`, `ode45`
- **Operators as functions** (1): `gt`
- **Constants** (1): `nan`
- **Other** (1): `struct2table`

## Rank 2: teaching and course staples

- **Errors** (6): `MException`, `assert`, `error` (p), `rethrow`, `throw`, `warning`
- **Elementary maths** (37): `acos`, `angle`, `asin`, `atan`, `atan2`, `conj`, `cos`, `cosh`, `cumprod`, `deg2rad`, `diag`, `fix`, `flip`, `fliplr`, `flipud`, `floor`, `imag`, `kron`, `log`, `median`, `mod`, `norm`, `prod` (p), `rad2deg`, `randn`, `rank`, `real`, `rem` (p), `round`, `sign`, `sin` (p), `sinh`, `std`, `tan`, `tanh`, `trace`, `unique`
- **Types and tests** (23): `any`, `cell`, `class`, `fieldnames`, `horzcat`, `isa`, `iscell`, `ischar`, `iscolumn`, `isempty`, `isfinite`, `isinf`, `islogical`, `isnan`, `isnumeric`, `isreal`, `isrow`, `isscalar`, `isstruct`, `isvector`, `num2cell`, `struct` (p), `vertcat`
- **Control plots and units** (11): `bodeplot`, `db`, `db2mag`, `impulseplot`, `mag2db`, `nyquistplot`, `pzplot`, `rlocusplot`, `sgrid`, `stepplot`, `zgrid`
- **Strings and conversion** (9): `char`, `int2str` (p), `mat2str` (p), `newline`, `str2double`, `str2num`, `strcat` (p), `strcmp` (p), `strcmpi`
- **Signal and filters** (13): `cheby2`, `cumtrapz`, `deconv`, `dirac`, `fftshift`, `heaviside`, `hist`, `histcounts` (p), `hypot`, `ifftshift`, `interp`, `polyfit`, `taylor` (p)
- **Files, folders, session** (11): `clearvars`, `display`, `drawnow`, `fileparts`, `format`, `fullfile`, `isdir`, `isfile`, `isfolder`, `more`, `rmpath`
- **ODE and optimisation** (6): `fminbnd`, `ode15s` (p), `ode23` (p), `ode23s` (p), `odeset`, `optimset`

## Rank 3: the rest

- **Constants** (7): `Inf` (p), `NaN` (p), `eps` (p), `i` (p), `inf`, `j` (p), `pi` (p)
- **Dates and calendar** (10): `NaT`, `addtodate`, `calquarters`, `calweeks`, `hms`, `iscalendarduration`, `isnat`, `posixtime`, `timeofday`, `ymd`
- **Colormaps** (15): `autumn`, `bone`, `cool`, `copper`, `gray` (p), `hot` (p), `hsv`, `jet` (p), `parula` (p), `pink`, `spring`, `summer`, `turbo` (p), `white`, `winter`
- **Plot leftovers** (10): `barh` (p), `box`, `cla`, `clim`, `fill3`, `gca` (p), `meshc`, `shg`, `subtitle`, `surfc`
- **Other** (5): `bdclose`, `bdroot`, `beep`, `containers_Map`, `pkg`
- **Symbolic** (8): `collect`, `isAlways`, `latex`, `poly2sym`, `pretty`, `str2sym`, `symvar`, `vpa`
- **Operators as functions** (19): `ctranspose`, `eq`, `ge`, `ldivide`, `le`, `lt`, `minus` (p), `mldivide`, `mpower`, `mrdivide`, `mtimes`, `ne`, `plus` (p), `power`, `rdivide`, `times`, `transpose`, `uminus`, `uplus`
- **Control plots and units** (1): `stepDataOptions`

## Where they live

Source module of each name's `f_*` method (a hint for the writer, not a help group):

- `const`: 7
- `lib_dates`: 10
- `lib_lang`: 21
- `lib_plot`: 25
- `lib_signal`: 1
- `lib_sim`: 2
- `lib_types`: 1
- `matlab_runtime`: 149
## Suggested `help.GROUPS` group per category

Signal and filters, Control plots and units: `Signal processing` (the plot commands `bodeplot` etc. next to `Plot options`). ODE and optimisation: `Fitting and optimisation`. Elementary maths: `Maths`. Types and tests, Operators as functions: `Language` (or `Numeric types`). Errors: `Language`. Strings and conversion: `Strings`. Files, folders, session: `Session` or `Data files`. Symbolic: `Symbolic`. Colormaps, Plot leftovers: `Plotting`, `Images and colour`. Dates and calendar: `Tables and dates`. Constants: `Numeric types`. Other: `Maps`, `Simulink models`, `Tables and dates`.

Rank counts: 25 + 116 + 75 = 216. Counted by a throwaway script; `char`, `class`, `fft`, `filter`, `ode45`, `save`, `sin` and the other staples above have no page today.

## Batch 1 (2026-11-24): written

`fft`, `ifft`, `filter`, `freqz`, `findpeaks`, `butter`, `cheby1`, `ellip`, `interp1`, `trapz`, `ode45`, `fzero`, `fminsearch`, `save`, `load`. Remaining: rank 1, 10 (`addpath`, `all`, `cd`, `ceil`, `gt`, `log10`, `log2`, `nan`, `pwd`, `struct2table`); rank 2, 116; rank 3, 75.

## Batch 2 (2026-11-24): written

`cd`, `pwd`, `addpath`, `all`, `ceil`, `log10`, `log2`, `gt`, `nan`, `struct2table`. This completes rank 1 (25 of 25). Remaining: rank 2, 116; rank 3, 75 (191 names). `any` and `pi` are named in the bug items but still have no page (rank 2 and rank 3).

## What the sweep found (2026-11-24)

- 216 of 762 callable names had no page, including `fft`, `filter`, `ode45`, `sin`, `class`, `error` and `save`. The site and README advertised 25 of them.
- Writing 30 pages (these 25 plus the five audio pages) with every claim run turned up dozens of defects, none fixed (feature freeze). The silent wrong answers (`all`/`any` of a matrix, `load` type loss, `struct2table` class, `trapz` shape, ignored `ode45` options, `nan` array forms, constants lost after `clear`) are in `docs/ROADMAP.md` Phase 0; the crashes and raw Python errors are in Phase 4; users see both on the site's Known issues page.
- Method and scripts: `side-session-notes/.../help-audit-2026-11-24.md` (outside the repo); the method is repeatable: compare `dir(_Library)` `f_*` names and `api._GROUPS` with `help.topics()`.
- Pattern: a function with no page also has no tests of its edge cases, and those are where the bugs were. Missing-argument calls fall through to Python `TypeError` almost everywhere; one argument-count check in the library dispatcher may fix the whole class (not investigated).
