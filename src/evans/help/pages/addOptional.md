# addOptional

Add an optional argument to an inputParser.

## Syntax

    addOptional(p, name, default)
    addOptional(p, name, default, validator)

## Description

Declare an optional positional argument, with the value it takes when left out. It must be declared before the name-value ones. See [inputParser](inputParser) for the whole picture.

## Example

```matlab
p = inputParser;
addOptional(p, 'n', 10);
parse(p);
p.Results
```

## See also

[inputParser](inputParser) · [parse](parse)
