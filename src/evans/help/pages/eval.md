# eval

Run MATLAB text as code.

## Syntax

    eval(expression)
    eval(tryExpression, catchExpression)
    y = eval(expression)

## Description

`eval` translates the text and runs it in the current workspace, echoing as typed. With two inputs, the second runs if the first raises an error. `y = eval(expression)` returns the value of a single expression.

Inside a function, `eval` can read the function's variables but cannot create or change them: Evans stops with an error rather than lose the assignment silently. Return the value with `y = eval(...)` instead.

## Example

```matlab
eval('q = 7')
z = eval('3*3')
eval('1 +* 2', 'w = 5;')
w
```

## See also

[evalin](evalin) · [feval](feval) · [str2func](str2func)
