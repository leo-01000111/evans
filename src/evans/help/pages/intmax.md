# intmax

Largest value of an integer class.

## Syntax

    v = intmax
    v = intmax(classname)
    v = intmax(A)

## Description

`intmax('int8')` is 127. With no argument the class is `int32`. Given an integer array, it uses that array's class. The result has the integer class, so `intmax('int8') + 1` saturates at 127.

## Example

```matlab
intmax('uint8')
intmax('int16') + 1
class(intmax)
```

## See also

[intmin](intmin) · [flintmax](flintmax) · [realmax](realmax)
