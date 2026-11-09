"""
User classes: ``classdef`` files.
=================================
A ``Name.m`` file that starts with ``classdef`` is translated by
:mod:`.matlab` into one Python function per method and a call to
:meth:`.Runtime.make_class`, which builds a :class:`ClassDef` from them.
Calling ``Name(...)`` then makes a :class:`ClassObject`.

Value classes copy on write, by the same ``_shared`` mark cells and structs
use (see :func:`.matlab_runtime.share`); handle classes (``< handle``) are
shared references and are never copied. Dispatch on the object, ``obj.f(x)``
and ``f(obj, x)``, runs the same method; ``Runtime.lookup`` returns a
:class:`Dispatcher` for any name a loaded class defines.

Import :mod:`.matlab_runtime` first; the two import each other.
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np

from .matlab_runtime import MatlabError, Struct, _brief, share

#: Superclasses that are not files: they make a class a handle class.
BUILTIN_SUPERS = {"handle": False, "matlab.mixin.Copyable": True,
                  "matlab.mixin.SetGet": False,
                  "matlab.mixin.Heterogeneous": False}

_OPERATORS = {
    "plus": "+", "minus": "-", "times": ".*", "mtimes": "*",
    "rdivide": "./", "mrdivide": "/", "ldivide": ".\\", "mldivide": "\\",
    "power": ".^", "mpower": "^", "eq": "==", "ne": "~=", "lt": "<",
    "le": "<=", "gt": ">", "ge": ">=",
}


class PropDef:
    def __init__(self, name, default_fn, attrs, owner):
        self.name = name
        self.default_fn = default_fn
        self.attrs = attrs
        self.owner = owner
        self._value: Any = None
        self._have = False
        access = attrs.get("Access", "public")
        self.get_access = attrs.get("GetAccess", access)
        self.set_access = attrs.get("SetAccess", access)
        self.constant = bool(attrs.get("Constant"))
        self.hidden = bool(attrs.get("Hidden"))

    def value(self):
        """The default, worked out once; marked shared so writes copy it."""
        if not self._have:
            v = self.default_fn() if self.default_fn else np.zeros((0, 0))
            self._value = share(v)
            self._have = True
        return self._value


class MethodDef:
    def __init__(self, name, fn, kind, attrs, explicit_supers, owner):
        self.name = name
        self.fn = fn
        self.kind = kind          # method ctor get set
        self.attrs = attrs
        self.explicit_supers = set(explicit_supers)
        self.owner = owner
        self.static = bool(attrs.get("Static"))
        self.access = attrs.get("Access", "public")
        self.hidden = bool(attrs.get("Hidden"))


class ClassDef:
    def __init__(self, rt, name, supers, attrs, handle, copyable):
        self.rt = rt
        self.name = name
        self.supers: list[ClassDef] = supers
        self.attrs = attrs
        self.handle = handle
        self.copyable = copyable
        self.props: dict[str, PropDef] = {}
        self.methods: dict[str, MethodDef] = {}
        self.enums: list = []
        self.events: list[str] = []
        self._members: dict[str, ClassObject] = {}

    def __repr__(self) -> str:
        return f"  class {self.name}"

    # structure -------------------------------------------------------

    def mro(self) -> list[ClassDef]:
        out = [self]
        for s in self.supers:
            for c in s.mro():
                if c not in out:
                    out.append(c)
        return out

    def isa(self, name: str) -> bool:
        return name == self.name or (name == "handle" and self.handle) \
            or any(s.isa(name) for s in self.supers)

    def find_prop(self, name: str) -> PropDef | None:
        for c in self.mro():
            if name in c.props:
                return c.props[name]
        return None

    def find_method(self, name: str) -> MethodDef | None:
        for c in self.mro():
            if name in c.methods:
                return c.methods[name]
        return None

    def all_props(self) -> list[PropDef]:
        seen: dict[str, PropDef] = {}
        for c in reversed(self.mro()):
            for p in c.props.values():
                seen.setdefault(p.name, p)
        return list(seen.values())

    def public_methods(self) -> list[str]:
        names = {}
        for c in reversed(self.mro()):
            for m in c.methods.values():
                if m.kind in ("get", "set") or m.hidden \
                        or m.access != "public":
                    continue
                names[m.name] = True
        return sorted(names)

    # making objects ----------------------------------------------------

    def constructor(self):
        """``Name(...)`` as the function the interpreter calls."""
        def fn(*args, nargout=1):
            return self.construct(args)
        fn._ml_function = fn._ml_nargout = True
        fn._ml_class = self
        fn.__name__ = self.name
        return fn

    def construct(self, args: tuple) -> ClassObject:
        if self.attrs.get("Abstract"):
            raise MatlabError(f"Cannot instantiate abstract class "
                              f"'{self.name}'.")
        if self.enums:
            raise MatlabError(f"Cannot create an object of enumeration class "
                              f"'{self.name}'; use one of its members.")
        obj = ClassObject(self)
        self.init_props(obj)
        return self.run_ctor(obj, args)

    def init_props(self, obj: ClassObject) -> None:
        for p in self.all_props():
            if not p.constant:
                obj.props[p.name] = p.value()

    def run_ctor(self, obj: ClassObject, args: tuple) -> ClassObject:
        ctor = self.methods.get(self.name)
        if ctor is None:
            for s in self.supers:
                obj = s.run_ctor(obj, ())
            if args:
                raise MatlabError("Too many input arguments.")
            return obj
        for s in self.supers:
            if s.name not in ctor.explicit_supers:
                obj = s.run_ctor(obj, ())
        result = invoke(self.rt, ctor, args, 1, _self=obj)
        if not isinstance(result, ClassObject):
            raise MatlabError(f"Output argument of the constructor of "
                              f"'{self.name}' was not assigned.")
        return result

    def member(self, name: str) -> ClassObject | None:
        """An enumeration member, made on first use."""
        if name not in self._members:
            for n, args in self.enums:
                if n == name:
                    obj = ClassObject(self)
                    obj.enum = name
                    self.init_props(obj)
                    self._members[name] = self.run_ctor(obj, args())
                    self._members[name].enum = name
                    break
            else:
                return None
        return self._members[name]

    def static_member(self, name: str):
        """``Class.name``: an enumeration member, a constant or a static."""
        m = self.member(name)
        if m is not None:
            return m
        p = self.find_prop(name)
        if p is not None and p.constant:
            return p.value()
        meth = self.find_method(name)
        if meth is not None and meth.static:
            return BoundMethod(self.rt, meth, None)
        raise MatlabError(f"Unrecognized method, property, or field "
                          f"'{name}' for class '{self.name}'.",
                          "MATLAB:noSuchMethodOrField")


class ClassObject:
    """An instance. Value objects are copied on write; handles are not."""

    _shared = False

    def __init__(self, cls: ClassDef) -> None:
        self.cls = cls
        self.props: dict[str, Any] = {}
        self.alive = True
        self.enum: str | None = None
        self.listeners: list = []

    def __copy__(self):
        new = ClassObject.__new__(ClassObject)
        new.__dict__.update(self.__dict__)
        new.props = dict(self.props)
        new._shared = False
        return new

    def __repr__(self) -> str:
        return default_text(self)


class BoundMethod:
    """``obj.method``: callable with the rest of the arguments."""

    _ml_function = True
    _ml_nargout = True

    def __init__(self, rt, method: MethodDef, obj) -> None:
        self.rt = rt
        self.method = method
        self.obj = obj
        self.__name__ = method.name

    def __call__(self, *args, nargout=1):
        if self.obj is not None:
            args = (self.obj, *args)
        return invoke(self.rt, self.method, args, nargout)


class Dispatcher:
    """A function name some loaded class defines a method for."""

    _ml_function = True
    _ml_nargout = True

    def __init__(self, rt, name: str, glob: dict, loc: dict) -> None:
        self.rt = rt
        self.name = name
        self.glob = glob
        self.loc = loc
        self.__name__ = name

    def __call__(self, *args, nargout=1):
        for a in args:
            if isinstance(a, ClassObject):
                m = a.cls.find_method(self.name)
                if m is not None and not m.static:
                    return invoke(self.rt, m, args, nargout)
        plain = self.rt.lookup(self.name, self.glob, self.loc,
                               dispatch=False)
        return self.rt.call(plain, args, nargout=nargout)


class Listener:
    def __init__(self, source, event: str, fn) -> None:
        self.source = source
        self.event = event
        self.fn = fn
        self.enabled = True


# ──────────────────────────────────────────────────────────────
#  Running methods
# ──────────────────────────────────────────────────────────────

def invoke(rt, method: MethodDef, args: tuple, nargout: int = 1, **extra):
    """Call a method with its class on the access stack."""
    rt.class_ctx.append(method.owner)
    try:
        result = method.fn(*args, nargout=nargout, **extra)
    finally:
        rt.class_ctx.pop()
    if nargout == 1 and type(result) is tuple:
        result = result[0]
    return result


def build(rt, name, supers, attrs, props, methods, enums, events) -> ClassDef:
    handle = copyable = False
    resolved = []
    for s in supers:
        if s in BUILTIN_SUPERS:
            handle = True
            copyable = copyable or BUILTIN_SUPERS[s]
            continue
        sc = rt.class_named(s)
        handle = handle or sc.handle
        copyable = copyable or sc.copyable
        resolved.append(sc)
    cls = ClassDef(rt, name, resolved, attrs, handle, copyable)
    for pname, fn, pattrs in props:
        cls.props[pname] = PropDef(pname, fn, pattrs, cls)
    for mname, fn, kind, mattrs, explicit in methods:
        cls.methods[mname] = MethodDef(mname, fn, kind, mattrs, explicit,
                                       cls)
    cls.enums = enums
    cls.events = list(events)
    rt.method_index.update(m for m in cls.methods
                           if m != name and m != "delete"
                           and not m.startswith(("get.", "set.")))
    return cls


def super_call(rt, klass, superclass, method, args, nargout, obj=None):
    if superclass in BUILTIN_SUPERS:
        return obj
    sc = rt.class_named(superclass)
    m = sc.find_method(method)
    if m is None or m.kind == "ctor":          # obj = obj@Super(args)
        return sc.run_ctor(obj, tuple(args))
    return invoke(rt, m, args, nargout)


# ──────────────────────────────────────────────────────────────
#  Properties
# ──────────────────────────────────────────────────────────────

def _check(rt, access, p: PropDef, verb: str) -> None:
    if access == "public":
        return
    ctx = rt.class_ctx[-1] if rt.class_ctx else None
    ok = False
    if ctx is not None:
        if isinstance(access, list):
            ok = ctx is p.owner or ctx.name in access
        elif access == "private":
            ok = ctx is p.owner
        else:
            ok = ctx.isa(p.owner.name) or p.owner.isa(ctx.name)
    if not ok:
        raise MatlabError(
            f"You cannot {verb} the '{p.name}' property of {p.owner.name} "
            f"class.", f"MATLAB:class:{verb.capitalize()}Prohibited")


def _alive(obj: ClassObject) -> None:
    if not obj.alive:
        raise MatlabError("Invalid or deleted object.")


def get_property(obj: ClassObject, name: str):
    """``obj.name``: a property's value, or a method called on ``obj``."""
    cls = obj.cls
    rt = cls.rt
    _alive(obj)
    p = cls.find_prop(name)
    if p is None:
        m = cls.find_method(name)
        if m is not None and m.kind == "method":
            if m.access != "public":
                _check(rt, m.access, PropDef(name, None, {}, m.owner), "call")
            return BoundMethod(rt, m, None if m.static else obj)
        raise MatlabError(f"Unrecognized method, property, or field "
                          f"'{name}' for class '{cls.name}'.",
                          "MATLAB:noSuchMethodOrField")
    _check(rt, p.get_access, p, "get")
    if p.constant:
        return p.value()
    getter = cls.find_method("get." + name)
    key = (cls.name, name, "get")
    if getter is not None and key not in rt.class_busy:
        rt.class_busy.add(key)
        try:
            return invoke(rt, getter, (obj,), 1)
        finally:
            rt.class_busy.discard(key)
    return obj.props.get(name, np.zeros((0, 0)))


def assign_object(rt, obj: ClassObject, path: list, value, owned: bool):
    """``obj.name... = value``; the object, copied first if it is a value."""
    (kind, key), rest = path[0], path[1:]
    if kind != ".":
        raise MatlabError("Indexing an object with () or {} is not "
                          "supported; assign to one of its properties.")
    cls = obj.cls
    _alive(obj)
    p = cls.find_prop(key)
    if p is None:
        raise MatlabError(f"Unrecognized property '{key}' for class "
                          f"'{cls.name}'.", "MATLAB:noSuchMethodOrField")
    if p.constant:
        raise MatlabError(f"Cannot set the Constant property '{key}' of "
                          f"class '{cls.name}'.")
    _check(rt, p.set_access, p, "set")
    if not cls.handle and not (owned and not obj._shared):
        obj = copy.copy(obj)
    if rest:
        value = rt.assign(obj.props.get(key), rest, value, owned)
    setter = cls.find_method("set." + key)
    busy = (cls.name, key, "set")
    if setter is not None and busy not in rt.class_busy:
        rt.class_busy.add(busy)
        try:
            result = invoke(rt, setter, (obj, value), 0 if cls.handle else 1)
        finally:
            rt.class_busy.discard(busy)
        if isinstance(result, ClassObject):
            obj = result
        return obj
    obj.props[key] = value
    return obj


# ──────────────────────────────────────────────────────────────
#  Operators and display
# ──────────────────────────────────────────────────────────────

def _type(x) -> str:
    return x.cls.name if isinstance(x, ClassObject) else type(x).__name__


def overload_binary(name: str, a, b):
    for x in (a, b):
        if isinstance(x, ClassObject):
            m = x.cls.find_method(name)
            if m is not None:
                return invoke(x.cls.rt, m, (a, b), 1)
    if name in ("eq", "ne") and isinstance(a, ClassObject) \
            and isinstance(b, ClassObject) and (a.cls.handle or a.enum):
        same = a is b or (a.enum is not None and a.cls is b.cls
                          and a.enum == b.enum)
        return same if name == "eq" else not same
    raise MatlabError(f"Binary operator '{_OPERATORS[name]}' is not "
                      f"supported for operands of type '{_type(a)}' and "
                      f"'{_type(b)}'.")


def overload_unary(name: str, a):
    m = a.cls.find_method(name)
    if m is None:
        raise MatlabError(f"Unary operator '{name}' is not supported for "
                          f"operands of type '{a.cls.name}'.")
    return invoke(a.cls.rt, m, (a,), 1)


def default_text(obj: ClassObject) -> str:
    cls = obj.cls
    if obj.enum is not None:
        return f"  {cls.name} enumeration\n\n    {obj.enum}\n"
    rt = cls.rt
    names = [p.name for p in cls.all_props()
             if p.get_access == "public" and not p.hidden]
    if not names:
        return f"  {cls.name} with no properties.\n"
    width = max(len(n) for n in names)
    lines = [f"  {cls.name} with properties:", ""]
    rt.class_ctx.append(cls)       # a display may read what a getter reads
    try:
        for n in names:
            lines.append(f"    {n:>{width}}: {_brief(get_property(obj, n))}")
    finally:
        rt.class_ctx.pop()
    return "\n".join(lines) + "\n"


def show_object(rt, name: str, obj: ClassObject) -> None:
    m = obj.cls.find_method("display")
    if m is not None:
        invoke(rt, m, (obj,), 0)
        return
    m = obj.cls.find_method("disp")
    if m is not None:
        print(f"{name} =\n")
        invoke(rt, m, (obj,), 0)
        print()
        return
    print(f"{name} =\n\n{default_text(obj)}")


def disp_object(rt, obj: ClassObject) -> None:
    print(default_text(obj))


def event_data(source, event: str) -> Struct:
    return Struct({"EventName": event, "Source": source})
