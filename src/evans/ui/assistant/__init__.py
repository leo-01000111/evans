"""
Cedric, the assistant side panel: ask a free OpenRouter model about the code
at hand.

The model, context and reply format are :mod:`evans.assistant`; this is the
side-panel page, the sources that let it read from (and apply edits to) the
console, script tabs and live cells, and the floating *Ask Cedric* button.
"""

from .ask_float import AskCedricFloat
from .panel import AssistantPanel
from .sources import (
    ConsoleSource,
    EditorSource,
    LoopSource,
    ModelSource,
    Source,
    SwitchSource,
)

__all__ = ["AskCedricFloat", "AssistantPanel", "ConsoleSource", "EditorSource",
           "LoopSource", "ModelSource", "Source", "SwitchSource"]
