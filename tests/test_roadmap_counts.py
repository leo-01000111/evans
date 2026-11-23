"""
docs/ROADMAP.md counts its own open items: each phase heading says "N open" and the
"At a glance" table repeats the numbers. Both are written by hand, so this test
recounts the `- [ ]` items and fails when a count has drifted.
"""

from __future__ import annotations

import re
from pathlib import Path

ROADMAP = Path(__file__).resolve().parents[1] / "docs" / "ROADMAP.md"
OPEN_ITEM = re.compile(r"^\s*- \[ \]")


def _sections() -> list[tuple[str, int]]:
    """(heading, open items) for every ## and ### section, own lines only."""
    out: list[tuple[str, int]] = []
    heading, count = None, 0
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        if re.match(r"#{2,3} ", line):
            if heading is not None:
                out.append((heading, count))
            heading, count = line, 0
        elif OPEN_ITEM.match(line):
            count += 1
    if heading is not None:
        out.append((heading, count))
    return out


def _counted() -> dict[str, int]:
    """Phase heading -> open items, a phase including its ### subsections
    except 8.4, which is counted and stated on its own."""
    totals: dict[str, int] = {}
    phase = None
    for heading, count in _sections():
        if heading.startswith("## "):
            phase = heading
            totals[phase] = count
        elif heading.startswith("### 8.4"):
            totals[heading] = count
        elif phase is not None:
            totals[phase] += count
    return totals


def test_every_phase_heading_states_the_open_count_it_has():
    checked = 0
    for heading, actual in _counted().items():
        m = re.search(r"(\d+) open", heading)
        if m:
            checked += 1
            assert int(m.group(1)) == actual, f"{heading!r} says {m.group(1)}, found {actual}"
    assert checked >= 9, "phase headings no longer state their counts"


def test_the_at_a_glance_table_matches_the_headings():
    text = ROADMAP.read_text(encoding="utf-8")
    table = {name: int(n) for name, n in re.findall(r"^\| (.+?) \| (\d+) \|", text, re.M)}
    assert len(table) >= 10, "the At a glance table is missing"
    sections = dict(_sections())
    totals = _counted()
    for name, n in table.items():
        key = re.match(r"Phase (\d+(?:\.\d+)?)", name)
        if name == "1.0":
            actual = sections["### What blocks it"]
        elif key and "." in key.group(1):
            actual = next(v for k, v in totals.items() if k.startswith(f"### {key.group(1)} "))
        else:
            actual = next(v for k, v in totals.items() if k.startswith(f"## Phase {key.group(1)} "))
        assert n == actual, f"table says {name!r}: {n}, found {actual}"
