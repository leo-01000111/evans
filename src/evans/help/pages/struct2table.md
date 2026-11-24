# struct2table

Show a struct or struct array as a table, one row per struct element.

## Syntax

    T = struct2table(S)

## Description

`struct2table(S)` takes a scalar struct (one row) or a struct array (one row per element) and builds a table with one column per field. Printing it shows the columns side by side:

    s.a = 1; s.b = 'x';
    T = struct2table(s)

prints a header row `a b` and one row `1 'x'`. For a struct array such as `s(1).a = 1; s(2).a = 5` there is one row per element, in order, and text cells are shown in quotes. A field that is missing in some elements (`s(1).a = 1; s(2).b = 2`) shows as `[]` there, and the columns come in the order the fields first appear. A field value may be a vector (`[1 2 3]`), a cell (`{1×2 cell}`) or a struct (`[1×1 struct]`); it is shown as one cell. A matrix of structs is read down its columns, so a 2-by-2 struct array gives 4 rows. An empty struct array prints `0×0 empty table`.

Limits of Evans: the result is a display object, not a real table.

- `istable(T)` is 0 and `class(T)` is `'double'`.
- Columns cannot be read: `T.a` fails with `Unrecognized property or field "a"`, and `T.Properties.VariableNames` fails the same way. Brace indexing `T{2,'a'}` is refused.
- `table2struct`, `table2cell`, `table2array` and `summary` refuse it ("table2struct needs a table.").
- `T(1,:)` returns all the rows, not the first.
- `height(T)`, `width(T)` and `size(T)` do report rows and fields (2 rows and 1 field give `2 1`), and `numel(T)` is the number of rows.
- Name-value options such as `'AsArray'` or `'RowNames'` are not supported; they fail with a Python `TypeError` ("takes 2 positional arguments but 4 were given").
- A wrong argument gives a Python error rather than a MATLAB-style message: `struct2table(5)` fails with "'int' object is not iterable", `struct2table({1})` and `struct2table('abc')` with an `AttributeError`, and `struct2table()` with a missing-argument `TypeError`.

To get a real table to compute with, build it with [table](table), [cell2table](cell2table) or [array2table](array2table) instead.

## Example

```matlab
s = struct('name', {'Ann', 'Bob'}, 'n', {1, 2});
T = struct2table(s)
```

It prints two rows, one per struct, under the headings `name` and `n`.

## See also

[table](table) · [table2struct](table2struct) · [cell2table](cell2table) · [array2table](array2table)
