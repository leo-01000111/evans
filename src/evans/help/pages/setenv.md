# setenv

Set an environment variable.

## Syntax

    setenv(name, value)
    setenv(name)

## Description

Sets `name` to `value` for Evans and the commands it starts with [system](system). With no value (or `''`) the variable is removed.

## Example

```matlab
setenv('EVANS_DEMO', '42');
getenv('EVANS_DEMO')
setenv('EVANS_DEMO');
```

## See also

[getenv](getenv) · [system](system)
