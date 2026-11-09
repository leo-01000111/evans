# isobject

Whether a value is an object of a user class.

## Syntax

    tf = isobject(x)

## Description

True for an object made from a `classdef` file. Numbers, text, structs and cells give false.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
isobject(p)
isobject(5)
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
