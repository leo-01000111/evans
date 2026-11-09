# copy

A copy of a handle object.

## Syntax

    new = copy(obj)

## Description

Only for classes derived from `matlab.mixin.Copyable`. The copy is a new handle with the same property values; a handle held inside a property is shared, not copied.

## Example

The example writes a small class file in the current folder.

```matlab
src = {'classdef Cp < matlab.mixin.Copyable', 'properties', 'v = 1;', 'end', 'end'};
fid = fopen('Cp.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
a = Cp();
b = copy(a);
b.v = 5;
a.v
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify)
