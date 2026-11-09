# addlistener

Run a function when a handle object announces an event.

## Syntax

    lis = addlistener(obj, 'EventName', @callback)

## Description

The class declares the event in an `events` block, and `notify(obj, 'EventName')` calls every listener with the object and an event structure (`EventName` and `Source`). `delete(lis)` removes a listener.

## Example

The example writes a small class file, `Bell.m`, in the current folder.

```matlab
src = {'classdef Bell < handle', 'events', 'Rung', 'end', 'methods', 'function ring(b)', 'notify(b, ''Rung'');', 'end', 'end', 'end'};
fid = fopen('Bell.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
b = Bell();
lis = addlistener(b, 'Rung', @(s, e) disp(e.EventName));
b.ring()
```

## See also

[classdef](classdef) · [notify](notify) · [properties](properties) · [methods](methods)
