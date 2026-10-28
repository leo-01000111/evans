# regexp

Match a regular expression.

## Syntax

    [startIndex, endIndex] = regexp(str, expression)
    [startIndex, endIndex, tokenExtents, match, tokens, names, splitStr] = regexp(str, expression)
    out = regexp(str, expression, outkey)
    [out1, out2] = regexp(str, expression, outkey1, outkey2)
    out = regexp(..., 'once')
    out = regexp(..., option)

## Description

`regexp(str, expression)` finds the matches of the regular expression `expression` in `str`. With no keyword the outputs come in this order: start indices and end indices (row vectors, counting from 1), token extents, the matched text, the tokens, a struct of named tokens and the text between matches.

Keywords choose the outputs and their order: `'match'` (a cell of matched text), `'tokens'` (a cell holding a 1×k cell of the captured groups per match; with no groups, the whole match), `'names'` (a struct of the `(?<name>...)` groups, or a struct array for several matches), `'start'`, `'end'`, `'tokenExtents'` and `'split'`. With `'once'` only the first match is returned, not wrapped in a cell: `'match'` gives a character vector, `''` when nothing matches.

Other options: `'ignorecase'`, `'emptymatch'` (zero-length matches are skipped by default, as in MATLAB), `'dotexceptnewline'`, `'lineanchors'`, `'freespacing'` and `'forceCellOutput'`. On a cell array of text each output is a cell, the input's shape, of per-string results.

The syntax is MATLAB's: `(?<name>...)` named tokens, `\k<name>`, `\<` and `\>` for the start and end of a word, `^` and `$`, lookarounds. Evans does not support dynamic expressions `(??@...)` and `(?@...)`.

## Example

```matlab
[tok, mat] = regexp('Kp=2.5, Ki=0.8', '(\w+)=([\d.]+)', 'tokens', 'match');
mat
tok{2}
p = regexp('Kp=2.5', '(?<name>\w+)=(?<value>[\d.]+)', 'names')
```

## See also

[regexpi](regexpi) · [regexprep](regexprep) · [strsplit](strsplit) · [strfind](strfind) · [contains](contains)
