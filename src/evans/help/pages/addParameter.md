# addParameter

Add a name-value argument to an inputParser.

## Syntax

    addParameter(p, name, default)
    addParameter(p, name, default, validator)

## Description

Declare a name-value argument. `addParamValue` is the old name for it; `p.addSwitch(name)` declares one that takes no value. See [inputParser](inputParser) for the whole picture.

## Example

```matlab
p = inputParser;
addParameter(p, 'tol', 1e-3);
parse(p, 'tol', 5);
p.Results
```

## See also

[inputParser](inputParser) · [parse](parse)
