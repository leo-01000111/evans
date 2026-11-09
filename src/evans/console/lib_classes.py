"""
Working with classes: ``properties``, ``methods``, ``ismethod``, ``isprop``,
``isvalid``, ``isobject``, ``delete`` for handles, ``copy``, and the
``addlistener`` / ``notify`` pair.

A mixin of :class:`.matlab_runtime._Library`; the classes themselves are in
:mod:`.classes`. Import :mod:`.matlab_runtime` first, never this module on
its own.
"""

from __future__ import annotations

from . import classes as _cls  # noqa: F401
from . import matlab_runtime as _mr  # noqa: F401
from .classes import ClassDef, ClassObject, Listener
from .matlab_runtime import Cell, MatlabError, _as_text, _nargout, share


class ClassLibrary:
    """MATLAB's functions that ask about, or act on, objects."""

    def _class_of(self, x, who: str) -> ClassDef:
        if isinstance(x, ClassObject):
            return x.cls
        if isinstance(x, str):
            return self.rt.class_named(x)
        raise MatlabError(f"{who}: expected an object or a class name.")

    def _listing(self, title: str, names: list[str], nargout: int):
        if nargout >= 1:
            return Cell(names, rows=len(names) or 1)
        print(f"{title}\n")
        for n in names:
            print(f"    {n}")
        print()
        return None

    @_nargout
    def f_properties(self, x, nargout=1):
        cls = self._class_of(x, "properties")
        names = [p.name for p in cls.all_props()
                 if p.get_access == "public" and not p.hidden]
        return self._listing(f"Properties for class {cls.name}:", names,
                             nargout)

    @_nargout
    def f_methods(self, x, nargout=1):
        cls = self._class_of(x, "methods")
        names = cls.public_methods()
        return self._listing(f"Methods for class {cls.name}:", names,
                             nargout)

    def f_ismethod(self, x, name):
        if not isinstance(x, ClassObject):
            return False
        m = x.cls.find_method(_as_text(name))
        return m is not None and m.kind == "method" and not m.hidden \
            and m.access == "public"

    def f_isprop(self, x, name):
        if not isinstance(x, ClassObject):
            return False
        p = x.cls.find_prop(_as_text(name))
        return p is not None and not p.hidden

    def f_isobject(self, x):
        return isinstance(x, ClassObject)

    def f_isvalid(self, x):
        return bool(x.alive) if isinstance(x, ClassObject) else False

    def f_delete(self, *names):
        if names and isinstance(names[0], Listener):
            for lis in names:
                if lis in lis.source.listeners:
                    lis.source.listeners.remove(lis)
            return
        if names and isinstance(names[0], ClassObject):
            for obj in names:
                if not obj.cls.handle:
                    raise MatlabError("delete is only for handle objects.")
                if obj.alive:
                    m = obj.cls.find_method("delete")
                    if m is not None:
                        _cls.invoke(self.rt, m, (obj,), 0)
                    obj.alive = False
            return
        return super().f_delete(*names)

    def f_copy(self, x):
        if not isinstance(x, ClassObject) or not x.cls.copyable:
            raise MatlabError("copy needs an object of a class derived from "
                              "matlab.mixin.Copyable.")
        new = ClassObject(x.cls)
        new.props = {k: share(v) for k, v in x.props.items()}
        return new

    def f_addlistener(self, source, event, fn):
        if not isinstance(source, ClassObject) or not source.cls.handle:
            raise MatlabError("addlistener needs a handle object.")
        name = _as_text(event)
        if not any(name in c.events for c in source.cls.mro()):
            raise MatlabError(f"Class '{source.cls.name}' has no event "
                              f"'{name}'.")
        lis = Listener(source, name, fn)
        source.listeners.append(lis)
        return lis

    def f_notify(self, source, event, data=None):
        name = _as_text(event)
        if not isinstance(source, ClassObject):
            raise MatlabError("notify needs a handle object.")
        if not any(name in c.events for c in source.cls.mro()):
            raise MatlabError(f"Class '{source.cls.name}' has no event "
                              f"'{name}'.")
        info = data if data is not None else _cls.event_data(source, name)
        for lis in list(source.listeners):
            if lis.event == name and lis.enabled:
                self.rt.call(lis.fn, (source, info), nargout=0)
