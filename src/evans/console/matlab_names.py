"""
MATLAB functions Evans does not have yet.

Typing one of these gives "Unrecognized function or variable", the same words
as for a typo. :func:`missing_message` adds a sentence telling the user which
of the two it is, so nobody hunts for a spelling mistake that is not there.
The same table is the "Not in Evans" help page. A name leaves it when the
function is written; ``tests/golden/test_lib_lang.py`` fails if a name here
has been implemented without being removed, or the page is out of date.
"""

from __future__ import annotations

#: group → names, as MATLAB spells them.
NOT_IN_EVANS: dict[str, tuple[str, ...]] = {
    "Arrays and indexing": (
        "accumarray", "bsxfun", "colon", "cummax", "cummin", "histc",
        "mat2cell", "mink", "maxk", "rot90", "sortrows", "issorted",
        "bounds",
        "normalize", "rescale", "histcounts2", "histogram2", "vander", "hilb", "invhilb",
        "toeplitz", "hankel", "pascal", "rosser", "wilkinson", "gallery",
        "hadamard", "compan", "blkdiag", "shiftdim",
        "swapbytes",
    ),
    "Sets": ("intersect", "setdiff", "setxor", "union", "uniquetol", "ismembertol"),
    "Numeric types": ("typecast",),
    "Sparse and iterative solvers": (
        "lsqr", "ilu", "ichol",
    ),
    "Linear algebra": (
        "lsqminnorm", "linsolve", "normest", "givens", "hess", "schur", "qz",
        "balance", "sylvester", "polyeig", "condeig",
    ),
    "Maths and numerics": (
        "rat", "rats", "ellipke", "ellipj", "legendre", "besselj",
        "bessely", "besseli", "besselk", "airy", "expint", "psi", "gammainc",
        "betainc", "nextpow2", "primefactors", "perms", "del2", "gradient", "dblquad", "integral3", "lsqlin", "ga", "patternsearch", "particleswarm",
        "simulannealbnd",
    ),
    "Differential equations": (
        "ode113", "ode15i", "odeget", "dde23", "ddesd", "bvp4c", "bvp5c", "pdepe",
    ),
    "Strings": (
        "strvcat", "sscanf", "validatestring", "strjust", "strtok", "regexptranslate",
        "compose", "extractBetween", "extractAfter",
        "extractBefore", "insertAfter", "insertBefore", "erase",
        "eraseBetween", "replace", "replaceBetween", "reverse", "strip",
        "count", "matches", "textwrap",
    ),
    "Tables, dates and categories": (
        "datetime", "duration", "seconds", "minutes", "hours", "days",
        "years", "calendar", "weekday", "eomday", "addtodate", "timetable",
        "categorical", "cell2table", "table2struct",
        "table2cell", "innerjoin", "outerjoin", "stack", "unstack",
        "groupsummary", "grouptransform", "rowfun", "varfun", "splitapply",
        "findgroups", "retime", "synchronize", "isbetween", "timeit",
        "cputime", "etime", "weeknum", "milliseconds", "isdatetime",
        "isduration", "iscategorical", "istimetable", "summary", "head",
        "tail", "removevars", "addvars", "movevars", "renamevars",
        "splitvars", "mergevars", "rmmissing", "fillmissing",
        "standardizeMissing", "ismissing", "isoutlier", "rmoutliers",
        "filloutliers",
    ),
    "Language and functions": (
        "inputname", "narginchk", "nargoutchk", "nargchk",
        "evalc", "lasterr", "lastwarn", "onCleanup",
        "isvarname", "genvarname", "mfilename", "mlock", "munlock",
        "builtin", "run", "rehash", "pcode", "mex", "memoize", "isargout",
        "nthargout", "ismethod", "isprop", "methods", "properties",
        "metaclass", "isobject", "isjava", "javaObject", "pyrun", "pyenv",
    ),
    "Files, dialogs and hardware": (
        "imread", "imwrite", "imfinfo", "importdata", "readcell", "writecell", "readvars", "readlines",
        "writelines", "tempdir", "tempname",
        "websave", "webread", "urlread", "unzip", "zip", "gzip", "gunzip",
        "tar", "untar", "matfile", "xmlread", "xmlwrite",
        "uiwait", "uiresume",
        "menu", "uifigure", "uicontrol", "uimenu",
        "uitable", "uipanel", "serialport", "serialportlist", "tcpclient",
        "udpport", "bluetooth", "i2c", "spi", "arduino",
    ),
    "Plotting": (
        "gco",
        "polarplot", "polaraxes", "compass", "feather",
        "rose", "pareto", "stem3", "waterfall", "ribbon", "trisurf",
        "triplot", "trimesh", "slice", "isosurface", "streamline",
        "streamslice", "comet", "comet3", "animatedline", "getframe",
        "movie", "refresh", "hggroup", "daspect", "pbaspect",
        "camlight", "lighting", "material", "light", "camorbit", "campos",
        "camtarget", "zoom", "pan", "rotate3d", "datacursormode",
        "linkaxes", "linkprop", "copyobj", "findobj", "findall", "ishandle",
        "isgraphics", "set", "get", "scatterhistogram", "heatmap",
        "wordcloud", "geoplot", "geobubble", "plotmatrix", "plotyy",
        "ezplot", "fcontour", "fsurf", "fmesh", "fplot3", "bar3", "bar3h",
    ),
    "Graphs, geometry and clustering": (
        "graph", "digraph", "shortestpath", "conncomp", "minspantree",
        "delaunay", "convhull", "voronoi", "inpolygon", "polyarea",
        "polyshape", "rectint", "knnsearch", "kmeans", "pdist", "pdist2",
        "linkage", "cluster", "dbscan",
    ),
    "Statistics and distributions": (
        "mad", "range", "iqr", "zscore", "histfit", "normfit", "normrnd",
        "unifrnd", "unifpdf", "unifcdf", "exprnd", "exppdf", "expcdf",
        "poissrnd", "binornd", "binopdf", "binocdf", "chi2pdf", "chi2cdf",
        "tpdf", "tcdf", "fpdf", "fcdf", "gampdf", "gamcdf", "betapdf",
        "betacdf", "wblpdf", "wblcdf", "lognpdf", "logncdf", "ksdensity",
        "ecdf", "anova1", "anovan", "ttest2", "kstest", "lillietest",
        "chi2gof", "ranksum", "signrank", "fitlm", "fitglm", "stepwiselm",
        "fitnlm", "fitctree", "fitcsvm", "fitcknn", "predict", "crossval",
        "pca", "factoran", "mvnrnd", "mvnpdf", "mvncdf", "movsum", "movstd",
        "movvar", "movmin", "movmax", "movmad", "movprod", "movfun",
    ),
    "Signal processing": (
        "conv2", "filter2", "fft2", "ifft2", "fftn", "ifftn", "unwrap", "peak2peak", "rms", "snr",
        "sinad", "thd", "bandpass", "lowpass", "highpass", "bandstop",
        "envelope", "medfilt1", "sgolay", "sgolayfilt", "buttord", "cheb1ord", "ellipord", "besself",
        "firls", "firpm", "remez", "kaiserord", "tf2zp", "zp2tf", "tf2sos",
        "sos2tf", "zp2sos", "sos2zp", "freqs", "invfreqz", "invfreqs", "lpc",
        "levinson", "hilbert", "chirp", "gauspuls", "sawtooth", "square",
        "sinc", "pulstran", "rectpuls", "tripuls", "stft", "istft", "cwt",
        "dwt", "idwt", "wavedec", "waverec",
    ),
    "Control and identification": (
        "tfest", "arx", "armax", "oe", "bj", "n4sid", "ssest", "iddata",
        "idtf", "idss", "idpoly", "procest", "compare", "resid", "pem",
        "impulseest", "spa", "etfe", "systune", "hinfsyn", "mixsyn",
        "loopsyn", "ncfsyn", "musyn", "robuststab", "wcgain", "ucover",
        "mpc", "mpcmove", "linmod", "dlinmod", "findop",
        "operspec", "frd", "fitfrd", "iopzplot", "sigma", "sigmaplot", "dsort", "esort", "ssbal",
        "prescale", "rss", "drss", "rlocfind", "icare", "idare", "care",
        "dare", "dlqr", "lqry", "lqrd", "kalmd", "reg", "augstate",
        "connect", "append", "sminreal", "modred", "stabsep", "ctrbf",
        "obsvf", "isproper", "isdt", "isct", "issiso", "ismimo", "getdelay",
        "totaldelay", "absorbDelay", "thiran", "d2d",
        "upsample", "pidstd", "pidtool", "getIOTransfer",
        "getLoopTransfer",
    ),
    "Symbolic": (
        "dsolve", "ztrans", "iztrans", "fourier", "ifourier", "symsum", "symprod", "vpasolve", "digits", "assume",
        "assumeAlso", "assumptions", "coeffs", "horner",
        "rewrite", "isolate", "children", "lhs", "rhs", "jacobian",
        "hessian", "curl", "divergence", "laplacian", "potential", "jordan",
        "eigenvals", "eigenvects", "rref", "charpoly", "minpoly",
        "odeToVectorField", "daeFunction", "piecewise", "kroneckerDelta", "rectangularPulse", "triangularPulse", "sinint",
        "cosint", "lambertw", "zeta", "hypergeom", "meijerG", "symfun",
        "sympref", "texlabel",
    ),
    "Simulink": (
        "slbuild", "replace_block", "sldebug", "simset",
        "simget", "sltest", "slproject",
    ),
    "System and environment": (
        "ver", "version", "license", "usejava", "ispref", "getpref",
        "setpref", "addpref", "rmpref", "prefdir", "userpath", "matlabroot",
        "winopen", "open", "edit", "type", "doc", "lookfor", "helpwin",
        "demo", "web", "profile", "profsave", "checkcode", "publish",
        "diary", "echo", "bench", "memory", "gpuArray",
        "gather", "parpool", "parfeval", "batch", "gcp", "distributed",
        "codistributed", "datastore", "mapreduce", "codegen", "loadlibrary",
        "calllib", "actxserver", "dos", "unix", "perl", "ftp", "sendmail",
    ),
}

#: Every name above, for the lookup.
ALL: frozenset[str] = frozenset(n for group in NOT_IN_EVANS.values()
                                for n in group)


def missing_message(name: str) -> str:
    """The error for a name that is neither a variable nor a function."""
    text = f"Unrecognized function or variable '{name}'."
    if name in ALL:
        text += (f" '{name}' is a MATLAB function that Evans does not have "
                 f"yet, so this is not a typo. Help > Not in Evans lists "
                 f"what is missing.")
    return text
