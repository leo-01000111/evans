# getenv

The value of an environment variable.

## Syntax

    value = getenv(name)

## Description

The variable's value as text, or `''` if it is not set.

## Example

```matlab
setenv('EVANS_DEMO', 'on');
getenv('EVANS_DEMO')
```

## See also

[setenv](setenv) · [system](system)
