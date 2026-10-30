"""
Block parameters that name workspace variables.
===============================================
In Simulink a Gain of ``Kp`` or a sine at ``2*pi*f`` is evaluated in the
MATLAB workspace each time the model is compiled, which is what makes model
variables and parameter sweeps work: change ``Kp`` at the prompt, run again.

A block keeps such a parameter as text (see
:attr:`~evans.sim.block.Block.expressions`). :func:`resolve_model` evaluates
every one, inside subsystems too, and returns a copy of the model that holds
only numbers, ready for the compiler. The evaluator is whatever the caller
has: the console's workspace in the app, the caller's workspace for ``sim``
typed at the prompt, and an empty MATLAB workspace otherwise
(:func:`default_evaluator`), where ``2*pi`` still works and ``Kp`` does not.

Evaluation happens before a run, on the thread that owns the workspace. The
solver thread only ever sees the resolved copy.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .block import BlockError, ParamSpec

#: Evaluates one MATLAB expression; raises on an error.
Evaluator = Callable[[str], Any]


class WorkspaceError(Exception):
    """An expression could not be evaluated, or gave an unusable value."""


_DEFAULT: Evaluator | None = None


def default_evaluator() -> Evaluator:
    """An empty MATLAB workspace: constants and functions, no variables."""
    global _DEFAULT
    if _DEFAULT is None:
        from ..console.interpreter import Interpreter
        _DEFAULT = Interpreter().evaluate
    return _DEFAULT


def constant_value(text: str) -> Any:
    """``text`` evaluated with no variables; :class:`WorkspaceError` if not."""
    try:
        return default_evaluator()(text)
    except Exception as exc:                               # noqa: BLE001
        raise WorkspaceError(str(exc)) from exc


def coerce(spec: ParamSpec, value: Any) -> Any:
    """
    An evaluated value in the form the block expects for this kind.

    ``float`` gives a number (or a flat array, for a vector Gain or
    Constant), ``vector`` a flat array, ``matrix`` a 2-D one; ``data`` is
    passed through for the block to read.
    """
    if spec.kind == "data":
        return value
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        raise BlockError(
            f"must be numeric, and it evaluated to "
            f"{type(value).__name__}") from None
    if spec.kind == "matrix":
        if arr.size == 0:
            raise BlockError("is empty")
        return np.atleast_2d(arr)
    if spec.kind == "vector":
        return arr.reshape(-1)
    if arr.size == 0:
        raise BlockError("is empty")
    return float(arr.reshape(-1)[0]) if arr.size == 1 else arr.reshape(-1)


def workspace_variables(evaluate: Evaluator) -> dict[str, Any]:
    """
    The variables behind an evaluator, for the blocks that run MATLAB code.

    An evaluator from the console is a bound method of the interpreter or
    its runtime, whose namespace is the workspace; anything else has none.
    """
    owner = getattr(evaluate, "__self__", None)
    namespace = getattr(owner, "namespace", None)
    if namespace is None:
        namespace = getattr(owner, "ns", None)
    return dict(namespace) if isinstance(namespace, dict) else {}


def bind_code(flat_model, evaluate: Evaluator | None = None) -> None:
    """
    Give the MATLAB code blocks of a flattened model their workspace.

    After flattening, because flattening rebuilds every block from its
    parameters, and what a block read from the workspace is not one.
    """
    from .compile import CompileError

    code = [b for b in flat_model if b.binds_workspace]
    if not code:
        return
    variables = workspace_variables(evaluate or default_evaluator())
    for block in code:
        try:
            block.bind(variables)
        except (BlockError, ValueError, TypeError) as exc:
            raise CompileError(
                f"{block.type_name} {block.block_id!r}: {exc}") from exc


def has_expressions(model) -> bool:
    """Whether any block, at any depth, has a parameter left to evaluate."""
    for block in model:
        if block.expressions:
            return True
        if block.type_name == "Subsystem" and _dict_has_expressions(
                block.params.get("model")):
            return True
    return False


def _dict_has_expressions(data) -> bool:
    if not data:
        return False
    from .block import create
    for entry in data.get("blocks", []):
        if entry.get("type") == "Subsystem":
            if _dict_has_expressions(entry.get("params", {}).get("model")):
                return True
            continue
        try:
            block = create(entry["type"], "__probe__",
                           **{k: v for k, v in entry.get("params", {}).items()
                              if k != "model"})
        except (BlockError, KeyError, ValueError, TypeError):
            continue
        if block.expressions:
            return True
    return False


def resolve_model(model, evaluate: Evaluator | None = None, _path: str = ""):
    """
    A copy of ``model`` with every workspace expression evaluated.

    Raises :class:`~evans.sim.compile.CompileError` naming the block, the
    parameter and the text when an expression fails or gives a value the
    block cannot use, so the message reads like Simulink's: which block,
    which box, what was typed.
    """
    from .compile import CompileError

    evaluate = evaluate or default_evaluator()
    resolved = model.copy()
    for block in resolved:
        where = f"{_path}{block.block_id}"
        if block.type_name == "Subsystem":
            inner = block.inner_model()
            if has_expressions(inner):
                block.set_param("model", resolve_model(
                    inner, evaluate, f"{where}/").to_dict())
            continue
        if not block.expressions:
            continue
        values: dict[str, Any] = {}
        for name, text in block.expressions.items():
            spec = block.spec(name)
            try:
                raw = evaluate(text)
            except Exception as exc:                       # noqa: BLE001
                raise CompileError(
                    f"{block.type_name} {where!r}: cannot evaluate "
                    f"{spec.label} = {text}: {_message(exc)}") from exc
            try:
                values[name] = coerce(spec, raw)
            except BlockError as exc:
                raise CompileError(
                    f"{block.type_name} {where!r}: {spec.label} = {text} "
                    f"{exc}") from exc
        try:
            block.resolve(values)
        except (BlockError, ValueError, TypeError) as exc:
            shown = ", ".join(f"{block.spec(n).label} = {t}"
                              for n, t in block.expressions.items()) \
                or ", ".join(f"{block.spec(n).label} = {v}"
                             for n, v in values.items())
            raise CompileError(
                f"{block.type_name} {where!r} ({shown}): {exc}") from exc
    return resolved


def _message(exc: BaseException) -> str:
    text = str(exc).strip()
    for prefix in ("Error: ", "MatlabError: "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text or type(exc).__name__
