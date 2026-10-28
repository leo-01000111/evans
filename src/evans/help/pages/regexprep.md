# regexprep

Replace text that matches a regular expression.

## Syntax

    newStr = regexprep(str, expression, replace)
    newStr = regexprep(..., option)

## Description

`regexprep(str, expression, replace)` replaces every match of `expression` in `str` with `replace`. In `replace`, `$0` is the whole match, `$1` to `$9` the tokens and `$<name>` a named token; `\n`, `\t` and `\$` are newline, tab and a dollar sign. If `expression` and `replace` are cell arrays, each pair is applied in turn (one `replace` is used for every expression). On a cell array of text each element is replaced and the shape kept.

Options: `'once'` replaces only the first match, a number `N` only the Nth, and `'ignorecase'`, `'emptymatch'`, `'dotexceptnewline'`, `'lineanchors'` and `'freespacing'` work as in [regexp](regexp). Evans does not support `'preservecase'` or `${...}` dynamic replacements; both are errors.

## Example

```matlab
s = regexprep('x1 + x22', 'x(\d+)', 'x[$1]')
```

## See also

[regexp](regexp) · [strrep](strrep)
