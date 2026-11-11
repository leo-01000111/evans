"""
CHANGELOG.md keeps up with the code.

A release adds its section to the changelog. This fails when the current
`evans.__version__` has no section, unless "Unreleased" is the only section
above the newest release (work waiting for its release).
"""

import re
from pathlib import Path

import evans

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^## (.+?)\s*$", re.MULTILINE)


def _sections() -> list[str]:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return HEADING.findall(text)


def test_the_changelog_has_a_section_for_the_current_version():
    sections = _sections()
    versions = [re.match(r"(\d+\.\d+\.\d+)\b", s) for s in sections]
    versions = [m.group(1) if m else s for m, s in zip(versions, sections)]
    above = versions[:versions.index(evans.__version__)] \
        if evans.__version__ in versions else None
    assert above is not None, (
        f"CHANGELOG.md has no section for version {evans.__version__}")
    assert above in ([], ["Unreleased"]), (
        f"CHANGELOG.md has sections above {evans.__version__}: {above}")


def test_the_changelog_is_newest_first():
    def key(s: str):
        m = re.match(r"(\d+)\.(\d+)\.(\d+)", s)
        return tuple(int(g) for g in m.groups()) if m else None

    keys = [k for k in map(key, _sections()) if k]
    assert keys == sorted(keys, reverse=True)


def test_every_version_has_its_date():
    for s in _sections():
        if re.match(r"\d+\.\d+\.\d+", s):
            assert re.search(r"\d{4}-\d{2}-\d{2}", s), s
