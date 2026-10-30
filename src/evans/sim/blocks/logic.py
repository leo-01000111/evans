"""
Logic and bit operations: comparisons, Boolean logic, bitwise operators.

A logic signal is a number, ``1`` for true and ``0`` for false, and any
non-zero input counts as true, as in Simulink.

The comparisons are discontinuous, so they declare zero crossings and latch
their result between them (see :class:`~evans.sim.block.ModeLatch`): a
Relational Operator switching a Switch block's control lands on the exact
instant its inputs cross. Each one is written as tests of ``z >= 0``, the
solver's convention for a value of exactly zero, so ``a >= b`` at ``a = b``
is true and ``a > b`` is not, on the dot.
"""

from __future__ import annotations

import numpy as np

from ..block import Block, BlockError, ModeLatch, ParamSpec, register

_CAT = "Logic and Bit Operations"

_RELATIONS = ("==", "~=", "<", "<=", ">=", ">")


def _crossings(op: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The values whose sign decides ``a op b``, each tested as ``z >= 0``."""
    if op in (">=", "<"):
        return a - b
    if op in (">", "<="):
        return b - a
    return np.concatenate([a - b, b - a])          # == and ~=


def _decide(op: str, z: np.ndarray) -> np.ndarray:
    """``a op b`` from :func:`_crossings`' values."""
    pos = z >= 0
    if op == ">=":
        return pos
    if op == "<":
        return ~pos
    if op == "<=":
        return pos
    if op == ">":
        return ~pos
    n = len(z) // 2
    equal = pos[:n] & pos[n:]
    return equal if op == "==" else ~equal


class _Comparison(ModeLatch, Block):
    """Shared by the three comparison blocks: ``in1 op in2``."""

    def _operands(self, u) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def _op(self) -> str:
        return self.params["operator"]

    def _fresh_mode(self, u) -> np.ndarray:
        a, b = self._operands(u)
        return _decide(self._op(), _crossings(self._op(), a, b)).astype(float)

    def output(self, t, x, xd, u):
        return [self._mode_or(self._fresh_mode(u)).copy()]

    def output_widths(self, input_widths):
        return [max(input_widths) if input_widths else 1]

    def zero_crossings(self, t, x, xd, u):
        a, b = self._operands(u)
        return _crossings(self._op(), a, b)

    def n_zero_crossings(self, input_widths):
        width = max(input_widths) if input_widths else 1
        return 2 * width if self._op() in ("==", "~=") else width

    def update_modes(self, t, x, xd, u):
        return self._latch(self._fresh_mode(u))


def _broadcast(a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = np.atleast_1d(a), np.atleast_1d(b)
    width = max(len(a), len(b))
    return np.broadcast_to(a, width).astype(float), \
        np.broadcast_to(b, width).astype(float)


@register
class RelationalOperator(_Comparison):
    type_name = "RelationalOperator"
    category = _CAT
    description = "in1 op in2: ==, ~=, <, <=, >=, >; 1 when true."
    default_inputs = ("in1", "in2")
    params_spec = (
        ParamSpec("operator", "Operator", "<=", kind="choice",
                  choices=_RELATIONS),
    )

    def _operands(self, u):
        return _broadcast(u[0], u[1])

    def label(self):
        return self.params["operator"]


@register
class CompareToConstant(_Comparison):
    type_name = "CompareToConstant"
    category = _CAT
    description = "u op constant; 1 when true."
    params_spec = (
        ParamSpec("operator", "Operator", "<=", kind="choice",
                  choices=_RELATIONS),
        ParamSpec("constant", "Constant value", 3.0),
    )
    labels_expressions = True

    def _operands(self, u):
        return _broadcast(u[0], self.params["constant"])

    def label(self):
        return f"{self.params['operator']} {self.shown('constant')}"


@register
class CompareToZero(_Comparison):
    type_name = "CompareToZero"
    category = _CAT
    description = "u op 0; 1 when true."
    params_spec = (
        ParamSpec("operator", "Operator", "<=", kind="choice",
                  choices=_RELATIONS),
    )

    def _operands(self, u):
        return _broadcast(u[0], 0.0)

    def label(self):
        return f"{self.params['operator']} 0"


@register
class LogicalOperator(Block):
    type_name = "LogicalOperator"
    category = _CAT
    description = "AND, OR, NAND, NOR, XOR, NOT of its inputs; non-zero is true."
    params_spec = (
        ParamSpec("operator", "Operator", "AND", kind="choice",
                  choices=("AND", "OR", "NAND", "NOR", "XOR", "NOT")),
        ParamSpec("n_inputs", "Number of inputs", 2, kind="int"),
    )

    def configure(self) -> None:
        n = 1 if self.params["operator"] == "NOT" \
            else int(self.params["n_inputs"])
        if n < 1:
            raise BlockError("Logical Operator needs at least one input")
        self.inputs = [f"in{i + 1}" for i in range(n)]

    def output(self, t, x, xd, u):
        width = max((len(np.atleast_1d(v)) for v in u), default=1)
        values = [np.broadcast_to(np.atleast_1d(v), width) != 0 for v in u]
        op = self.params["operator"]
        if op == "NOT":
            result = ~values[0]
        elif op in ("AND", "NAND"):
            result = np.logical_and.reduce(values)
        elif op in ("OR", "NOR"):
            result = np.logical_or.reduce(values)
        else:
            result = np.logical_xor.reduce(values)
        if op in ("NAND", "NOR"):
            result = ~result
        return [result.astype(float)]

    def label(self):
        return self.params["operator"]


@register
class BitwiseOperator(Block):
    """
    Bitwise logic on whole numbers, as unsigned 32-bit integers.

    With a bit mask the operator combines the input with the mask; without
    one, it combines the inputs with each other. ``NOT`` takes one input.
    """

    type_name = "BitwiseOperator"
    category = _CAT
    description = "Bitwise AND, OR, XOR, NOT on whole numbers (32-bit)."
    params_spec = (
        ParamSpec("operator", "Operator", "AND", kind="choice",
                  choices=("AND", "OR", "XOR", "NOT")),
        ParamSpec("use_mask", "Use bit mask", True, kind="bool"),
        ParamSpec("mask", "Bit mask", 255.0),
        ParamSpec("n_inputs", "Number of inputs (no mask)", 2, kind="int"),
    )

    def configure(self) -> None:
        op = self.params["operator"]
        n = 1 if op == "NOT" or self.params["use_mask"] \
            else int(self.params["n_inputs"])
        if n < 1:
            raise BlockError("Bitwise Operator needs at least one input")
        self.inputs = [f"in{i + 1}" for i in range(n)]

    @staticmethod
    def _bits(value) -> np.ndarray:
        v = np.atleast_1d(np.asarray(value, dtype=float))
        return np.mod(np.trunc(v), 2.0 ** 32).astype(np.uint64)

    def output(self, t, x, xd, u):
        op = self.params["operator"]
        operands = [self._bits(v) for v in u]
        if op == "NOT":
            result = ~operands[0] & np.uint64(0xFFFFFFFF)
            return [result.astype(float)]
        if self.params["use_mask"]:
            operands.append(self._bits(self.params["mask"]))
        fn = {"AND": np.bitwise_and, "OR": np.bitwise_or,
              "XOR": np.bitwise_xor}[op]
        return [fn.reduce(np.broadcast_arrays(*operands)).astype(float)]

    def label(self):
        return f"bitwise\n{self.params['operator']}"
