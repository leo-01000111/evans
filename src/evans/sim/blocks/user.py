"""
User-defined blocks: MATLAB code run at every evaluation.

``Fcn`` applies one MATLAB expression in ``u`` (``u(1)*sin(u(2))``);
``MATLABFunction`` runs a function whose arguments and outputs become the
block's ports::

    function [y, dy] = fcn(u, k)
    y = k*u^2;
    dy = 2*k*u;

Both go through the console's translator, once, when the block is
configured; each evaluation then runs the translated Python. That is the
per-step cost to watch: a few dozen microseconds a call, which an ODE solver
pays several times a step.

Workspace variables named in the code (``k`` above, if it is not an
argument) are read when the model compiles, as a parameter expression is,
and held for the run; changing them mid-run has no effect. Functions such as
``sin`` are found as at the console.

Neither block has state. MATLAB's ``persistent`` variables would be updated
at every solver stage, not once a step, so they are not a way to give one
memory; use a Unit Delay or Memory block instead.
"""

from __future__ import annotations

import re

import numpy as np

from ..block import Block, BlockError, ParamSpec, register

_CAT = "User-Defined"

_SIGNATURE = re.compile(
    r"^\s*function\s+(?:(?:\[(?P<outs>[^\]]*)\]|(?P<out>\w+))\s*=\s*)?"
    r"(?P<name>\w+)\s*(?:\((?P<ins>[^)]*)\))?", re.M)
_LOOKUP = re.compile(r"__ml__\.lookup\('(\w+)'")


class _MatlabCode:
    """MATLAB code translated once and run on demand."""

    def __init__(self, source: str, function: bool) -> None:
        from ...console.matlab import MatlabSyntaxError, translate
        self.function = function
        self.name = ""
        try:
            if function:
                chunks = translate(source)
                defs = [c for c in chunks if c.function]
                if not defs:
                    raise BlockError("the code must define a function")
                self.code = compile("\n".join(c.python for c in defs),
                                    "<MATLAB Function>", "exec")
                head = _SIGNATURE.search(source)
                self.name = head.group("name") if head else ""
            else:
                chunks = translate(f"__evans_value__ = ({source});")
                self.code = compile("\n".join(c.python for c in chunks),
                                    "<Fcn>", "exec")
        except MatlabSyntaxError as exc:
            raise BlockError(f"the MATLAB code does not parse: "
                             f"{exc.message}") from None
        self.free = sorted(set(_LOOKUP.findall(
            "\n".join(c.python for c in chunks))))
        self._glob: dict | None = None
        self._fn = None

    def bind(self, variables: dict) -> None:
        """Make the run's globals: the runtime, and the workspace's values."""
        from ...console import matlab_runtime as _mr
        glob: dict = {}
        runtime = _mr.Runtime(glob)
        glob["__ml__"] = runtime
        for name in self.free:
            if name in variables:
                glob[name] = variables[name]
        if self.function:
            exec(self.code, glob)
            self._fn = glob.get(self.name)
            if self._fn is None:
                raise BlockError(f"no function named {self.name!r}")
        # Resolve every other free name now, once, rather than on each call.
        for name in self.free:
            if name not in glob and name != self.name:
                try:
                    glob[name] = runtime.lookup(name, glob, glob)
                except Exception:                          # noqa: BLE001
                    pass                    # a local variable of the function
        self._glob = glob

    def run(self, inputs: list, nargout: int = 1) -> list:
        if self._glob is None:
            self.bind({})
        glob = self._glob
        if self.function:
            result = glob["__ml__"].call(self._fn, tuple(inputs),
                                         nargout=nargout)
            return list(result) if nargout > 1 else [result]
        return [self.run_scope({"u": inputs[0]})]

    def run_scope(self, scope: dict):
        """An expression's value with these names bound (``u``, ``u1``…)."""
        if self._glob is None:
            self.bind({})
        local = dict(scope)
        exec(self.code, self._glob, local)
        return local["__evans_value__"]


def _matlab_value(v: np.ndarray):
    """A signal as MATLAB code sees it: a scalar, or a column."""
    v = np.atleast_1d(np.asarray(v, dtype=float))
    return float(v[0]) if v.size == 1 else v.reshape(-1, 1)


def _signal(value) -> np.ndarray:
    try:
        return np.atleast_1d(np.asarray(value, dtype=float)).reshape(-1)
    except (TypeError, ValueError):
        raise BlockError(
            f"the code returned {type(value).__name__}, not a number") \
            from None


class _CodeBlock(Block):
    """Shared running and width probing for the two code blocks."""

    binds_workspace = True
    _code: _MatlabCode

    def bind(self, variables: dict) -> None:
        self._code.bind(variables)

    def _evaluate(self, t, u) -> list[np.ndarray]:
        try:
            outs = self._code.run([_matlab_value(v) for v in u],
                                  nargout=len(self.outputs))
        except BlockError:
            raise
        except Exception as exc:                           # noqa: BLE001
            raise BlockError(
                f"{self.type_name} {self.block_id!r} failed at t = {t:.6g}: "
                f"{str(exc).strip() or type(exc).__name__}") from None
        return [_signal(v) for v in outs]

    def output_widths(self, input_widths):
        probe = [np.zeros(w) for w in input_widths]
        try:
            return [len(v) for v in self._evaluate(0.0, probe)]
        except BlockError:
            return [1] * len(self.outputs)

    def output(self, t, x, xd, u):
        return self._evaluate(t, u)


@register
class Fcn(_CodeBlock):
    type_name = "Fcn"
    category = _CAT
    description = "A MATLAB expression in u, such as u(1)*sin(u(2))."
    params_spec = (
        ParamSpec("expr", "Expression", "u", kind="code",
                  help="MATLAB, in the input u; u(k) is its k-th element. "
                       "Workspace variables are read when the model runs."),
    )

    def configure(self) -> None:
        text = str(self.params["expr"]).strip()
        if not text:
            raise BlockError("Fcn needs an expression")
        self._code = _MatlabCode(text, function=False)

    def label(self):
        return str(self.params["expr"])


@register
class MATLABFunction(_CodeBlock):
    type_name = "MATLABFunction"
    category = _CAT
    description = "A MATLAB function; its arguments and outputs are the ports."
    params_spec = (
        ParamSpec("code", "Function", "function y = fcn(u)\ny = u;\n",
                  kind="code",
                  help="One MATLAB function. Its inputs become input ports "
                       "and its outputs output ports, in order."),
    )

    def configure(self) -> None:
        source = str(self.params["code"])
        head = _SIGNATURE.search(source)
        if head is None:
            raise BlockError(
                "the code must start with a function line, such as "
                "function y = fcn(u)")
        outs = head.group("outs") if head.group("outs") is not None \
            else (head.group("out") or "")
        ins = head.group("ins") or ""
        self.outputs = [n for n in re.split(r"[\s,]+", outs.strip()) if n]
        self.inputs = [n for n in re.split(r"[\s,]+", ins.strip()) if n]
        if not self.outputs:
            raise BlockError("the function must return at least one output")
        self._code = _MatlabCode(source, function=True)

    def label(self):
        head = _SIGNATURE.search(str(self.params["code"]))
        return f"MATLAB Function\n{head.group('name')}" if head \
            else "MATLAB Function"
