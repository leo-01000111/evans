"""
Saving a live script back to ``.mlx``.

The three SiPro labs were saved by MATLAB R2023a. Opening one and saving it
again must give a file that reads back as the same document, and the
editor's Save must keep a script an ``.mlx`` when that is what it came from.
(``test_live_ui.py`` covers the editor's buttons and the warning about what
``.mlx`` cannot hold; ``test_live_formats.py`` the plain-text format.)
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from evans.console.live import (
    Cell,
    LiveDocument,
    load,
    read_mlx,
    save,
    write_mlx,
)

SIPRO = Path(__file__).parent.parent / "fixtures" / "sipro"


@pytest.mark.parametrize("name", ["C1", "C2", "C3"])
def test_a_matlab_live_script_survives_being_saved_again(name, tmp_path):
    original = read_mlx(SIPRO / f"{name}.mlx")
    out = save(original, tmp_path / f"{name}.mlx")
    again = load(out)
    assert again.same_content(original)
    assert [c.kind for c in again.cells] == [c.kind for c in original.cells]
    assert [c.section_break for c in again.cells] == \
        [c.section_break for c in original.cells]


def test_the_saved_file_is_the_package_matlab_expects(tmp_path):
    out = write_mlx(LiveDocument([Cell.code("x = 1;")]), tmp_path / "a.mlx")
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "_rels/.rels",
                "matlab/document.xml", "matlab/output.xml"} <= names
        assert "x = 1;" in z.read("matlab/document.xml").decode("utf-8")


def test_saving_by_suffix_chooses_the_format(tmp_path):
    doc = LiveDocument([Cell.code("y = 2;")])
    mlx = save(doc, tmp_path / "s.mlx")
    plain = save(doc, tmp_path / "s.m")
    assert zipfile.is_zipfile(mlx)
    assert not zipfile.is_zipfile(plain)
    assert load(mlx).same_content(load(plain))
