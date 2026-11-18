"""
What the MATLAB-style apps became: the plot renderer every analysis pane uses
(`LTIViewer`), the root-locus designer and PID tuner of the Design tab, and
the snapshot bar.

Each is a widget over a core module that does the arithmetic headlessly —
:mod:`evans.core.viewer`, :mod:`evans.core.designer` and
:mod:`evans.core.pidtune`. The split is the same one the console uses,
and for the same reason: a design decision that can only be checked by looking
at a window is a design decision that does not get checked.
"""

from .designer_app import ControlSystemDesigner
from .lti_viewer import LTIViewer
from .pid_tuner import PIDTuner
from .snapshots import SnapshotBar

__all__ = ["LTIViewer", "ControlSystemDesigner", "PIDTuner", "SnapshotBar"]
