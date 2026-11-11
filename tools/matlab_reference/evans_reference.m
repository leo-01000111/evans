function evans_reference
% EVANS_REFERENCE  Record MATLAB's own answers for Evans to test against.
%
% HOW TO RUN (takes about a minute):
%   1. Put this file in any folder you can write to (Desktop is fine).
%   2. In MATLAB, go to that folder (Current Folder pane, or cd).
%   3. Type   evans_reference   and press Enter.
%   4. It writes  evans_reference.mat  in the same folder.
%      Email that .mat file back. That is all that is needed.
%
% What it does: runs a few hundred short MATLAB lines ("probes"), each in a
% clean workspace, and saves for each one the value it produced (or the
% error it raised), its class and size, plus the code itself. Evans later
% runs the same code and compares. Nothing is changed on this computer apart
% from writing the one .mat file. If a toolbox (Control System, Signal
% Processing, Optimization) is missing, its probes just record the error.

    here = fileparts(mfilename('fullpath'));
    target = fullfile(here, 'evans_reference.mat');

    P = probes();
    n = size(P, 1);
    ref = repmat(struct('id', 0, 'section', '', 'code', '', 'ok', false, ...
        'value', [], 'cls', '', 'sz', [], 'err_id', '', 'err_msg', '', ...
        'warn_id', ''), n, 1);

    fprintf('Evans reference: running %d probes...\n', n);
    for k = 1:n
        rec = run_probe(char(P{k, 2}));
        rec.id = k;
        rec.section = char(P{k, 1});
        rec.code = char(P{k, 2});
        ref(k) = orderfields(rec, ref(k));
        if mod(k, 50) == 0
            fprintf('  %d / %d\n', k, n);
        end
    end
    close all force

    v = ver;
    meta = struct( ...
        'matlab_version', version, ...
        'release', version('-release'), ...
        'computer', computer, ...
        'date', datestr(now, 'yyyy-mm-dd HH:MM:SS'), ...
        'toolboxes', {{v.Name}}, ...
        'n_probes', n);
    save(target, 'ref', 'meta', '-v7');

    ok = sum([ref.ok]);
    fprintf('\nDone: %d probes, %d gave a value, %d raised an error.\n', ...
        n, ok, n - ok);
    secs = unique({ref.section}, 'stable');
    for s = 1:numel(secs)
        in = strcmp({ref.section}, secs{s});
        fprintf('  %-12s %3d probes, %3d errors\n', secs{s}, sum(in), ...
            sum(in & ~[ref.ok]));
    end
    fprintf('\nSaved: %s\nPlease email that file back.\n', target);
end


function rec = run_probe(probe_code_)
% Runs one probe in this function's own (clean) workspace.
    rec = struct('id', 0, 'section', '', 'code', '', 'ok', false, ...
        'value', [], 'cls', '', 'sz', [], 'err_id', '', 'err_msg', '', ...
        'warn_id', '');
    lastwarn('', '');
    try
        evalc(probe_code_);
        if exist('out', 'var') ~= 1
            error('evans:noOut', 'The probe did not set out.');
        end
        rec.cls = class(out);
        rec.sz = size(out);
        rec.value = plain(out);
        rec.ok = true;
    catch err
        rec.err_id = err.identifier;
        rec.err_msg = err.message;
    end
    [~, rec.warn_id] = lastwarn;
    close all force
end


function v = plain(x)
% A value as plain data a .mat file can carry to Evans: numbers, logicals,
% chars, cells and structs. Objects become something readable.
    if isstring(x)
        v = cellstr(x);
    elseif istable(x) || isa(x, 'timetable')
        v = struct('VariableNames', {x.Properties.VariableNames}, ...
            'Data', {plain(table2cell(x))});
    elseif isdatetime(x)
        v = cellstr(string(x, 'yyyy-MM-dd HH:mm:ss.SSS'));
    elseif isduration(x)
        v = seconds(x);
    elseif isa(x, 'calendarDuration') || iscategorical(x)
        v = cellstr(string(x));
    elseif isa(x, 'containers.Map')
        v = struct('keys', {plain(keys(x))}, 'values', {plain(values(x))});
    elseif isa(x, 'function_handle')
        v = func2str(x);
    elseif iscell(x)
        v = cellfun(@plain, x, 'UniformOutput', false);
    elseif isstruct(x)
        v = x;
        f = fieldnames(x);
        for i = 1:numel(x)
            for j = 1:numel(f)
                v(i).(f{j}) = plain(x(i).(f{j}));
            end
        end
    elseif isobject(x)
        v = sprintf('<%s object>', class(x));
    else
        v = x;
    end
end


function P = probes()
% Each probe is one line of MATLAB that sets out. They are kept in the .mat
% file, so Evans replays exactly these lines.
    P = {};
    P = add(P, 'arith', [
        "out = round([-2.5 -1.5 -0.5 0.5 1.5 2.5]);"
        "out = fix([-2.7 2.7]);"
        "out = [floor(-2.5) ceil(-2.5) floor(2.5) ceil(2.5)];"
        "out = mod([-7 7 -7 7], [3 3 -3 -3]);"
        "out = rem([-7 7 -7 7], [3 3 -3 -3]);"
        "out = [mod(5.5, 2) mod(5, 0) rem(5, 0)];"
        "out = [0.1 + 0.2 == 0.3, abs(0.1 + 0.2 - 0.3) < eps];"
        "out = [1/0 -1/0];"
        "out = isnan([0/0 Inf-Inf Inf*0]);"
        "out = 2^-1;"
        "out = (-8)^(1/3);"
        "out = nthroot(-8, 3);"
        "out = sqrt(-4);"
        "out = [abs(3+4i) angle(-1)];"
        "out = log(-1);"
        "out = [1 2 3] .^ 2;"
        "out = [1 2; 3 4]^2;"
        "out = [1 2; 3 4]^-1;"
        "out = 3 \ 6;"
        "out = hypot(3, 4);"
        "out = exp(1);"
        "out = [factorial(5) nchoosek(5, 2) gcd(12, 18) lcm(4, 6)];"
        "out = primes(20);"
        "out = isprime(1:10);"
        "out = 5 + true;"
        "out = class(true + true);"
        "out = floor(log10(1000));"
        "out = 1e308 * 10;"
        "out = [realmax realmin eps(1) flintmax];"
        "out = eps(single(1));"
        "out = [sign(-3) sign(0) sign(2)];"
        "out = 10 / 3;"
        "out = -0;"
        "out = 1 / -0;"
    ]);
    P = add(P, 'integers', [
        "out = int8(127) + int8(1);"
        "out = int8(-128) - 1;"
        "out = uint8(3) - uint8(5);"
        "out = [int8(2.5) int8(-2.5) int8(3.5)];"
        "out = int16(100) * 2.6;"
        "out = int32(7) / int32(2);"
        "out = uint8(200) + 300;"
        "out = class(int8(1) * 2.5);"
        "out = idivide(int32(7), int32(2));"
        "out = idivide(int32(-7), int32(2));"
        "out = idivide(int32(7), int32(2), 'floor');"
        "out = intmax('int32');"
        "out = intmin('int8');"
        "out = bitand(12, 10);"
        "out = bitshift(1, 3);"
        "out = bitxor(uint8(5), uint8(3));"
        "out = sum(int8([100 100]));"
        "out = class(sum(int8([100 100])));"
        "out = mean(int8([100 100]));"
        "out = class(mean(int8([100 100])));"
        "out = int8([100 50]) * 2;"
        "out = double(int8(-5)) / 2;"
        "out = cast(300, 'uint8');"
        "out = class(uint8(250):uint8(255));"
        "out = uint8(250):uint8(255);"
        "out = single(1) / 3;"
        "out = class(single(1) + 1);"
        "out = class(single(1) + int8(1));"
        "out = int8(5) + int16(5);"
        "out = abs(int8(-128));"
        "out = -intmin('int16');"
        "out = typecast(single(1), 'uint32');"
        "out = int32(5) * 0.5;"
        "out = uint8(-3);"
    ]);
    P = add(P, 'arrays', [
        "out = size(1:0);"
        "out = size(zeros(0, 3));"
        "out = size([]);"
        "out = size('');"
        "out = size({});"
        "out = size(zeros(3, 0)');"
        "out = 10:-3:1;"
        "out = numel(0:0.1:1);"
        "out = 0:0.1:0.3;"
        "out = linspace(0, 1, 5);"
        "A = magic(4); out = A(end, end);"
        "A = magic(4); out = A(:, end);"
        "A = magic(4); out = A(end);"
        "A = magic(4); out = A(2:end-1, [1 end]);"
        "A = magic(4); out = A(5);"
        "A = magic(4); out = A(:)';"
        "x = 1:5; x(end+1) = 6; x(8) = 8; out = x;"
        "x = []; x(3) = 1; out = x;"
        "A = zeros(2); A(3, 3) = 1; out = A;"
        "x = 1:5; x([2 4]) = []; out = x;"
        "A = magic(3); A(2, :) = []; out = A;"
        "A = magic(3); A(:, 1) = []; out = A;"
        "x = 1:6; out = x(x > 3);"
        "x = 1:3; out = x(logical([1 0 1]));"
        "x = [5 0 7 0 9]; out = find(x);"
        "x = [5 0 7 0 9]; out = find(x, 2);"
        "[r, c] = find([0 1; 1 0]); out = [r c];"
        "A = magic(3); A(A > 5) = 0; out = A;"
        "out = isempty(zeros(0, 3));"
        "out = ndims(zeros(2, 3, 4));"
        "out = size(ones(2, 3), 3);"
        "out = size(zeros(2, 3, 4), 3);"
        "out = reshape(1:6, 2, []);"
        "out = reshape(1:6, [], 2)';"
        "out = size(cat(3, [1 2], [3 4]));"
        "X = permute(reshape(1:24, 2, 3, 4), [3 1 2]); out = {size(X), X(:, :, 1)};"
        "out = size(squeeze(ones(1, 1, 3)));"
        "out = sum(magic(3));"
        "out = sum(magic(3), 2);"
        "out = sum(ones(2, 3, 2), 3);"
        "out = sum([]);"
        "out = sum(zeros(0, 3));"
        "out = prod([]);"
        "out = max([]);"
        "out = mean([]);"
        "out = mean(zeros(0, 3));"
        "out = max([1 NaN 3]);"
        "out = min([NaN NaN]);"
        "[m, i] = max([3 7 7]); out = [m i];"
        "out = max(magic(3), [], 2);"
        "out = max(5, [1 7 3]);"
        "out = sort([3 1 NaN 2]);"
        "out = sort([3 1 NaN 2], 'descend');"
        "[s, i] = sort([2 1 2 1]); out = [s; i];"
        "out = sortrows([3 1; 1 2; 3 0]);"
        "out = unique([3 1 2 3 1]);"
        "[u, i, j] = unique([3 1 2 3 1]); out = {u, i', j'};"
        "out = cumsum(1:4);"
        "out = cumprod(1:4);"
        "out = diff([1 4 9 16]);"
        "out = diff([1 4 9 16], 2);"
        "out = [any([0 0]) all([]) any([])];"
        "out = repmat([1 2], 2, 2);"
        "out = kron([1 2], [1; 1]);"
        "out = rot90(magic(3));"
        "out = circshift(1:5, 2);"
        "out = circshift(magic(3), 1, 2);"
        "out = triu(magic(3), 1);"
        "out = diag([1 2 3]);"
        "out = diag(magic(3), 1);"
        "out = eye(2, 3);"
        "out = class(ones(2, 'int8'));"
        "out = class(zeros(2, 'like', int8(1)));"
        "out = true(2);"
        "out = false(1, 3);"
        "out = [isequal([1 2], [1 2]) isequal('a', 97)];"
        "out = num2cell([1 2]);"
        "out = cell2mat({[1 2], 3; [4 5], 6});"
        "x = 1:3; out = size(x([]));"
        "x = 1:5; out = x(end-1:end);"
        "A = reshape(1:24, 2, 3, 4); out = A(2, 3, 4);"
        "A = reshape(1:24, 2, 3, 4); out = A(:, :, 2);"
        "out = sum(ones(2, 3, 4), [1 2]);"
        "out = zeros(3, 0) * zeros(0, 2);"
        "out = [1; 2] + [10 20];"
        "out = numel(ones(3, 4, 2));"
        "out = fliplr(1:3);"
        "out = horzcat([1 2], [], 3);"
        "a = 1:3; a(5) = 9; out = a;"
        "s = 'abc'; s(5) = 'e'; out = double(s);"
    ]);
    P = add(P, 'logic', [
        "out = [1 2 3] == [1 5 3];"
        "out = 'abc' == 'abd';"
        "out = xor(true, false);"
        "out = ~[1 0 2];"
        "out = class(1 < 2);"
        "out = [isreal(complex(1, 0)) isreal(1 + 0i)];"
        "out = isnan([1 NaN]) | isinf([Inf 1]);"
        "out = class(true & 1);"
        "out = logical([2 0 -1]);"
        "out = [isa(1, 'numeric') isa(int8(1), 'integer') isa(single(1), 'float')];"
        "out = exist('notAThingAtAll_xyz');"
        "out = isscalar([]) + isvector(1:3) + ismatrix(ones(2,2,2));"
    ]);
    P = add(P, 'text', [
        "out = 'abc' + 1;"
        "out = char([72 105]);"
        "out = double('A');"
        "out = strcat('a ', 'b');"
        "out = strcat({'a '}, 'b');"
        "out = ['ab'; 'cd'];"
        "out = num2str(pi);"
        "out = num2str(pi, 8);"
        "out = num2str([1 2 3]);"
        "out = num2str(1e10);"
        "out = num2str(-0.5);"
        "out = num2str(int8(5));"
        "out = num2str(123456789);"
        "out = num2str(0.1 + 0.2);"
        "out = num2str([1.5 2.25; 3 4]);"
        "out = mat2str([1 2; 3 4]);"
        "out = mat2str([0.1 1/3]);"
        "out = mat2str(logical([1 0]));"
        "out = int2str([2.5 -2.5]);"
        "out = sprintf('%d', 3.5);"
        "out = sprintf('%d', 3);"
        "out = sprintf('%5.2f|', [1 2.345]);"
        "out = sprintf('%s-%d', 'ab', 3);"
        "out = sprintf('%x', 255);"
        "out = sprintf('%g', 1e-5);"
        "out = sprintf('%g', 100000);"
        "out = sprintf('%g', 1000000);"
        "out = sprintf('%.3g', 0.0001234);"
        "out = sprintf('%e', 12345.678);"
        "out = sprintf('%c', 72, 105);"
        "out = sprintf('%d%%', 50);"
        "out = sprintf('%+d', 5);"
        "out = sprintf('%05.1f', 3.14159);"
        "out = sprintf('[%s]', '');"
        "out = sprintf('%d,', [1 2; 3 4]);"
        "out = sprintf('%s', 65);"
        "out = sprintf('%d', int8(-3));"
        "out = sprintf('%.2f', -0.001);"
        "out = sprintf('%10s|', 'hi');"
        "out = sprintf('%-6d|', 42);"
        "out = sprintf('%i %u', 7, 8);"
        "out = sprintf('%s', 'tab\there');"
        "out = sprintf('a\nb');"
        "out = strsplit('a,b,,c', ',');"
        "out = strsplit('a  b');"
        "out = strjoin({'a', 'b', 'c'}, '-');"
        "out = strtrim(sprintf('  a \t'));"
        "out = strrep('aaa', 'aa', 'b');"
        "out = regexprep('abc123', '\d', '#');"
        "out = regexp('a1b22', '\d+', 'match');"
        "out = regexp('key=val', '(\w+)=(\w+)', 'tokens');"
        "out = regexp('abc', 'b');"
        "out = regexpi('ABC', 'b', 'match');"
        "[tok, rest] = strtok('hello world'); out = {tok, rest};"
        "out = [strcmp('a', 'a') strcmpi('A', 'a') strncmp('abc', 'abd', 2)];"
        "out = strcmp({'a', 'b'}, 'a');"
        "out = upper('abc');"
        "out = lower(['A'; 'B']);"
        "out = fliplr('abc');"
        "out = size(blanks(3));"
        "out = deblank('a  ');"
        "out = str2num('[1 2 3]');"
        "out = str2double('3.14');"
        "out = str2double('abc');"
        "out = str2double({'1', 'x'});"
        "out = contains('hello', 'ell');"
        "out = startsWith('hello', 'he');"
        "out = upper({'ab', 'c'});"
        "out = strfind('abcabc', 'bc');"
        "out = num2str(true);"
        "out = dec2bin(10);"
        "out = dec2hex(255);"
        "out = hex2dec('FF');"
        "out = isspace('a b');"
        "out = length('hello');"
    ]);
    P = add(P, 'strings', [
        "out = numel(""hello"");"
        "out = strlength(""hello"");"
        "out = ""a"" + ""b"";"
        "out = size([""a"" ""bc""]);"
        "out = string(5);"
        "out = string(1/3);"
        "out = double(""3.5"");"
        "out = ""abc"" == ""abc"";"
        "out = class(""x"");"
        "out = upper(""abc"");"
        "out = strsplit(""a b c"");"
        "out = join([""a"" ""b""], ""-"");"
        "out = strrep(""hello"", ""l"", ""L"");"
        "out = [""x"" ""y""] + 1;"
        "out = string({'a', 'b'});"
        "out = char(""hi"");"
        "out = ""ab"" < ""b"";"
        "out = contains([""apple"" ""pear""], ""ea"");"
        "out = sprintf(""%d"", 4);"
        "out = class(sprintf(""%d"", 4));"
    ]);
    P = add(P, 'cells', [
        "c = {1, 'a'; 2, 'b'}; out = size(c);"
        "c = {1, 'a'; 2, 'b'}; out = c{2, 1};"
        "c = {1, 'a'; 2, 'b'}; out = c(2, :);"
        "c = {1, 2}; out = class(c(1));"
        "c = {}; c{3} = 1; out = size(c);"
        "s = struct('a', {1, 2}); out = size(s);"
        "s = struct('a', {1, 2}); out = [s.a];"
        "s = struct('a', {{1, 2}}); out = size(s);"
        "s.b.c = 5; out = s.b.c;"
        "out = fieldnames(struct('b', 1, 'a', 2));"
        "s = struct('a', 1); out = isfield(s, {'a', 'z'});"
        "s = struct('a', 1, 'b', 2); out = fieldnames(rmfield(s, 'a'));"
        "out = fieldnames(orderfields(struct('b', 1, 'a', 2)));"
        "out = cellfun(@numel, {'ab', 'c'});"
        "out = cellfun(@(x) x * 2, {1, 2}, 'UniformOutput', false);"
        "out = cellfun('isempty', {[], 1});"
        "out = arrayfun(@(x) x^2, 1:3);"
        "out = struct2cell(struct('a', 1, 'b', 'x'));"
        "out = cell2struct({1; 2}, {'p'; 'q'}, 1);"
        "s = struct(); s(2).x = 1; out = {size(s), isempty(s(1).x)};"
        "[x, y] = deal(1, 2); out = [x y];"
        "c = {1, 2, 3}; out = [c{:}];"
        "c = {'a', 'b'}; out = sprintf('%s,', c{:});"
        "c = {}; out = isempty(c);"
        "out = iscellstr({'a', 'b'});"
        "out = ismember('b', {'a', 'b'});"
        "[tf, loc] = ismember([1 5 2], [2 1]); out = [tf; loc];"
        "out = setdiff([5 1 3], [1]);"
        "out = intersect([1 2 3], [2 3 4]);"
        "out = union([3 1], [2 1]);"
        "c = num2cell(1:3); out = c';"
        "m = {1, 'x'; [1 2], {2}}; out = cellfun(@class, m, 'UniformOutput', false);"
    ]);
    P = add(P, 'semantics', [
        "a = [1 2 3]; b = a; b(1) = 9; out = a;"
        "a = [1 2 3]; c = {a}; a(2) = 0; out = c{1};"
        "a = [1 2 3]; s.f = a; a(3) = 0; out = s.f;"
        "c = {1, 2}; d = c; d{1} = 9; out = c{1};"
        "s.a = 1; t = s; t.a = 2; out = s.a;"
        "a = 1:3; f = @() a; a(1) = 9; out = f();"
        "out = 0; for k = [], out = 1; end"
        "out = []; for c = [1 2; 3 4], out(end+1) = sum(c); end"
        "out = 0; k = 0; while true, k = k + 1; if k > 3, break; end, out = out + k; end"
        "x = 'b'; switch x, case {'a', 'b'}, out = 1; otherwise, out = 2; end"
        "x = 3; switch x, case 1, out = 'one'; case {2, 3}, out = 'two-three'; end"
        "try, error('my:id', 'boom %d', 3); catch e, out = {e.identifier, e.message}; end"
        "f = @(x) x.^2 + 1; out = f(2);"
        "g = @plus; out = g(1, 2);"
        "out = func2str(@(x) x + 1);"
        "out = nargin(@(a, b) a);"
        "out = feval(@max, [1 5 2]);"
        "eval('x = 3;'); out = x;"
        "out = eval('1 + 1');"
        "for k = 1:3, end, out = k;"
        "for k = 1:0, end, out = exist('k', 'var');"
        "x = 5; x(2) = 7; out = x;"
        "out = isempty(''); "
        "if [], out = 1; else, out = 2; end"
        "if [1 1 0], out = 1; else, out = 2; end"
        "s = 0; for i = 1:10, if mod(i, 2), continue, end, s = s + i; end, out = s;"
    ]);
    P = add(P, 'errors', [
        "out = [1 2] + [1 2 3];"
        "x = [1 2 3]; out = x(4);"
        "x = [1 2 3]; out = x(0);"
        "x = [1 2 3]; out = x(1.5);"
        "out = ones(2) * ones(3);"
        "out = undefinedFunctionXyz(1);"
        "c = {1}; out = c{2};"
        "s.a = 1; out = s.b;"
        "out = [1 2; 3];"
        "out = zeros(2, 'logical');"
        "out = str2func(42);"
        "out = cell2mat({1, 'a'});"
        "error('Simple message'); out = 1;"
        "x = 1:3; x(5) = []; out = x;"
        "out = strcat(1, 2);"
        "out = {1} + 1;"
    ]);
    P = add(P, 'numerics', [
        "out = det(magic(3));"
        "out = rank(magic(4));"
        "out = inv([2 1; 1 3]);"
        "out = [1 2; 3 4] \ [5; 6];"
        "out = [norm([3 4]) norm(magic(3)) norm(magic(3), 1) norm(magic(3), 'fro')];"
        "out = trace(magic(3));"
        "out = sort(eig([2 1; 1 2]));"
        "out = sort(abs(eig(magic(4))));"
        "out = svd(magic(3));"
        "out = cond([1 2; 3 4]);"
        "out = pinv([1 2; 2 4]);"
        "out = abs(null([1 1]));"
        "out = expm([0 1; 0 0]);"
        "out = sqrtm([4 0; 0 9]);"
        "out = logm(eye(2));"
        "out = chol([4 2; 2 3]);"
        "[L, U, Pm] = lu([1 2; 3 4]); out = {L, U, Pm};"
        "out = polyfit(1:4, [2 4 6 8], 1);"
        "out = polyfit(0:3, [1 2 5 10], 2);"
        "out = polyval([1 2 3], 2);"
        "out = sort(roots([1 -3 2]));"
        "out = conv([1 1], [1 -1]);"
        "[q, r] = deconv([1 0 -1], [1 1]); out = {q, r};"
        "out = poly([1 2]);"
        "out = polyder([1 2 3]);"
        "out = polyint([3 2 1]);"
        "out = interp1([1 2 3], [10 20 30], 2.5);"
        "out = interp1([1 2 3], [10 20 30], 2.5, 'nearest');"
        "out = interp1([1 2 3], [10 20 30], 4);"
        "out = interp1([1 2 3], [10 20 30], 4, 'linear', 'extrap');"
        "out = spline([0 1 2], [0 1 4], 1.5);"
        "out = pchip([0 1 2], [0 1 4], 1.5);"
        "out = interp2([1 2; 3 4], 1.5, 1.5);"
        "out = [trapz([1 2 3]) trapz([0 1 2], [0 1 4])];"
        "out = cumtrapz([1 2 3]);"
        "out = integral(@(x) x.^2, 0, 1);"
        "out = fzero(@(x) x^2 - 2, [1 2]);"
        "out = fminsearch(@(x) (x - 3).^2, 0);"
        "[t, y] = ode45(@(t, y) -y, [0 1], 1); out = y(end);"
        "out = [median([3 1 4 1 5]) mode([1 2 2 3 3])];"
        "out = [var([1 2 3 4]) std([1 2 3 4]) var([1 2 3 4], 1)];"
        "out = cov([1 2 3], [1 2 4]);"
        "out = corrcoef([1 2 3], [2 4 7]);"
        "out = mean([1 2; 3 4]);"
        "out = mean([1 2; 3 4], 'all');"
        "out = median([1 NaN 3]);"
        "out = abs(fft([1 0 0 0]));"
        "out = abs(fft([1 2 3 4]));"
        "out = real(ifft(fft([1 2 3])));"
        "out = filter(1, [1 -0.5], [1 0 0]);"
        "[X, Y] = meshgrid(1:2, 1:3); out = {X, Y};"
        "out = cross([1 0 0], [0 1 0]);"
        "out = dot([1 2 3], [4 5 6]);"
        "out = full(sparse([1 2], [1 2], [3 4]));"
        "out = nnz(sparse([1 0; 0 2]));"
        "out = histcounts([1 2 2 3], 3);"
        "out = round(pi, 2);"
        "out = round(1234, -2);"
        "out = floor([-0.5 0.5]);"
        "out = normest(magic(3)) > 0;"
        "out = sum(1:100);"
        "out = mean([true false true]);"
        "out = max([1+1i, 2]);"
        "out = sort([1+1i, -2, 0.5i]);"
        "out = abs(-int8(5));"
        "out = prod(int16([200 200]));"
        "out = cumsum([1 NaN 2]);"
        "out = movmean(1:5, 3);"
        "out = detrend([1 2 4]);"
        "out = smoothdata([1 5 1 5 1], 'movmean', 3);"
    ]);
    P = add(P, 'control', [
        "G = tf(1, [1 2 1]); [n, d] = tfdata(G, 'v'); out = {n, d};"
        "out = dcgain(tf(2, [1 3]));"
        "out = sort(pole(tf(1, [1 3 2])));"
        "out = zero(tf([1 2], [1 3 2]));"
        "H = feedback(tf(1, [1 1]), 1); [n, d] = tfdata(H, 'v'); out = {n, d};"
        "H = feedback(tf(2, [1 1]), tf(1, [1 5])); [n, d] = tfdata(H, 'v'); out = {n, d};"
        "H = tf(1, [1 1]) * tf(1, [1 2]); [n, d] = tfdata(H, 'v'); out = {n, d};"
        "H = tf(1, [1 1]) + tf(1, [1 2]); [n, d] = tfdata(H, 'v'); out = {n, d};"
        "[Gm, Pm, Wcg, Wcp] = margin(tf(1, [1 3 3 1])); out = [Gm Pm Wcg Wcp];"
        "[Gm, Pm, Wcg, Wcp] = margin(tf(10, [1 3 3 1])); out = [Gm Pm Wcg Wcp];"
        "[mag, ph] = bode(tf(1, [1 1]), [0.1 1 10]); out = {squeeze(mag)', squeeze(ph)'};"
        "[mag, ph] = bode(tf(1, [1 0 0]), [1 10]); out = {squeeze(mag)', squeeze(ph)'};"
        "S = stepinfo(tf(4, [1 2 4])); out = [S.RiseTime S.SettlingTime S.Overshoot S.Peak S.PeakTime];"
        "y = step(tf(1, [1 1]), 0:0.5:2); out = y';"
        "y = impulse(tf(1, [1 1]), 0:0.5:2); out = y';"
        "Gd = c2d(tf(1, [1 1]), 0.1); [n, d] = tfdata(Gd, 'v'); out = {n, d};"
        "Gd = c2d(tf(1, [1 1]), 0.1, 'tustin'); [n, d] = tfdata(Gd, 'v'); out = {n, d};"
        "Gc = d2c(tf(0.1, [1 -0.9], 0.1)); [n, d] = tfdata(Gc, 'v'); out = {n, d};"
        "[n, d] = ss2tf([0 1; -2 -3], [0; 1], [1 0], 0); out = {n, d};"
        "[A, B, C, D] = tf2ss(1, [1 3 2]); out = {A, B, C, D};"
        "out = lqr([0 1; 0 0], [0; 1], eye(2), 1);"
        "out = place([0 1; 0 0], [0; 1], [-1 -2]);"
        "out = [rank(ctrb([0 1; 0 0], [0; 1])) rank(obsv([0 1; 0 0], [1 0]))];"
        "[wn, z] = damp(tf(4, [1 2 4])); out = [wn z];"
        "out = evalfr(tf(1, [1 1]), 1i);"
        "out = squeeze(freqresp(tf(1, [1 1]), [0 1]))';"
        "G = minreal(tf([1 1], [1 2 1])); [n, d] = tfdata(G, 'v'); out = {n, d};"
        "out = [isstable(tf(1, [1 -1])) isstable(tf(1, [1 1]))];"
        "sys = ss([0 1; -2 -3], [0; 1], [1 0], 0); out = dcgain(sys);"
        "sys = ss(tf(1, [1 3 2])); out = sort(eig(sys.A));"
        "G = tf([1 2], [1 3 2]); out = sort(pole(G));"
        "y = step(tf(1, [1 -0.5], 1), 0:4); out = y';"
        "s = tf('s'); G = (s + 1) / (s^2 + 2*s + 5); [n, d] = tfdata(G, 'v'); out = {n, d};"
        "G = zpk([-1], [-2 -3], 4); [n, d] = tfdata(tf(G), 'v'); out = {n, d};"
        "out = bandwidth(tf(1, [1 1]));"
        "G = tf(1, [1 1], 'InputDelay', 0.5); out = G.InputDelay;"
        "[r, k] = rlocus(tf(1, [1 3 2]), [0 1 4]); out = {sort(r(:, 1)), sort(r(:, 3))};"
        "K = acker([0 1; 0 0], [0; 1], [-1 -2]); out = K;"
        "out = covar(ss(-1, 1, 1, 0), 1);"
        "out = norm(tf(1, [1 1]), 2);"
        "out = norm(tf(1, [1 1]), Inf);"
        "allm = allmargin(tf(1, [1 3 3 1])); out = allm.GainMargin;"
        "y = lsim(tf(1, [1 1]), ones(1, 5), 0:4); out = y';"
        "G = pade(tf(1, 1, 'OutputDelay', 1), 1); [n, d] = tfdata(G, 'v'); out = {n, d};"
    ]);
    P = add(P, 'signal', [
        "[b, a] = butter(2, 0.5); out = {b, a};"
        "[b, a] = butter(3, 0.2, 'high'); out = {b, a};"
        "[b, a] = cheby1(2, 1, 0.3); out = {b, a};"
        "out = hann(4)';"
        "out = hamming(5)';"
        "out = fir1(4, 0.5);"
        "[b, a] = butter(2, 0.3); out = filtfilt(b, a, [1 2 3 4 5 6]);"
        "[h, w] = freqz([1 1], 1, 4); out = {abs(h)', w'};"
        "[pks, locs] = findpeaks([1 3 2 5 4]); out = {pks, locs};"
        "out = xcorr([1 2 3]);"
        "out = resample([1 2 3 4], 2, 1);"
        "[pxx, f] = periodogram([1 2 3 4]); out = {pxx', f'};"
        "out = blackman(4)';"
        "out = kaiser(4, 2)';"
        "out = grpdelay([1 1], 1, 4)';"
        "out = impz([1], [1 -0.5], 4)';"
        "out = decimate(1:20, 2);"
    ]);
    P = add(P, 'optim', [
        "opts = optimoptions('fmincon', 'Display', 'off'); out = fmincon(@(x) sum((x - [1 2]).^2), [0 0], [1 1], 2, [], [], [], [], [], opts);"
        "opts = optimoptions('linprog', 'Display', 'off'); out = linprog([-1 -1], [1 2; 3 1], [4; 6], [], [], [0 0], [], opts)';"
        "opts = optimoptions('lsqcurvefit', 'Display', 'off'); out = lsqcurvefit(@(p, x) p(1) * exp(p(2) * x), [1 1], 0:3, 2 * exp(0.5 * (0:3)), [], [], opts);"
        "opts = optimoptions('fsolve', 'Display', 'off'); out = fsolve(@(x) x^2 - 4, 1, opts);"
        "opts = optimoptions('fminunc', 'Display', 'off'); out = fminunc(@(x) (x - 2)^2 + 1, 0, opts);"
        "opts = optimoptions('quadprog', 'Display', 'off'); out = quadprog(eye(2), [-1; -1], [], [], [], [], [], [], [], opts)';"
        "opts = optimoptions('intlinprog', 'Display', 'off'); out = intlinprog([-1; -1], [1 2], [1 1; 1 -1], [3.5; 1], [], [], [0; 0], [], opts)';"
    ]);
    P = add(P, 'data', [
        "T = table([1; 2], {'a'; 'b'}, 'VariableNames', {'x', 'y'}); out = T.x';"
        "T = table([1; 2], {'a'; 'b'}, 'VariableNames', {'x', 'y'}); out = height(T);"
        "T = table([1; 2], [3; 4]); out = T.Properties.VariableNames;"
        "T = sortrows(table([3; 1; 2], 'VariableNames', {'v'}), 'v'); out = T.v';"
        "T = table([1; 2; 3], [4; 5; 6], 'VariableNames', {'a', 'b'}); out = T(T.a > 1, :).b';"
        "T = table([1; 1; 2], [10; 20; 30], 'VariableNames', {'g', 'v'}); G = groupsummary(T, 'g', 'mean', 'v'); out = G.mean_v';"
        "m = containers.Map({'a', 'b'}, {1, 2}); out = {keys(m), values(m), m('b'), m.Count};"
        "m = containers.Map('KeyType', 'double', 'ValueType', 'any'); m(3) = 1; m(1) = 2; out = keys(m);"
        "out = datenum(2026, 11, 11);"
        "out = datestr(datenum(2026, 11, 11, 13, 5, 0), 'yyyy-mm-dd HH:MM:SS');"
        "out = datetime(2024, 1, 31) + calmonths(1);"
        "out = days(datetime(2024, 3, 1) - datetime(2024, 2, 1));"
        "out = weekday(datenum(2026, 11, 11));"
        "out = seconds(minutes(2));"
        "out = year(datetime(2026, 11, 11) + caldays(60));"
        "out = jsonencode(struct('a', 1, 'b', [1 2 3], 'c', 'x'));"
        "out = jsondecode('{""a"": [1, 2], ""b"": {""c"": true}}');"
        "out = jsondecode('[{""x"": 1}, {""x"": 2}]');"
        "out = categorical({'b', 'a', 'b'});"
    ]);
end


function P = add(P, section, codes)
    for k = 1:numel(codes)
        P(end + 1, :) = {section, codes(k)}; %#ok<AGROW>
    end
end

