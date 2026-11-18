# Code map

A short guide to where things are, for people and coding agents new to the code.
Read this first instead of exploring: it is cheaper. Every package under `src/evans/`
is named here (`tests/test_codemap.py` checks), so a new package fails the suite until
it gets a line.

About 85,000 lines in 200 modules. The large files are listed with their size: **search
them (grep, go-to-definition), don't read them whole.**

## Packages

| Package | What it is | Start at |
|---|---|---|
| `evans` | entry point, self-test (`--check`), GitHub update check, `__version__` | `app.py`, `selftest.py` |
| `evans.core` | classical and modern control analysis, Qt-free (`Model`, Bode, Routh, LQR, PID tuning…) | `model.py`, `architecture.py`, `algebra.py` |
| `evans.console` | the MATLAB interpreter: parser/translator, runtime, and the `lib_*` command libraries | `interpreter.py`, `matlab.py` |
| `evans.console.live` | live scripts (cells), `.mlx` and live `.m` formats, LaTeX/PDF reports; Qt-free | `document.py`, `livem.py` |
| `evans.sim` | the Simulink engine: model file, compile/flatten, solver, linearise | `model.py`, `compile.py`, `solver.py` |
| `evans.sim.blocks` | the block library, one module per Simulink category | `__init__.py`, `../block.py` (the contract) |
| `evans.help` | help pages, one Markdown file per command in `help/pages/` | `__init__.py` |
| `evans.examples` | sample `.evx` models (rebuilt by `tools/build_examples.py`) | `__init__.py` |
| `evans.assistant` | Cedric's OpenRouter client and prompt protocol, Qt-free | `client.py`, `protocol.py` |
| `evans.ui` | the window and app-wide pieces: menus, theme, settings, updater, autosave; `side_panel.py` is each workspace's right-hand tabbed panel (`SidePanel`); `design_panel.py` is the Analyse panel's Design tab (Gain · Compensator · PID, live apply to K₂); `preferences.py` is the Preferences dialog (`preferences_dialog(window)`; theme, title bar, block boxes, snapshot bar, autosave, updates, startup, scope); `panes.py` the pane grid (`PaneGrid.active_index`) and each plot pane's Compare menu; `search.py` the command palette's Qt-free matching and order (`Entry`, `score`, `rank`), `search_registry.py` what it lists (`collect(window)`), `search_popup.py` the popup, `shortcuts.py` the Help ▸ Keyboard shortcuts sheet (also the source of `help/pages/shortcuts.md`) | `mainwindow.py` |
| `evans.ui.console` | command window, workspace, script editor, live editor, figures | `console_dock.py` |
| `evans.ui.code` | code editing: highlighting, completion popup, hover/Ctrl+click | `editor.py`, `completion.py` |
| `evans.ui.sim` | the Model tab: canvas, palette, inspector, scope, run toolbar | `sim_tab.py`, `canvas.py` |
| `evans.ui.apps` | what the apps became: the plot renderer every pane uses (`LTIViewer`), the Design tab's root-locus designer and PID tuner, the snapshot bar | the widget's own module |
| `evans.ui.tabs` | the classical analysis tabs (System, Time, Frequency, Stability…) | the tab's own module |
| `evans.ui.tabs.modern` | the state-space views (Modern tab) | `modern_tab.py`, `context.py` |
| `evans.ui.diagram` | the fixed course-architecture diagram | `fixed_diagram.py` |
| `evans.ui.assistant` | Cedric's panel (the last side-panel tab of every workspace), what he reads (`sources.py`) and the Ask Cedric buttons | `panel.py` |

## Large files: search, don't read

| File | Lines | Holds |
|---|---|---|
| `console/matlab_runtime.py` | 6000 | everything translated MATLAB calls: indexing, assignment, cells, structs, errors, `InputParser` |
| `console/matlab.py` | 2000 | the MATLAB → Python translator (parser, `classdef`, nested functions) |
| `console/lib_*.py` | 500–1800 each | commands, grouped: `lib_plot`, `lib_optim`, `lib_files`, `lib_stats`, `lib_signal`, `lib_dates`, `lib_tables`, `lib_sparse`, `lib_system`, `lib_text`, `lib_cells`, `lib_lang`, `lib_sim`, `lib_types`, `lib_ui`, `lib_classes` |
| `console/figure_mpl.py` | 1100 | matplotlib rendering (3-D, pies, PDF/EPS) |
| `ui/console/figure_view.py` | 1450 | pyqtgraph rendering of 2-D figures, data tips |
| `ui/mainwindow.py` | 1900 | the window: menus, side panels, layout, quit, recovery |
| `ui/plots.py` | 1200 | plot widgets shared by the analysis tabs |
| `sim/solver.py` | 1200 | the simulation engine (steps, zero crossings, sample hits) |

## Where to look for…

- **A console command** (`foo(...)`): `grep -n "def foo\b" src/evans/console/lib_*.py`;
  its help page is `src/evans/help/pages/foo.md`; its tests `tests/golden/test_lib_<group>.py`.
- **A MATLAB language feature** (indexing, `end`, cells, errors): `matlab.py` translates it,
  `matlab_runtime.py` runs it; tests in `tests/golden/test_matlab*.py` and
  `test_confident_liars.py`.
- **A Simulink block**: `sim/blocks/<category>.py`; the contract is `sim/block.py`; how
  the canvas draws it is `ui/sim/items.py`.
- **A menu action**: `ui/mainwindow.py` `_build_menus` (File · Edit · View · Help; the
  settings are in `ui/preferences.py`, the presets in `_build_plant_menu`, the stability
  lamp and margins in `LoopStatus`, `ui/context_bar.py`, shown in the status bar).
- **Something saved between sessions**: `ui/persist.py` (QSettings keys); window layout,
  side panels included (`side/<workspace>/open|tab|width`), in `MainWindow.save_layout`.
- **A workspace's side panel** (Loop, Properties, Workspace, Cedric…): `ui/side_panel.py`;
  the main window builds them and moves Cedric between them (`_place_cedric`).
- **Design and compare** (`sisotool`, `pidtuner`, `ltiview`): `ui/design_panel.py` writes K₂
  through `MainWindow.change_loop`; `MainWindow.open_app` routes the console commands;
  tests in `tests/golden/test_apps_ui.py`.
- **The command palette** (Ctrl+K, Ctrl+Shift+P, the title-strip field): the window's
  `show_search`; ranking in `ui/search.py` (tests: `tests/test_search.py`, Qt-free), the entry
  list in `ui/search_registry.py`, the popup in `ui/search_popup.py`; a menu action reaches
  it by itself, a workspace-specific one needs `action.setProperty("workspace", ...)` in
  `_build_menus`. Tests: `tests/golden/test_search_ui.py`.
- **Theme colours and spacing**: `ui/theme.py`, `ui/design.py`.

## Tests by area

Run only the area you changed while working; run the full suite (about 26 minutes) once
before committing.

| Area changed | Run |
|---|---|
| a console command / `lib_*` | `python -m pytest tests/golden/test_lib_<group>.py -q` |
| the MATLAB language | `python -m pytest tests/golden -q -k "matlab or liars or lang or classdef or nd_arrays or types"` |
| `sim` or a block | `python -m pytest tests/golden -q -k "sim or canvas or scope"` |
| `core` analysis | the module's own `tests/test_<module>.py` (Qt-free, fast), then `tests/golden/test_analysis_values.py` |
| live scripts | `python -m pytest tests -q -k "live or mlx or sipro"` |
| a window or widget | the matching `tests/golden/test_*_ui.py` |
| the command palette or the shortcut sheet | `python -m pytest tests/test_search.py tests/golden/test_search_ui.py -q` |
| help pages | `python -m pytest tests/test_help.py -q` |
| README numbers (counts) | `python -m pytest tests/golden/test_packaging.py -q` |

`ruff check .` always. Qt tests run offscreen; a modal dialog no test answers fails at
once (`tests/conftest.py`).
