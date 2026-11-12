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
- Tests: `python -m pytest` (about 26 minutes for ~5300 tests; Qt runs offscreen). While working,
  run only the changed area's tests (table in `docs/CODEMAP.md`); run the full
  suite once, in the background, before committing.
- Lint: `ruff check .` (CI runs it; `Inspiration/` is excluded).
- Run: `python app.py`.
- Examples under File > Examples are built by `tools/build_examples.py`.
- Docs site is built from `site/` into `site/_build/` (ignored).

## Layout
Read `docs/CODEMAP.md` before exploring: every package, the large files to
search rather than read, and which tests cover which area.

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
- A release adds its section to `CHANGELOG.md` as well as to the site's patch
  notes (`site/pages/patch-notes.html`); `tests/test_changelog.py` checks it.
- The Windows installer is unsigned on purpose until there are more users.
- The model files in `tests/fixtures/models/` are frozen: never edit or delete
  one. A format change adds fixtures for the new format and must keep the old
  ones loading (`tests/golden/test_model_compat.py`).
- `COURSE MATERIAL/` is third-party copyright and must stay out of git.

## Working with an LLM in this repo
Evans is a large codebase, so coding in it with an LLM is expensive. Keep few
things in flight: at most about two sessions at once, never a fan-out of many.
A big or risky feature gets its own session; small related tasks (a test, a
docs section, a few-line fix) are batched into one. Run the full suite once
per batch before committing, not once per tiny task. Read only the files the
work needs, and ask before starting the next big item.

- A fresh session per big feature reads less and drifts less than a long one.
  Decisions and leftovers go in `docs/ROADMAP.md`, not only in chat.
- Navigate with go-to-definition and find-references (the Pyright language
  server; `[tool.pyright]` in `pyproject.toml`) before reading whole files.
- Hand broad searches to a cheap read-only subagent (`scout`, on Haiku) and
  keep only its conclusions.
