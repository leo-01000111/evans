"""
Simulink from the console.
==========================
``sim``, ``new_system``, ``load_system``, ``open_system``, ``save_system``,
``close_system``, ``get_param``, ``set_param``, ``add_block``,
``delete_block``, ``add_line``, ``delete_line``, ``find_system`` and ``gcs``,
in MATLAB's syntax, on Evans models.

A mixin of :class:`.matlab_runtime._Library`; see :mod:`.lib_system` for how
the mixins are imported.

Which model a name means
------------------------
A model is named as in Simulink, by its file name without the extension. A
name is looked up among the models already loaded, then as the model on the
Model tab, then as ``name.fmdl`` in the current folder and on the path,
which loads it. Block paths are ``model/block``, and ``model/sub/block``
inside a subsystem.

Parameters
----------
``get_param`` returns text, as MATLAB does, and ``set_param`` takes text or
numbers. A number stays a number; other text is a workspace expression,
evaluated when the model runs, exactly as typed in the block's dialog.
Parameter names are matched loosely: Evans's own (``gain``, ``num``),
the label (``Upper limit``), or Simulink's (``Gain``, ``Numerator``,
``UpperLimit``, ``SampleTime``).

What ``sim`` returns
--------------------
A structure like Simulink's ``SimulationOutput``: ``out.tout`` (a column of
times), ``out.yout`` (the top-level Outports' signals, one column each, when
there are any), and one field per To Workspace block in its save format.
``sim`` given a model *object* from the Python side returns the Python
result instead, as it always has.
"""

from __future__ import annotations

import os
import re

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import Cell, MatlabError, Struct, _as_text, _nargout

#: Simulink's parameter names that are not Evans's name or label, by
#: normalised name. Each maps to the candidates tried, in order.
_ALIASES: dict[str, tuple[str, ...]] = {
    "numerator": ("num",),
    "denominator": ("den",),
    "p": ("Kp",),
    "i": ("Ki",),
    "d": ("Kd",),
    "n": ("Tf",),
    "upperlimit": ("upper",),
    "lowerlimit": ("lower",),
    "upperlimitsaturation": ("upper",),
    "lowerlimitsaturation": ("lower",),
    "upperlimitlimit": ("upper",),
    "sampletime": ("sample_time",),
    "initialcondition": ("x0",),
    "initialstate": ("x0",),
    "initialconditions": ("x0",),
    "variablename": ("name",),
    "saveformat": ("format",),
    "steptime": ("step_time",),
    "before": ("initial",),
    "after": ("final",),
    "listofsigns": ("signs",),
    "inputs": ("signs", "n_inputs"),
    "outputs": ("n_outputs",),
    "numinputs": ("n_inputs",),
    "numberofinputs": ("n_inputs",),
    "operator": ("operation", "relop", "logicop"),
    "function": ("function",),
    "expression": ("expr",),
    "expr": ("expr",),
    "deadzonestart": ("start",),
    "deadzoneend": ("end",),
    "risingslewlimit": ("rising",),
    "fallingslewlimit": ("falling",),
    "quantizationinterval": ("interval",),
    "deadtime": ("delay",),
    "delaytime": ("delay",),
    "timedelay": ("delay",),
    "initialoutput": ("x0", "initial"),
    "threshold": ("threshold",),
    "breakpointsfordimension1": ("x_table",),
    "breakpointsfordimension2": ("y_table",),
    "breakpointsdata": ("x_table",),
    "inputvalues": ("x_table",),
    "outputvalues": ("y_table",),
    "table": ("y_table", "table"),
    "tabledata": ("y_table", "table"),
    "elements": ("index",),
    "indices": ("index",),
    "zeros": ("zeros",),
    "poles": ("poles",),
    "variable": ("data",),
    "data": ("data",),
    "outputafterfinalvalue": ("after",),
    "interpolatedata": ("interpolate",),
    "port": ("order",),
    "portnumber": ("order",),
    "constantvalue": ("value",),
    "bias": ("bias",),
    "phase": ("phase",),
    "frequency": ("frequency",),
    "amplitude": ("amplitude",),
    "period": ("period",),
    "pulsewidth": ("duty",),
    "phasedelay": ("delay",),
    "seed": ("seed",),
    "datastorename": ("store",),
    "gototag": ("tag",),
    "tag": ("tag",),
}

#: Simulink's library names for blocks whose Evans name differs (after
#: dropping spaces and case): what ``add_block`` accepts as a source.
_BLOCK_NAMES: dict[str, str] = {
    "transferfcn": "TransferFcn",
    "transferfunction": "TransferFcn",
    "statespace": "StateSpace",
    "zeropole": "ZeroPole",
    "pidcontroller": "PID",
    "discretepidcontroller": "DiscretePID",
    "discretetransferfcn": "DiscreteTF",
    "discretestatespace": "DiscreteSS",
    "zeroorderhold": "ZeroOrderHold",
    "sinewave": "Sine",
    "pulsegenerator": "Pulse",
    "bandlimitedwhitenoise": "Noise",
    "randomnumber": "Noise",
    "transportdelay": "TransportDelay",
    "1dlookuptable": "Lookup1D",
    "1-dlookuptable": "Lookup1D",
    "lookuptable": "Lookup1D",
    "2dlookuptable": "Lookup2D",
    "2-dlookuptable": "Lookup2D",
    "nlookuptable": "Lookup1D",
    "deadzone": "DeadZone",
    "ratelimiter": "RateLimiter",
    "coulombandviscousfriction": "CoulombFriction",
    "mathfunction": "MathFunction",
    "trigonometricfunction": "Trig",
    "minmax": "MinMax",
    "add": "Sum",
    "subtract": "Sum",
    "sumofelements": "Sum",
    "divide": "Product",
    "toworkspace": "ToWorkspace",
    "fromworkspace": "FromWorkspace",
    "stopsimulation": "StopSimulation",
    "in1": "Inport",
    "out1": "Outport",
    "subsystem": "Subsystem",
    "matlabfunction": "MATLABFunction",
    "fcn": "Fcn",
    "relationaloperator": "RelationalOperator",
    "logicaloperator": "LogicalOperator",
    "comparetoconstant": "CompareToConstant",
    "comparetozero": "CompareToZero",
    "bitwiseoperator": "BitwiseOperator",
    "discretetimeintegrator": "DiscreteIntegrator",
    "discretefirfilter": "DiscreteFIR",
    "discretefilter": "DiscreteFilter",
    "repeatingsequence": "RepeatingSequence",
    "signalbuilder": "SignalBuilder",
    "counterlimited": "Counter",
    "counterfreerunning": "Counter",
    "datastoreread": "DataStoreRead",
    "datastorewrite": "DataStoreWrite",
    "datastorememory": "DataStoreMemory",
    "xygraph": "XYGraph",
    "prelookup": "Prelookup",
    "enable": "Enable",
    "trigger": "Trigger",
    "goto": "Goto",
    "from": "From",
    "ifactionsubsystem": "Subsystem",
    "enabledsubsystem": "Subsystem",
    "triggeredsubsystem": "Subsystem",
}

#: Run settings ``get_param`` and ``set_param`` accept on a model, with the
#: setting each one is stored as.
_SETTINGS = {
    "stoptime": "StopTime",
    "solver": "Solver",
    "solvername": "Solver",
    "maxstep": "MaxStep",
    "fixedstep": "MaxStep",
    "reltol": "RelTol",
    "abstol": "AbsTol",
}


class SimulinkLibrary:
    """The Simulink commands; see the module docstring."""

    # ── running ─────────────────────────────────────────────────

    @_nargout
    def f_sim(self, model, *args, nargout=1):
        from ..sim.compile import CompileError
        from ..sim.model import ModelError, SimModel
        from ..sim.solver import SimulationError, simulate

        legacy = isinstance(model, SimModel)
        target = model if legacy else self._model(model)
        settings = dict(target.settings)
        rest = list(args)
        if rest and not isinstance(rest[0], str) \
                and not isinstance(rest[0], dict):
            span = np.asarray(rest.pop(0), dtype=float).reshape(-1)
            if span.size:
                settings["StopTime"] = float(span[-1])
        pairs: list = []
        for item in rest:
            if isinstance(item, dict):
                pairs += [x for kv in item.items() for x in kv]
            else:
                pairs.append(item)
        if len(pairs) % 2:
            raise MatlabError("sim: options come in name-value pairs.")
        for name, value in zip(pairs[::2], pairs[1::2]):
            key = _norm(_as_text(name))
            if key == "starttime":
                if _number(value) != 0:
                    raise MatlabError("sim: Evans runs start at t = 0.")
                continue
            if key in ("srcworkspace", "returnworkspaceoutputs",
                       "savetime", "saveoutput", "savestate"):
                continue
            if key not in _SETTINGS:
                raise MatlabError(f"sim: unknown option '{_as_text(name)}'.")
            setting = _SETTINGS[key]
            settings[setting] = _as_text(value) if setting == "Solver" \
                else _number(value)

        def tick(_fraction: float) -> None:
            from .lib_system import _stop_requested
            if _stop_requested(self.rt):
                raise SimulationError("stopped")

        step = float(settings.get("MaxStep") or 0.0)
        try:
            result = simulate(
                target, t_end=float(settings["StopTime"]),
                solver=str(settings["Solver"]),
                max_step=step if step > 0 else None,
                rtol=float(settings["RelTol"]),
                atol=float(settings["AbsTol"]),
                progress=tick, evaluate=self.rt.evaluate)
        except (SimulationError, CompileError, ModelError) as exc:
            raise MatlabError(f"sim: {exc}") from None
        if legacy:
            return result
        return simulation_output(result)

    # ── models ──────────────────────────────────────────────────

    def f_new_system(self, name=None, *_):
        from ..sim.model import SimModel
        name = _as_text(name) if name is not None else "untitled"
        if name in self.rt.models:
            raise MatlabError(f"A model named '{name}' is already loaded.")
        self.rt.models[name] = SimModel(name)
        return name

    @_nargout
    def f_load_system(self, name, nargout=0):
        model = self._model(name)
        return model.name if nargout else None

    @_nargout
    def f_open_system(self, name, *_, nargout=0):
        model = self._model(name)
        bridge = self._bridge()
        if bridge is not None:
            bridge.show(model)
        return model.name if nargout else None

    def f_close_system(self, name=None, *_):
        if name is None:
            self.rt.models.clear()
            return None
        model_name = _as_text(name).split("/")[0]
        if model_name.lower().endswith(".fmdl"):
            model_name = os.path.splitext(os.path.basename(model_name))[0]
        self.rt.models.pop(model_name, None)
        return None

    f_bdclose = f_close_system

    @_nargout
    def f_save_system(self, name=None, path=None, *_, nargout=0):
        model = self._model(name) if name is not None else self._current()
        target = self.rt.resolve(_as_text(path)) if path is not None \
            else os.path.join(self.rt.folder, f"{model.name}.fmdl")
        if not target.lower().endswith(".fmdl"):
            target += ".fmdl"
        old = model.name
        model.save(target)
        self.rt.models.pop(old, None)
        self.rt.models[model.name] = model
        return target if nargout else None

    @_nargout
    def f_gcs(self, nargout=1):
        return self._current().name

    f_bdroot = f_gcs

    @_nargout
    def f_find_system(self, name=None, *args, nargout=1):
        model = self._model(name) if name is not None else self._current()
        pairs = [a for a in args if not (isinstance(a, str) and a.lower() in (
            "searchdepth", "lookundermasks", "followlinks"))]
        wanted: dict[str, str] = {}
        for key, value in zip(pairs[::2], pairs[1::2]):
            if isinstance(key, str) and _norm(key) == "blocktype":
                wanted["type"] = _block_type(_as_text(value))
            elif isinstance(key, str) and _norm(key) == "name":
                wanted["name"] = _as_text(value)
        paths = [model.name]
        for path, block in _walk(model, model.name):
            if "type" in wanted and block.type_name != wanted["type"]:
                continue
            if "name" in wanted and block.block_id != wanted["name"]:
                continue
            paths.append(path)
        if wanted:
            paths = paths[1:]
        return Cell(paths, rows=len(paths))

    # ── parameters ──────────────────────────────────────────────

    @_nargout
    def f_get_param(self, obj, name, nargout=1):
        key = _norm(_as_text(name))
        model, parts = self._split(obj)
        if not parts:
            if key in _SETTINGS:
                return _param_text(model.settings[_SETTINGS[key]])
            if key == "name":
                return model.name
            if key in ("blocks", "objectparameters"):
                return Cell([b.block_id for b in model], rows=len(model))
            raise MatlabError(
                f"get_param: a model has no parameter '{_as_text(name)}'. "
                f"Evans models have StopTime, Solver, MaxStep, RelTol and "
                f"AbsTol.")
        block = _block_at(model, parts)
        if key == "blocktype":
            return block.type_name
        if key == "name":
            return block.block_id
        if key == "parent":
            return "/".join([model.name, *parts[:-1]])
        if key == "dialogparameters":
            return Struct({spec.name: Struct() for spec in block.params_spec
                           if spec.kind != "model"})
        if key == "position":
            place = _placement(model, parts)
            return np.array([[place.x - 55, place.y - 30,
                              place.x + 55, place.y + 30]])
        param = _param_name(block, name)
        return _param_text(block.raw_params()[param])

    def f_set_param(self, obj, *args):
        if len(args) % 2:
            raise MatlabError("set_param: parameters come in name-value "
                              "pairs.")
        from ..sim.block import BlockError
        model, parts = self._split(obj)
        if not parts:
            for name, value in zip(args[::2], args[1::2]):
                key = _norm(_as_text(name))
                if key == "simulationcommand":
                    raise MatlabError("set_param: run a model with sim.")
                if key not in _SETTINGS:
                    raise MatlabError(
                        f"set_param: a model has no parameter "
                        f"'{_as_text(name)}'.")
                setting = _SETTINGS[key]
                model.settings[setting] = _as_text(value) \
                    if setting == "Solver" else _number(value)
            self._changed(model)
            return None

        def apply(block):
            for name, value in zip(args[::2], args[1::2]):
                key = _norm(_as_text(name))
                if key == "position":
                    continue                    # placed by _edit_block
                param = _param_name(block, name)
                try:
                    block.set_param(param, _param_value(block, param, value))
                except (BlockError, ValueError, TypeError) as exc:
                    raise MatlabError(
                        f"set_param: {'/'.join([model.name, *parts])}: "
                        f"{exc}") from None
        position = next((v for k, v in zip(args[::2], args[1::2])
                         if _norm(_as_text(k)) == "position"), None)
        _edit_block(model, parts, apply, position)
        self._changed(model)
        return None

    # ── building models ─────────────────────────────────────────

    @_nargout
    def f_add_block(self, source, dest, *args, nargout=0):
        from ..sim.block import BlockError
        from ..sim.model import ModelError
        type_name = _block_type(_as_text(source).split("/")[-1])
        model, parts = self._split(dest)
        if not parts:
            raise MatlabError("add_block: the destination is model/name.")
        if len(args) % 2:
            raise MatlabError("add_block: parameters come in name-value "
                              "pairs.")
        name = parts[-1]

        def add(target):
            if name in target.blocks:
                raise MatlabError(f"add_block: '{name}' already exists.")
            x, y = _free_spot(target)
            try:
                block = target.add(type_name, name, x=x, y=y)
            except (BlockError, ModelError) as exc:
                raise MatlabError(f"add_block: {exc}") from None
            for key, value in zip(args[::2], args[1::2]):
                if _norm(_as_text(key)) == "position":
                    target.move(name, *_centre(value))
                    continue
                param = _param_name(block, key)
                try:
                    block.set_param(param, _param_value(block, param, value))
                except (BlockError, ValueError, TypeError) as exc:
                    raise MatlabError(f"add_block: {name}: {exc}") from None
        _in_parent(model, parts, add)
        self._changed(model)
        return "/".join([model.name, *parts]) if nargout else None

    def f_delete_block(self, path):
        from ..sim.model import ModelError
        model, parts = self._split(path)
        if not parts:
            raise MatlabError("delete_block: name a block, model/name.")

        def remove(target):
            try:
                target.remove(parts[-1])
            except ModelError as exc:
                raise MatlabError(f"delete_block: {exc}") from None
        _in_parent(model, parts, remove)
        self._changed(model)

    def f_add_line(self, system, src, dst, *_):
        from ..sim.model import ModelError
        model, parts = self._split(system)

        def wire(target):
            a = _port_spec(target, _as_text(src), output=True)
            b = _port_spec(target, _as_text(dst), output=False)
            try:
                target.connect(a, b)
            except ModelError as exc:
                raise MatlabError(f"add_line: {exc}") from None
        _in_system(model, parts, wire)
        self._changed(model)

    def f_delete_line(self, system, src, dst=None, *_):
        model, parts = self._split(system)

        def unwire(target):
            b = None
            if dst is not None:
                b = _port_spec(target, _as_text(dst), output=False)
            a = _port_spec(target, _as_text(src), output=True)
            for conn in target.connections:
                if f"{conn.src}" == a and (b is None or f"{conn.dst}" == b):
                    target.disconnect(conn)
                    return
            raise MatlabError(f"delete_line: no line from {_as_text(src)}.")
        _in_system(model, parts, unwire)
        self._changed(model)

    # ── helpers ─────────────────────────────────────────────────

    def _bridge(self):
        return getattr(self.rt.host, "simulink", None) \
            if self.rt.host is not None else None

    def _current(self):
        """The model on the Model tab, else the last one loaded."""
        bridge = self._bridge()
        if bridge is not None:
            return bridge.model()
        if self.rt.models:
            return list(self.rt.models.values())[-1]
        raise MatlabError("No model is loaded; use load_system or "
                          "new_system first.")

    def _model(self, name):
        """A model by name (or path, or file name), loading it if need be."""
        from ..sim.model import SimModel
        if isinstance(name, SimModel):
            return name
        text = _as_text(name).strip()
        if not text:
            raise MatlabError("A model name is empty.")
        head = text.replace("\\", "/")
        if head.lower().endswith(".fmdl"):
            path = self.rt.resolve(head)
            stem = os.path.splitext(os.path.basename(path))[0]
            if stem in self.rt.models:
                return self.rt.models[stem]
            return self._load(path)
        head = head.split("/")[0]
        # The model on screen first: it is the live one, and a copy loaded
        # earlier under the same name would be edited behind its back.
        bridge = self._bridge()
        if bridge is not None and bridge.model().name == head:
            return bridge.model()
        if head in self.rt.models:
            return self.rt.models[head]
        for folder in [self.rt.folder, *self.rt.path]:
            path = os.path.join(folder, f"{head}.fmdl")
            if os.path.isfile(path):
                return self._load(path)
        raise MatlabError(
            f"'{head}' is not loaded, and there is no {head}.fmdl in the "
            f"current folder or on the path.")

    def _load(self, path: str):
        from ..sim.model import ModelError, SimModel
        try:
            model = SimModel.load(path)
        except (ModelError, OSError, ValueError) as exc:
            raise MatlabError(f"Cannot load {path}: {exc}") from None
        self.rt.models[model.name] = model
        return model

    def _split(self, obj):
        """``(model, [block, …])`` from a path such as ``'m/sub/Gain1'``."""
        from ..sim.model import SimModel
        if isinstance(obj, SimModel):
            return obj, []
        text = _as_text(obj).replace("\\", "/").strip("/")
        if text.lower().endswith(".fmdl"):
            return self._model(text), []
        head, *parts = text.split("/")
        return self._model(head), parts

    def _changed(self, model) -> None:
        """Tell the Model tab, when the model edited is the one it shows."""
        bridge = self._bridge()
        if bridge is not None:
            bridge.changed(model)


# ──────────────────────────────────────────────────────────────
#  The output of a run
# ──────────────────────────────────────────────────────────────

def simulation_output(result) -> Struct:
    """
    A run as Simulink's ``SimulationOutput``: ``tout``, ``yout`` and one
    field per To Workspace block, each in its block's save format.
    """
    t = np.asarray(result.t, dtype=float).reshape(-1, 1)
    out = Struct()
    out["tout"] = t
    if result.outputs:
        out["yout"] = np.hstack([result.signals[name]
                                 for name in result.outputs])
    for name, values in result.workspace.items():
        out[name] = _saved(name, values, t,
                           result.formats.get(name, "Array"))
    return out


def _saved(name: str, values, t, fmt: str):
    values = np.asarray(values, dtype=float)
    if fmt == "Timeseries":
        return Struct(Name=name, Time=t.copy(), Data=values)
    if fmt == "Structure With Time":
        return Struct(time=t.copy(), signals=Struct(
            values=values, dimensions=float(values.shape[1]), label=""),
            blockName=name)
    return values


# ──────────────────────────────────────────────────────────────
#  Names, paths and values
# ──────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _number(value) -> float:
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            raise MatlabError(f"'{value}' is not a number.") from None
    return float(np.asarray(value, dtype=float).reshape(-1)[0])


def _block_type(name: str) -> str:
    """An Evans block type from Evans's or Simulink's name for it."""
    from ..sim.block import block_types
    types = block_types()
    if name in types:
        return name
    key = _norm(name)
    for type_name in types:
        if _norm(type_name) == key:
            return type_name
    if key in _BLOCK_NAMES and _BLOCK_NAMES[key] in types:
        return _BLOCK_NAMES[key]
    raise MatlabError(
        f"There is no block '{name}' in Evans's library. Its blocks are: "
        f"{', '.join(sorted(types))}.")


def _param_name(block, name) -> str:
    """The block's parameter that ``name`` means, or a MatlabError."""
    text = _as_text(name)
    key = _norm(text)
    specs = [s for s in block.params_spec if s.kind != "model"]
    for spec in specs:
        if spec.name == text:
            return spec.name
    for spec in specs:
        if _norm(spec.name) == key:
            return spec.name
    for spec in specs:
        if _norm(spec.label) == key:
            return spec.name
    names = {s.name for s in specs}
    for candidate in _ALIASES.get(key, ()):
        if candidate in names:
            return candidate
    raise MatlabError(
        f"{block.type_name} block '{block.block_id}' has no parameter "
        f"'{text}'. Its parameters are: "
        f"{', '.join(s.name for s in specs) or '(none)'}.")


def _param_value(block, param: str, value):
    """A value from MATLAB as the block stores it."""
    spec = block.spec(param)
    if isinstance(value, str):
        text = value.strip()
        if spec.kind == "bool":
            return text.lower() in ("on", "true", "1", "yes")
        if spec.kind == "int":
            return int(float(text))
        return text
    if spec.kind == "bool":
        return bool(np.asarray(value).reshape(-1)[0])
    if spec.kind == "int":
        return int(_number(value))
    if spec.kind in ("str", "choice"):
        return _as_text(value)
    arr = np.asarray(value, dtype=float)
    if spec.kind == "float":
        return float(arr.reshape(-1)[0]) if arr.size == 1 else arr.reshape(-1)
    if spec.kind == "vector":
        return arr.reshape(-1)
    return value


def _param_text(value) -> str:
    """A parameter as ``get_param`` returns it: text."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"{float(value):.15g}"
    arr = np.asarray(value)
    if arr.dtype == object:
        return str(value)
    arr = np.atleast_1d(arr.astype(float))
    if arr.ndim == 1:
        return "[" + " ".join(f"{v:.15g}" for v in arr) + "]"
    return "[" + "; ".join(" ".join(f"{v:.15g}" for v in row)
                           for row in arr) + "]"


def _walk(model, prefix: str):
    """Every block's path and block, inside subsystems too."""
    for block in model:
        path = f"{prefix}/{block.block_id}"
        yield path, block
        if block.type_name == "Subsystem":
            yield from _walk(block.inner_model(), path)


def _block_at(model, parts: list[str]):
    """The block at ``parts`` (read-only: a subsystem's copy)."""
    from ..sim.model import ModelError
    target = model
    for depth, name in enumerate(parts):
        try:
            block = target.block(name)
        except ModelError:
            raise MatlabError(
                f"There is no block '{'/'.join([model.name, *parts[:depth + 1]])}'"
                f".") from None
        if depth == len(parts) - 1:
            return block
        if block.type_name != "Subsystem":
            raise MatlabError(f"'{name}' is not a subsystem.")
        target = block.inner_model()
    raise MatlabError("No block named.")


def _placement(model, parts: list[str]):
    target = model
    for name in parts[:-1]:
        target = _block_at(target, [name]).inner_model()
    return target.placement(parts[-1])


def _in_system(model, parts: list[str], fn) -> None:
    """Run ``fn`` on the (sub)system at ``parts``, writing a subsystem back."""
    if not parts:
        fn(model)
        return
    sub = _block_at(model, parts[:1])
    if sub.type_name != "Subsystem":
        raise MatlabError(f"'{parts[0]}' is not a subsystem.")
    inner = sub.inner_model()
    _in_system(inner, parts[1:], fn)
    sub.set_param("model", inner.to_dict())


def _in_parent(model, parts: list[str], fn) -> None:
    """Run ``fn`` on the system that holds the block ``parts[-1]``."""
    _in_system(model, parts[:-1], fn)


def _edit_block(model, parts: list[str], fn, position=None) -> None:
    def edit(system):
        block = _block_at(system, parts[-1:])
        fn(block)
        if position is not None:
            system.move(block.block_id, *_centre(position))
    _in_parent(model, parts, edit)


def _centre(position) -> tuple[float, float]:
    """A Simulink Position ``[left top right bottom]`` as a centre point."""
    p = np.asarray(position, dtype=float).reshape(-1)
    if p.size != 4:
        raise MatlabError("Position is [left top right bottom].")
    return float((p[0] + p[2]) / 2), float((p[1] + p[3]) / 2)


def _free_spot(model) -> tuple[float, float]:
    """Right of whatever is there, so a scripted model is readable."""
    if len(model) == 0:
        return 0.0, 0.0
    xs = [model.placement(b.block_id).x for b in model]
    ys = [model.placement(b.block_id).y for b in model]
    return max(xs) + 160.0, float(np.median(ys))


def _port_spec(model, spec: str, output: bool) -> str:
    """``'Gain1/1'`` (Simulink) or ``'Gain1/in'`` as ``'Gain1.in'``."""
    from ..sim.model import ModelError
    block_name, _, port = spec.replace(".", "/").partition("/")
    try:
        block = model.block(block_name)
    except ModelError:
        raise MatlabError(f"There is no block '{block_name}' in "
                          f"{model.name}.") from None
    ports = block.outputs if output else block.inputs
    if not port:
        port = "1"
    if port.isdigit():
        index = int(port) - 1
        if not 0 <= index < len(ports):
            kind = "output" if output else "input"
            raise MatlabError(
                f"{block_name} has {len(ports)} {kind} port"
                f"{'s' if len(ports) != 1 else ''}; there is no port {port}.")
        port = ports[index]
    elif port not in ports:
        raise MatlabError(f"{block_name} has no port '{port}'; its ports are "
                          f"{', '.join(ports) or '(none)'}.")
    return f"{block_name}.{port}"
