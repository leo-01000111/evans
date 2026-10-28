"""
How each MATLAB-shaped function is called, as the completion popup shows it.

The Python functions behind the console's commands take ``*systems`` and
keyword options (``step(*systems, t=None, plot=True)``), and the MATLAB
runtime's ``f_*`` methods mostly take ``*args`` — introspecting them would
show the plumbing. This table is the call as a student writes it, the way
MATLAB's own documentation states it: ``step(sys, t)``, ``lqr(A, B, Q, R)``.
A name not listed here falls back to its Python signature
(:func:`evans.ui.code.completion.python_signature`).

Each line is ``signature | description``; the description wins over the
docstring's first line where both exist.
"""

from __future__ import annotations

_TABLE = """
tf(num, den)                | Transfer function from numerator and denominator coefficients
ss(A, B, C, D, Ts)          | State-space model (Ts: already discrete)
zpk(z, p, k, Ts)            | Zero-pole-gain model (Ts: discrete)
tf2ss(num, den)             | Transfer function to state space: [A, B, C, D]
ss2tf(A, B, C, D)           | State space to transfer function: [num, den]
pade(T, n)                  | Padé approximation of a time delay e^(-sT)
pid(Kp, Ki, Kd, Tf)         | PID controller
lead(K, z, p)               | Lead compensator
lag(K, z, p)                | Lag compensator
series(sys1, sys2)          | Series connection: sys2 * sys1
parallel(sys1, sys2)        | Parallel connection: sys1 + sys2
feedback(sys1, sys2, sign)  | Closed loop: sys1 / (1 + sys1*sys2), negative by default
minreal(sys, tol)           | Cancel pole-zero pairs
pole(sys)                   | Poles of a system
zero(sys)                   | Zeros of a system
damp(sys)                   | Natural frequencies and damping ratios of the poles
dcgain(sys)                 | Steady-state gain: G(0), or G(1) if discrete
stepinfo(sys)               | Rise time, settling time, overshoot of the step response
margin(sys)                 | Gain and phase margins: [Gm, Pm, Wcg, Wcp]
allmargin(sys)              | Every gain, phase and delay margin
bandwidth(sys)              | Frequency where the gain falls 3 dB below DC
routh(den)                  | Routh-Hurwitz array of a polynomial
jury(den)                   | Jury stability table of a discrete polynomial
errconst(sys)               | Static error constants Kp, Kv, Ka
mpsplit(sys)                | Split into minimum-phase and all-pass parts
step(sys, t)                | Step response
impulse(sys, t)             | Impulse response
lsim(sys, u, t)             | Response to an arbitrary input u(t)
initial(sys, x0, t)         | Free response from initial state x0
ramp(sys, t)                | Ramp response
bode(sys, w)                | Bode magnitude and phase
nyquist(sys, w)             | Nyquist plot
nichols(sys, w)             | Nichols chart
pzmap(sys)                  | Pole-zero map
rlocus(sys, k)              | Root locus
ctrb(A, B)                  | Controllability matrix
obsv(A, C)                  | Observability matrix
gram(sys, type)             | Controllability ('c') or observability ('o') Gramian
hsvd(sys)                   | Hankel singular values
balred(sys, order)          | Balanced model reduction
canon(sys, type)            | Canonical state-space form ('modal' or 'companion')
isctrb(A, B)                | Is (A, B) controllable?
isobsv(A, C)                | Is (A, C) observable?
place(A, B, p)              | Pole placement gain K
acker(A, B, p)              | Pole placement by Ackermann's formula
lqr(A, B, Q, R)             | Linear-quadratic regulator: [K, S, e]
lqi(sys, Q, R)              | LQR with integral action
lqe(A, G, C, Q, R)          | Kalman estimator gain: [L, P, e]
kalman(sys, Qn, Rn)         | Kalman filter
estim(sys, L)               | Observer from an estimator gain
zn(sys, type)               | Ziegler-Nichols PID tuning
c2d(sys, Ts, method)        | Continuous to discrete time
d2c(sys, method)            | Discrete to continuous time
deadbeat(sys)               | Deadbeat controller
sim(model, tstop)           | Simulate a Simulink-style model
linearize(model, io)        | Linearize a model about an operating point
pidtune(sys, type)          | Tune a PID controller for a plant
ltiview(sys)                | Open the linear system viewer
sisotool(G, C)              | Open the SISO design tool on plant G, compensator C
pidtuner(sys)               | Open the PID tuner
tfdata(sys)                 | Numerator and denominator: [num, den]
zpkdata(sys)                | Zeros, poles and gain: [z, p, k]
ssdata(sys)                 | State-space matrices: [A, B, C, D]
evalfr(sys, x)              | Evaluate a system at one complex frequency
freqresp(sys, w)            | Frequency response at the frequencies w
isstable(sys)               | Are all poles stable?
bodeoptions()               | Options for bodeplot
nyquistoptions()            | Options for nyquistplot
timeoptions()               | Options for stepplot and friends
pzoptions()                 | Options for pzplot
stepplot(sys, t)            | Step response plot
impulseplot(sys, t)         | Impulse response plot
bodeplot(sys, w)            | Bode plot
nyquistplot(sys, w)         | Nyquist plot
pzplot(sys)                 | Pole-zero plot
rlocusplot(sys)             | Root locus plot
sgrid()                     | Damping and natural-frequency grid on an s-plane plot
clc                         | Clear the command window
clear(name)                 | Remove variables from the workspace
clearvars(name)             | Remove variables from the workspace
close(fig)                  | Close figures: close all
clf                         | Clear the current figure
figure(n)                   | Open or select a figure
gcf                         | The current figure
gca                         | The current axes
subplot(m, n, p)            | Axes in an m-by-n grid
sgtitle(text)               | Title over all subplots
hold(state)                 | Keep the plot when adding new lines: hold on
grid(state)                 | Grid lines: grid on
box(state)                  | Axes box outline
format(style)               | Number display format: format long
pause(seconds)              | Wait
tic                         | Start a stopwatch
toc                         | Seconds since tic
exist(name)                 | Is the name a variable (1), file (2) or function (5)?
cd(folder)                  | Change the current folder
pwd                         | The current folder
addpath(folder)             | Add a folder to the search path
rmpath(folder)              | Remove a folder from the search path
fullfile(part1, part2)      | Join path parts
fileparts(file)             | [folder, name, ext] of a path
isfile(file)                | Is it a file?
isfolder(folder)            | Is it a folder?
mkdir(folder)               | Create a folder
input(prompt)               | Ask for a value
error(msg, A)               | Throw an error
warning(msg, A)             | Print a warning
assert(cond, msg)           | Error unless cond is true
disp(X)                     | Display a value
fprintf(fmt, A)             | Print formatted text
sprintf(fmt, A)             | Format text into a string
num2str(x, precision)       | Number to text
int2str(x)                  | Integer to text
mat2str(A)                  | Matrix to MATLAB syntax text
str2num(text)               | Text to number
strcat(s1, s2)              | Join strings
strcmp(s1, s2)              | Are the strings equal?
strcmpi(s1, s2)             | Are the strings equal, ignoring case?
upper(str)                  | Uppercase
lower(str)                  | Lowercase
strtrim(str)                | Remove leading and trailing whitespace
strrep(str, old, new)       | Replace text
class(obj)                  | Class name of a value
isa(obj, classname)         | Is the value of that class?
fieldnames(s)               | Field names of a struct
isfield(s, field)           | Does the struct have the field?
struct(field, value)        | Structure
cell(n)                     | Cell array
size(A, dim)                | Array dimensions
length(A)                   | Largest dimension
numel(A)                    | Number of elements
ndims(A)                    | Number of dimensions
isempty(A)                  | Is the array empty?
zeros(n, m)                 | Array of zeros
ones(n, m)                  | Array of ones
eye(n)                      | Identity matrix
rand(n, m)                  | Uniform random numbers
randn(n, m)                 | Normal random numbers
linspace(a, b, n)           | n points from a to b, evenly spaced
logspace(a, b, n)           | n points from 10^a to 10^b (to pi if b is pi)
repmat(A, m, n)             | Tile an array
reshape(A, m, n)            | Change an array's shape
diag(v)                     | Diagonal matrix, or a matrix's diagonal
horzcat(A, B)               | Join side by side
vertcat(A, B)               | Join one above the other
round(x)                    | Round to the nearest integer
sum(A, dim)                 | Sum of elements
prod(A, dim)                | Product of elements
mean(A, dim)                | Average
median(A, dim)              | Median
std(A)                      | Standard deviation
cumsum(A, dim)              | Cumulative sum
diff(A)                     | Differences between neighbours, or a symbolic derivative
max(A)                      | Largest element: [M, I]
min(A)                      | Smallest element: [M, I]
sort(A, dim, direction)     | Sort
unique(A)                   | Unique values
find(X)                     | Indices of nonzero elements
trapz(x, y)                 | Trapezoidal integral
cumtrapz(x, y)              | Cumulative trapezoidal integral
interp1(x, v, xq)           | 1-D interpolation
inv(A)                      | Matrix inverse
det(A)                      | Determinant
rank(A)                     | Rank
trace(A)                    | Trace
norm(A)                     | Norm
eig(A)                      | Eigenvalues: [V, D]
kron(A, B)                  | Kronecker product
roots(p)                    | Polynomial roots
poly(r)                     | Polynomial from its roots, or characteristic polynomial
polyval(p, x)               | Evaluate a polynomial
polyfit(x, y, n)            | Fit a polynomial of degree n
conv(u, v)                  | Multiply polynomials (convolution)
deconv(u, v)                | Divide polynomials: [q, r]
meshgrid(x, y)              | 2-D grid coordinates: [X, Y]
fft(x)                      | Fast Fourier transform
ifft(X)                     | Inverse FFT
filter(b, a, x)             | Filter a signal
butter(n, Wn)               | Butterworth filter design: [b, a]
freqz(b, a, n)              | Digital filter frequency response
findpeaks(y)                | Local maxima: [pks, locs]
ode45(odefun, tspan, y0)    | Solve an ODE (Runge-Kutta 4/5): [t, y]
ode23(odefun, tspan, y0)    | Solve an ODE (Runge-Kutta 2/3): [t, y]
ode15s(odefun, tspan, y0)   | Solve a stiff ODE: [t, y]
odeset(name, value)         | ODE solver options
fzero(fun, x0)              | Root of a function
fminsearch(fun, x0)         | Minimum of a function (Nelder-Mead)
fminbnd(fun, x1, x2)        | Minimum on an interval
audioread(file)             | Read an audio file: [y, Fs]
audiowrite(file, y, Fs)     | Write an audio file
sound(y, Fs)                | Play a sound
save(file, vars)            | Save variables to a file
load(file)                  | Load variables from a file
plot(x, y, spec)            | Line plot
stem(x, y)                  | Stem plot of a sequence
stairs(x, y)                | Staircase plot
bar(x, y)                   | Bar chart
barh(x, y)                  | Horizontal bar chart
histogram(x, nbins)         | Histogram
semilogx(x, y)              | Plot with a logarithmic x axis
semilogy(x, y)              | Plot with a logarithmic y axis
loglog(x, y)                | Plot with both axes logarithmic
title(text)                 | Axes title
xlabel(text)                | x-axis label
ylabel(text)                | y-axis label
legend(label1, label2)      | Legend
axis(limits)                | Axis limits: [xmin xmax ymin ymax]
xlim([xmin xmax])           | x-axis limits
ylim([ymin ymax])           | y-axis limits
saveas(fig, file)           | Save a figure to a file
exportgraphics(fig, file)   | Save a figure to a file
abs(x)                      | Absolute value, magnitude
sqrt(x)                     | Square root
exp(x)                      | Exponential
log(x)                      | Natural logarithm
log10(x)                    | Base-10 logarithm
sin(x)                      | Sine
cos(x)                      | Cosine
tan(x)                      | Tangent
atan2(y, x)                 | Four-quadrant arctangent
floor(x)                    | Round down
ceil(x)                     | Round up
real(z)                     | Real part
imag(z)                     | Imaginary part
conj(z)                     | Complex conjugate
angle(z)                    | Phase angle (rad)
mod(a, m)                   | Remainder after division (sign of m)
rem(a, b)                   | Remainder after division (sign of a)
db(x)                       | Magnitude in decibels
pi                          | 3.14159…
eps                         | Floating-point relative accuracy
Inf                         | Infinity
NaN                         | Not a number
help_fm()                   | List the console's commands
syms(x, y)                  | Make symbolic variables: syms s t, syms a positive
sym(x)                      | Symbolic variable from a name, or an exact symbolic number
str2sym(text)               | Read a formula from text
laplace(f, t, s)            | Laplace transform, t to s by default
ilaplace(F, s, t)           | Inverse Laplace transform, s to t by default
simplify(f)                 | Simplest form of a formula
expand(f)                   | Multiply out products and powers
factor(f)                   | Factor a polynomial, or a number into primes
collect(f, x)               | Gather the terms in powers of x
partfrac(f, s)              | Partial-fraction expansion
numden(f)                   | Numerator and denominator: [N, D]
subs(f, old, new)           | Substitute values or formulas for variables
int(f, x, a, b)             | Integral, indefinite or from a to b
limit(f, x, a)              | Limit as x approaches a ('left', 'right')
taylor(f, x, a)             | Taylor series ('Order', n)
solve(eqn, x)               | Solve equations for variables
sym2poly(p)                 | Polynomial coefficients as numbers
poly2sym(c, x)              | Polynomial from its coefficients
symvar(f)                   | The symbolic variables in a formula
double(x)                   | Convert to a number
vpa(x, d)                   | Decimal value to d significant digits
pretty(f)                   | Print a formula in two dimensions
latex(f)                    | LaTeX source of a formula
isAlways(cond)              | Is the condition true for every value?
heaviside(x)                | Unit step, 1/2 at 0
dirac(x)                    | Dirac delta
matlabFunction(f)           | Function handle that evaluates a formula
fplot(f, [a b])             | Plot a formula or function over an interval
var(A)                      | Variance of a vector, or of each column of a matrix
mode(A)                     | Most frequent value of a vector, or of each column of a matrix
cov(x)                      | Covariance of a vector, of the columns of a matrix, or of two vectors
corrcoef(A)                 | Correlation coefficients of the columns of a matrix, or of two vectors
prctile(X, p)               | Percentiles of a vector, or of each column of a matrix
quantile(X, p)              | Quantiles of a vector, or of each column of a matrix
skewness(X)                 | Sample skewness of a vector, or of each column of a matrix
kurtosis(X)                 | Sample kurtosis of a vector, or of each column of a matrix
movmean(A, k)               | Moving average over a sliding window
movmedian(A, k)             | Moving median over a sliding window
smoothdata(A, 'movmean', k) | Smooth noisy data with a moving average or moving median
detrend(x)                  | Remove a straight-line (or polynomial) trend from data
normpdf(x)                  | Probability density of the normal distribution
normcdf(x)                  | Cumulative distribution function of the normal distribution
norminv(p)                  | Inverse of the normal cumulative distribution function
ttest(x)                    | One-sample or paired-sample t-test
regress(y, X)               | Multiple linear regression by least squares
randi(imax)                 | Random integers, uniformly distributed
randperm(n)                 | Random permutation of the integers 1 to n
rng(seed)                   | Seed or save the random number generator used by rand, randn, randi and randperm
svd(A)                      | Singular value decomposition
qr(A)                       | QR decomposition: an orthogonal times an upper-triangular matrix
lu(A)                       | LU decomposition with partial pivoting
chol(A)                     | Cholesky factorisation of a symmetric positive definite matrix
pinv(A)                     | Moore-Penrose pseudo-inverse
null(A)                     | Orthonormal basis for the null space of a matrix
orth(A)                     | Orthonormal basis for the range of a matrix
expm(A)                     | Matrix exponential
logm(A)                     | Matrix logarithm
sqrtm(A)                    | Matrix square root
cross(A, B)                 | Cross product of 3-element vectors
dot(A, B)                   | Dot product of two vectors, or of the columns of two matrices
cond(A)                     | Condition number of a matrix
triu(A)                     | Upper triangular part of a matrix
tril(A)                     | Lower triangular part of a matrix
circshift(A, k)             | Shift the elements of an array round in a circle
sub2ind(sz, row, col)       | Convert row and column subscripts to linear indices
ind2sub(sz, ind)            | Convert linear indices to row and column subscripts
strsplit(str)               | Split a character vector at a delimiter into a cell array
strjoin(C)                  | Join the character vectors of a cell array into one
regexp(str, expression)     | Match a regular expression
regexpi(str, expression)    | Match a regular expression, ignoring case
regexprep(str, expression, replace) | Replace text that matches a regular expression
contains(str, pattern)      | True where text contains a pattern
startsWith(str, pattern)    | True where text starts with a pattern
endsWith(str, pattern)      | True where text ends with a pattern
split(str)                  | Split text at delimiters into a column cell array
join(C)                     | Join the text in a cell array, with spaces or a delimiter
pad(str)                    | Pad text with spaces or another character to a common length
strfind(str, pattern)       | Starting positions of a pattern in text
strncmp(s1, s2, n)          | Compare the first n characters of text
strncmpi(s1, s2, n)         | Compare the first n characters of text, ignoring case
blanks(n)                   | A character vector of spaces
deblank(str)                | Remove trailing whitespace and null characters
isspace(str)                | True for whitespace characters
isletter(str)               | True for letters
isstrprop(str, category)    | True where characters belong to a category
cellfun(func, C)            | Apply a function to each element of a cell array
arrayfun(func, X)           | Apply a function to each element of an array
cell2mat(C)                 | Join the contents of a cell array into one matrix
struct2cell(s)              | The values of a struct's fields, as a cell array
cell2struct(C, fields)      | Build a struct from a cell array of values and a list of field names
rmfield(s, name)            | Remove fields from a struct
orderfields(s)              | Reorder the fields of a struct
getfield(s, name)           | The value of a struct field named by a string
setfield(s, name, value)    | A copy of a struct with a field set to a value
iscellstr(C)                | True for a cell array whose elements are all character vectors
deal(X)                     | Copy inputs to outputs
isequal(A, B)               | True when values are equal in size and content
isequaln(A, B)              | True when values are equal, treating NaN as equal to NaN
ismember(A, S)              | Which elements of one array occur in another
readmatrix(filename)        | Read a matrix of numbers from a delimited text file
writematrix(A)              | Write a matrix to a delimited text file
readtable(filename)         | Read a table with named columns from a delimited text file
writetable(T)               | Write a table to a delimited text file, names first
table(var1, ..., varN)      | A table of named columns, built from column vectors
fopen(filename)             | Open a file and return its file identifier
fclose(fid)                 | Close an open file
fgetl(fid)                  | Read the next line of a file, without its newline
textscan(fid, format)       | Read columns of formatted data from a file or text
jsondecode(text)            | Read JSON text into structs, arrays and cells
jsonencode(value)           | Write a value as JSON text
filtfilt(b, a, x)           | Zero-phase digital filtering: filter forwards, then backwards
fir1(n, Wn)                 | Window-method FIR filter design
pwelch(x)                   | Power spectral density by Welch's averaged periodogram
hann(n)                     | Hann (raised-cosine) window
xcorr(x)                    | Cross-correlation of two signals, or autocorrelation of one
resample(x, p, q)           | Change the sample rate by a rational factor p/q
fit(x, y, fittype)          | Fit a library curve model to data
lsqcurvefit(fun, x0, xdata, ydata) | Nonlinear least-squares fit of a model's parameters to data
fsolve(fun, x0)             | Solve a system of nonlinear equations F(x) = 0
fmincon(fun, x0, A, b)      | Minimise a function subject to constraints
linprog(f, A, b)            | Linear programming: minimise f'*x subject to linear constraints
integral(fun, a, b)         | Numerical integration of a function over an interval
spline(x, y, xq)            | Cubic spline interpolation, MATLAB's not-a-knot spline
who                         | List the variables in the workspace
whos                        | List the workspace's variables with their sizes and classes
dir                         | List the files and folders in a folder
datestr(t)                  | Convert a date to text
nchoosek(n, k)              | Binomial coefficient, or all combinations of a vector's elements
dec2bin(d)                  | Convert a nonnegative integer to its binary digits as text
"""


def _parse(table: str) -> dict[str, tuple[str, str]]:
    out = {}
    for line in table.strip().splitlines():
        signature, _, description = line.partition("|")
        signature = signature.strip()
        name = signature.split("(", 1)[0]
        out[name] = (signature if "(" in signature else "",
                     description.strip())
    return out


#: name → (call signature or "" for a constant/command, description).
SIGNATURES: dict[str, tuple[str, str]] = _parse(_TABLE)
