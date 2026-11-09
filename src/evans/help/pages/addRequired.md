# addRequired

Add a required argument to an inputParser.

## Syntax

    addRequired(p, name)
    addRequired(p, name, validator)

## Description

Declare a required argument of an inputParser. Required arguments must be declared before optional and name-value ones; `parse` fails with `Not enough input arguments.` if one is missing. See [inputParser](inputParser) for the whole picture.

## Example

```matlab
p = inputParser;
addRequired(p, 'x', @isnumeric);
parse(p, 4);
p.Results
```

## See also

[inputParser](inputParser) · [parse](parse)
