# isletter

True for letters.

## Syntax

    tf = isletter(str)

## Description

`isletter(str)` returns a logical array the size of `str`, true where the character is a letter (accented and other alphabets included). For anything that is not text the result is all false.

## Example

```matlab
isletter('x1 = 2y')
```

## See also

[isspace](isspace) · [isstrprop](isstrprop)
