# regexpi

Match a regular expression, ignoring case.

## Syntax

    [startIndex, endIndex] = regexpi(str, expression)
    out = regexpi(str, expression, outkey, ...)

## Description

`regexpi` is [regexp](regexp) with letter case ignored. It takes the same keywords and options, and `'matchcase'` turns case back on.

## Example

```matlab
regexpi('Step, STEP, step', 'step', 'match')
```

## See also

[regexp](regexp) · [regexprep](regexprep)
