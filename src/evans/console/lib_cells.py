"""
Cells and structs.
==================
Mapping over arrays and cells, and converting between cells, structs and matrices.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.
"""

from __future__ import annotations

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import MatlabError, _nargout  # noqa: F401


class CellLibrary:
    """cellfun, cell2mat, rmfield and the rest."""
