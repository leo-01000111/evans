# parse

Run an inputParser on a list of arguments.

## Syntax

    parse(p, args...)
    p.parse(args...)

## Description

Checks the arguments against what was declared and fills `p.Results`, `p.Unmatched` and `p.UsingDefaults`. A failed check stops with an error that names the argument.

## Example

```matlab
p = inputParser;
addParameter(p, 'gain', 1, @(x) x > 0);
parse(p, 'gain', 3);
p.Results.gain
```

## See also

[inputParser](inputParser) · [addParameter](addParameter)
