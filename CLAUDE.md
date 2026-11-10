# Evans

A control-systems workbench with a MATLAB-compatible console and a block-diagram
simulator. Python 3.12, PySide6 + pyqtgraph, numpy/scipy/python-control.
The folder is still called `16_FakeMatlab`; the project is **Evans** (was
FauxMatlab until 0.9).

## Naming
Never write "FauxMatlab" or "FakeMatlab" in new code, docs or the site. The only
exceptions are the legacy `.fmdl` format tag, the settings migration, and the
"was called FauxMatlab before 0.9" notes. MATLAB/Simulink are MathWorks
trademarks: mention them only to describe compatibility.

## Commands
- Tests: `python -m pytest` (Qt runs offscreen; `tests/conftest.py` sets this).
- Lint: `ruff check .` (CI runs it; `Inspiration/` is excluded).
- Run: `python app.py`.
- Examples under File > Examples are built by `tools/build_examples.py`.
- Docs site is built from `site/` into `site/_build/` (ignored).

## Layout
`src/evans/`: `core` (analysis, no Qt), `console` (MATLAB interpreter and the
`lib_*` command libraries), `sim`, `ui`, `help`, `assistant`, `examples`.
`tests/` holds unit tests; `tests/golden/` holds the value and UI-layout tests.

## Things that are not obvious
- Every console command has a help page in `src/evans/help/pages/*.md`;
  `tests/test_help.py` checks them. Add a page when you add a command.
- The README's numbers are asserted by `tests/golden/test_packaging.py`: the
  test count (within 10), the command count and groups, the block-type count
  and the pane-kind count. Adding any of these fails that test until the README
  text is updated too.
- The version has one source: `evans.__version__`. Do not copy it elsewhere.
- This machine has PyQt5, PyQt6 and PySide6 installed. pyqtgraph must be pinned
  to PySide6 (`PYQTGRAPH_QT_LIB`) before any Qt import, or the Qt DLLs clash.
  `app.py` and `conftest.py` already do this.
- The Windows installer is unsigned on purpose until there are more users.
- `COURSE MATERIAL/` is third-party copyright and must stay out of git.

## Working with an LLM in this repo
Evans is a large codebase, so coding in it with an LLM is expensive. Work slowly:
one feature at a time, finished, tested and reviewed before the next starts. Do
not batch several roadmap items or run parallel feature agents. Read only the
files the feature needs, and ask before moving on to the next item.
