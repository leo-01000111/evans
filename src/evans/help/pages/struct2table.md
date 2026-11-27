# struct2table

Convert a struct or struct array to a table.

## Syntax

    T = struct2table(S)
    T = struct2table(S, 'AsArray', true)
    T = struct2table(S, 'RowNames', names)

## Description

`struct2table(S)` returns a table with one variable per field of `S`, in the order the fields first appear. The result is a real table: `istable(T)` is 1, `class(T)` is `'table'`, and `T.a`, `T.Properties`, `T(1,:)`, `T{2,'a'}`, `table2struct`, `table2cell`, `table2array` and `summary` all work on it.

- For a struct array (a row or a column of structs), there is one row per element, in order. `struct2table(struct('a', {1, 2}))` is a 2-by-1 table whose `T.a` is the column `[1; 2]`.
- For a scalar struct, every field must have the same number of rows `m`, and the table has `m` rows: `s.x = [1; 2; 3]; s.y = [4; 5; 6]` gives a 3-by-2 table. Fields with different numbers of rows give the error "the fields of a scalar struct must all have the same number of rows".

In each variable, numbers and logicals that are one per row become a numeric (or logical) column. Text fields become a cell array of char vectors, so `T.name` is `{'Ann'; 'Bob'}`. Values of different sizes, structs and cells become a cell column, one value per row: `struct('v', {[1 2], 7})` gives `T.v = {[1 2]; 7}`.

Options:

- `'AsArray', true`: treat a scalar struct as a one-row table. Each field becomes one row, and a field with more than one row goes into a cell, so `s.x = [1; 2; 3]; s.y = 7` gives a 1-by-2 table with `T.x = {[1; 2; 3]}` and `T.y = 7`. For a struct array this option changes nothing.
- `'RowNames', names`: a cell array of distinct names, one per row, so rows can be indexed by name, as in `T('r2', :)`.

Limits of Evans: a table variable holds one column per row, so a field that would make a variable with several columns is refused with an error instead. That happens when every element holds a row vector of the same length (MATLAB would make an n-by-k variable), or when a scalar struct's field is a row vector or matrix. Make such a field a column, or put each value in a cell. A matrix of structs (2-by-2, say) is refused; pass `S(:)` for one row per element. A struct field becomes a cell holding the struct, not a nested struct array.

An input that is not a struct gives the error "struct2table: the input must be a struct or a struct array."

## Example

```matlab
s = struct('name', {'Ann', 'Bob'}, 'n', {1, 2});
T = struct2table(s)
T.n'
```

`T` is a 2-by-2 table with the variables `name` and `n`; `T.n'` is `[1 2]`.

## See also

[table](table) · [table2struct](table2struct) · [cell2table](cell2table) · [array2table](array2table)
