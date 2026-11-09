# notify

Announce an event from a handle object.

## Syntax

    notify(obj, 'EventName')
    notify(obj, 'EventName', data)

## Description

Calls each listener added with `addlistener` for that event, passing the object and `data`, or a structure with `EventName` and `Source` when `data` is left out.

## Example

The example writes a small class file in the current folder.

```matlab
src = {'classdef Bell < handle', 'events', 'Rung', 'end', 'end'};
fid = fopen('Bell.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
b = Bell();
addlistener(b, 'Rung', @(s, e) disp('rung'));
notify(b, 'Rung')
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [copy](copy)
