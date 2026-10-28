# Evans help

Reference pages for the functions you can call at the Evans console and in MATLAB scripts, grouped by what they do.

## Using this window

Each function has a page with its calling forms, a description of what Evans does with each one, a short example and links to related functions. Type in the search box to filter the tree on the left by name and by the text of the pages, and press Enter to open the first match. Every example has a Run link that runs it in the console as if you had typed it there, and a Copy link that puts it on the clipboard. In the script editor, Ctrl+click a function name to open its page directly. F1 and Help, Documentation open this overview.

## Build

[tf](tf) · [ss](ss) · [zpk](zpk) · [tf2ss](tf2ss) · [ss2tf](ss2tf) · [pade](pade) · [pid](pid) · [lead](lead) · [lag](lag)

## Connect

[series](series) · [parallel](parallel) · [feedback](feedback) · [minreal](minreal)

## Inspect

[pole](pole) · [zero](zero) · [damp](damp) · [dcgain](dcgain) · [stepinfo](stepinfo) · [margin](margin) · [allmargin](allmargin) · [bandwidth](bandwidth) · [routh](routh) · [jury](jury) · [errconst](errconst) · [mpsplit](mpsplit)

## Time

[step](step) · [impulse](impulse) · [lsim](lsim) · [initial](initial) · [ramp](ramp)

## Frequency

[bode](bode) · [nyquist](nyquist) · [nichols](nichols) · [pzmap](pzmap) · [rlocus](rlocus)

## State space

[ctrb](ctrb) · [obsv](obsv) · [gram](gram) · [hsvd](hsvd) · [balred](balred) · [canon](canon) · [isctrb](isctrb) · [isobsv](isobsv)

## Design

[place](place) · [acker](acker) · [lqr](lqr) · [lqi](lqi) · [lqe](lqe) · [kalman](kalman) · [estim](estim) · [zn](zn)

## Discrete

[c2d](c2d) · [d2c](d2c) · [deadbeat](deadbeat)

## Simulink

[sim](sim) · [linearize](linearize)

## Apps

[pidtune](pidtune) · [ltiview](ltiview) · [sisotool](sisotool) · [pidtuner](pidtuner)

## Model data

[tfdata](tfdata) · [zpkdata](zpkdata) · [ssdata](ssdata) · [evalfr](evalfr) · [freqresp](freqresp) · [isstable](isstable)

## Plot options

[bodeoptions](bodeoptions) · [nyquistoptions](nyquistoptions) · [timeoptions](timeoptions) · [pzoptions](pzoptions)

## Arrays

[zeros](zeros) · [ones](ones) · [eye](eye) · [rand](rand) · [linspace](linspace) · [logspace](logspace) · [size](size) · [length](length) · [numel](numel) · [reshape](reshape) · [repmat](repmat)

## Maths

[abs](abs) · [sqrt](sqrt) · [exp](exp) · [sum](sum) · [mean](mean) · [max](max) · [min](min) · [sort](sort) · [find](find) · [cumsum](cumsum) · [diff](diff) · [roots](roots) · [poly](poly) · [polyval](polyval) · [conv](conv) · [inv](inv) · [det](det) · [eig](eig)

## Plotting

[plot](plot) · [figure](figure) · [subplot](subplot) · [hold](hold) · [grid](grid) · [title](title) · [xlabel](xlabel) · [ylabel](ylabel) · [legend](legend) · [axis](axis) · [xlim](xlim) · [ylim](ylim) · [semilogx](semilogx)

## Symbolic

[syms](syms) · [sym](sym) · [laplace](laplace) · [ilaplace](ilaplace) · [simplify](simplify) · [expand](expand) · [factor](factor) · [partfrac](partfrac) · [numden](numden) · [sym2poly](sym2poly) · [subs](subs) · [int](int) · [limit](limit) · [solve](solve) · [double](double) · [matlabFunction](matlabFunction) · [fplot](fplot)

## Text

[disp](disp) · [fprintf](fprintf) · [sprintf](sprintf) · [num2str](num2str)

## Session

[clc](clc) · [clear](clear) · [tic](tic) · [toc](toc)

## Statistics

[var](var) · [mode](mode) · [cov](cov) · [corrcoef](corrcoef) · [prctile](prctile) · [quantile](quantile) · [skewness](skewness) · [kurtosis](kurtosis) · [movmean](movmean) · [movmedian](movmedian) · [smoothdata](smoothdata) · [detrend](detrend) · [normpdf](normpdf) · [normcdf](normcdf) · [norminv](norminv) · [ttest](ttest) · [regress](regress) · [randi](randi) · [randperm](randperm) · [rng](rng)

## Linear algebra

[svd](svd) · [qr](qr) · [lu](lu) · [chol](chol) · [pinv](pinv) · [null](null) · [orth](orth) · [expm](expm) · [logm](logm) · [sqrtm](sqrtm) · [cross](cross) · [dot](dot) · [cond](cond) · [triu](triu) · [tril](tril) · [circshift](circshift) · [sub2ind](sub2ind) · [ind2sub](ind2sub)

## Strings

[strsplit](strsplit) · [strjoin](strjoin) · [strtrim](strtrim) · [strrep](strrep) · [regexp](regexp) · [regexpi](regexpi) · [regexprep](regexprep) · [contains](contains) · [startsWith](startsWith) · [endsWith](endsWith) · [split](split) · [join](join) · [upper](upper) · [lower](lower) · [pad](pad) · [strfind](strfind) · [strncmp](strncmp) · [strncmpi](strncmpi) · [blanks](blanks) · [deblank](deblank) · [isspace](isspace) · [isletter](isletter) · [isstrprop](isstrprop)

## Cells and structs

[cellfun](cellfun) · [arrayfun](arrayfun) · [cell2mat](cell2mat) · [struct2cell](struct2cell) · [cell2struct](cell2struct) · [isfield](isfield) · [rmfield](rmfield) · [orderfields](orderfields) · [getfield](getfield) · [setfield](setfield) · [iscellstr](iscellstr) · [deal](deal) · [isequal](isequal) · [isequaln](isequaln) · [ismember](ismember)

## Data files

[readmatrix](readmatrix) · [writematrix](writematrix) · [readtable](readtable) · [writetable](writetable) · [table](table) · [fopen](fopen) · [fclose](fclose) · [fgetl](fgetl) · [textscan](textscan) · [jsondecode](jsondecode) · [jsonencode](jsonencode)

## Signal processing

[filtfilt](filtfilt) · [fir1](fir1) · [pwelch](pwelch) · [hann](hann) · [xcorr](xcorr) · [resample](resample)

## Fitting and optimisation

[fit](fit) · [lsqcurvefit](lsqcurvefit) · [fsolve](fsolve) · [fmincon](fmincon) · [linprog](linprog) · [integral](integral) · [spline](spline)

## System

[who](who) · [whos](whos) · [dir](dir) · [exist](exist) · [datestr](datestr) · [nchoosek](nchoosek) · [dec2bin](dec2bin)

## Guides

[s, the Laplace variable](s) · [MATLAB and Python at the prompt](python)
