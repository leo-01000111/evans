"""
`docs/CODEMAP.md` names every package, so a new one cannot be added without a
line saying what it is. A stale map misleads a reader more than no map.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_package_is_on_the_code_map():
    text = (ROOT / "docs" / "CODEMAP.md").read_text(encoding="utf-8")
    src = ROOT / "src"
    packages = sorted(
        ".".join(p.parent.relative_to(src).parts)
        for p in src.rglob("__init__.py")
        if "__pycache__" not in p.parts)
    missing = [p for p in packages if f"`{p}`" not in text]
    assert not missing, f"add these to docs/CODEMAP.md: {missing}"


def test_files_named_in_the_large_files_table_exist():
    text = (ROOT / "docs" / "CODEMAP.md").read_text(encoding="utf-8")
    table = text.split("## Large files")[1].split("## ")[0]
    for line in table.splitlines():
        if line.startswith("| `") and "*" not in line.split("`")[1]:
            name = line.split("`")[1]
            assert (ROOT / "src" / "evans" / name).is_file(), name
