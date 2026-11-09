# fileread

The text of a file.

## Syntax

    text = fileread(filename)

## Description

Reads the whole file as a character vector. UTF-8 is tried first, then Windows-1252. The name is relative to the current folder.

## Example

```matlab
writematrix([1 2 3], 'fileread_demo.csv');
txt = fileread('fileread_demo.csv')
delete('fileread_demo.csv');
```

## See also

[fopen](fopen) · [readmatrix](readmatrix) · [jsondecode](jsondecode) · [textscan](textscan)
