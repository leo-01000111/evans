"""
Tables, datetimes, durations and timetables.

Each test types MATLAB the way a user would and checks the answer against a
value worked out by hand (a calendar, a sum), not against Evans's own output.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from evans.console import Interpreter, set_figure_sink
from evans.console.figures import recording_sink


@pytest.fixture
def it(tmp_path, monkeypatch):
    previous = set_figure_sink(recording_sink())
    monkeypatch.chdir(tmp_path)
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "".join(r.output or "" for r in results)


def error_of(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, "expected an error"
    return failed[0].error


def val(it, name):
    return it.namespace[name]


T3 = "T = table([3;1;2], {'c';'a';'b'}, [30;10;20], 'VariableNames', {'n','s','m'});"


# ── indexing and assignment ───────────────────────────────────

def test_brace_indexing_gives_contents(it):
    run(it, T3 + "a = T{2,'m'}; b = T{:,[1 3]}; c = T{1,'s'}; d = T{2:3,1};")
    assert val(it, "a") == 10
    np.testing.assert_array_equal(val(it, "b"), [[3, 30], [1, 10], [2, 20]])
    assert list(val(it, "c")) == ["c"]
    np.testing.assert_array_equal(val(it, "d"), [[1], [2]])


def test_mixed_brace_refuses(it):
    run(it, T3)
    assert "Unable to concatenate" in error_of(it, "x = T{1,[1 2]};")


def test_assign_column_and_element(it):
    run(it, T3 + "T.k = [1;2;3]; T.m(2) = 99; T.n = T.n * 2; w = width(T);")
    np.testing.assert_array_equal(val(it, "T").variable(3), [[1], [2], [3]])
    np.testing.assert_array_equal(val(it, "T").variable(2), [[30], [99], [20]])
    np.testing.assert_array_equal(val(it, "T").variable(0), [[6], [2], [4]])
    assert val(it, "w") == 4


def test_assignment_is_by_value(it):
    run(it, T3 + "U = T; U.m(1) = -1; a = T.m(1);")
    assert val(it, "a") == 30


def test_wrong_height_is_refused(it):
    run(it, T3)
    assert "number of rows" in error_of(it, "T.z = [1;2];")


def test_delete_rows_and_variables(it):
    run(it, T3 + "T(2,:) = []; h = height(T); T(:,'s') = []; w = width(T);")
    assert val(it, "h") == 2 and val(it, "w") == 2
    run(it, "T.Properties.VariableNames")
    np.testing.assert_array_equal(val(it, "T").variable(0), [[3], [2]])


def test_append_row_with_cell_and_table(it):
    run(it, T3 + "T(end+1,:) = {5,'z',50}; h = height(T); x = T.n(4);"
        "T(5,:) = table(6,{'y'},60,'VariableNames',{'n','s','m'});"
        "m = T.m(5);")
    assert val(it, "h") == 4 and val(it, "x") == 5 and val(it, "m") == 60


def test_row_filter_with_mask(it):
    run(it, T3 + "U = T(T.n > 1, :); h = height(U); v = U.m;")
    assert val(it, "h") == 2
    np.testing.assert_array_equal(val(it, "v"), [[30], [20]])


def test_brace_assignment(it):
    run(it, T3 + "T{1,'m'} = 7; T{2:3,'n'} = [8;9]; a = T.m(1); b = T.n;")
    assert val(it, "a") == 7
    np.testing.assert_array_equal(val(it, "b"), [[3], [8], [9]])


def test_properties_assignment(it):
    run(it, T3 + "T.Properties.VariableNames = {'a','b','c'}; x = T.c(1);")
    assert val(it, "x") == 30


def test_row_names(it):
    run(it, "T = table([1;2],[3;4],'RowNames',{'r1','r2'},"
            "'VariableNames',{'a','b'}); x = T('r2','b').b; y = T.Properties.RowNames;")
    assert val(it, "x") == 4 and list(val(it, "y")) == ["r1", "r2"]


def test_size_functions_and_display(it):
    out = run(it, T3 + "s = size(T); T")
    np.testing.assert_array_equal(val(it, "s"), [3, 3])
    assert "3×3 table" in out and "{'a'}" in out


# ── sorting, sets, joins ──────────────────────────────────────

def test_sortrows_matrix_columns_and_direction(it):
    run(it, "A = [3 1; 1 2; 3 0; 1 1]; B = sortrows(A, [1 -2]);"
            "[C, ix] = sortrows(A, 2);")
    np.testing.assert_array_equal(val(it, "B"), [[1, 2], [1, 1], [3, 1], [3, 0]])
    np.testing.assert_array_equal(val(it, "C"), [[3, 0], [3, 1], [1, 1], [1, 2]])
    np.testing.assert_array_equal(val(it, "ix").reshape(-1), [3, 1, 4, 2])


def test_sortrows_table_ties_keep_order(it):
    run(it, "T = table([2;1;2;1],[1;2;3;4],'VariableNames',{'a','b'});"
            "U = sortrows(T,'a'); V = sortrows(T,'a','descend');")
    np.testing.assert_array_equal(val(it, "U").variable(1), [[2], [4], [1], [3]])
    np.testing.assert_array_equal(val(it, "V").variable(1), [[1], [3], [2], [4]])


def test_sortrows_text_variable(it):
    run(it, T3 + "U = sortrows(T, 's'); a = U.m;")
    np.testing.assert_array_equal(val(it, "a"), [[10], [20], [30]])


def test_unique_rows_of_a_table(it):
    run(it, "T = table([1;2;1;2],[5;6;5;7],'VariableNames',{'a','b'});"
            "[U, ia, ic] = unique(T); h = height(U);")
    assert val(it, "h") == 3
    np.testing.assert_array_equal(val(it, "ic").reshape(-1), [1, 2, 1, 3])


JOIN = ("A = table([1;2;1],[5;6;7],'VariableNames',{'k','v'});"
        "B = table([1;2],{'p';'q'},'VariableNames',{'k','w'});")


def test_innerjoin_and_join(it):
    run(it, JOIN + "C = innerjoin(A,B); D = join(A,B);")
    C, D = val(it, "C"), val(it, "D")
    np.testing.assert_array_equal(C.variable(0), [[1], [1], [2]])
    np.testing.assert_array_equal(C.variable(1), [[5], [7], [6]])
    assert list(C.variable(2)) == ["p", "p", "q"]
    np.testing.assert_array_equal(D.variable(1), [[5], [6], [7]])


def test_join_needs_every_key(it):
    run(it, "A = table([1;3],'VariableNames',{'k'});"
            "B = table([1;2],'VariableNames',{'k'});")
    assert "appear in the second" in error_of(it, "join(A,B)")


def test_outerjoin_merged_keys(it):
    run(it, "A = table([1;2],[5;6],'VariableNames',{'k','v'});"
            "B = table([2;3],[8;9],'VariableNames',{'k','w'});"
            "C = outerjoin(A,B,'Keys','k','MergeKeys',true);")
    C = val(it, "C")
    np.testing.assert_array_equal(C.variable(0), [[1], [2], [3]])
    v, w = C.variable(1).reshape(-1), C.variable(2).reshape(-1)
    assert v[0] == 5 and v[1] == 6 and math.isnan(v[2])
    assert math.isnan(w[0]) and w[1] == 8 and w[2] == 9


# ── groups ────────────────────────────────────────────────────

def test_groupsummary_sum_and_mean(it):
    run(it, "T = table([2;1;2;1],[1;2;3;4],'VariableNames',{'g','v'});"
            "S = groupsummary(T,'g','mean','v');")
    S = val(it, "S")
    assert S.columns == ["g", "GroupCount", "mean_v"]
    np.testing.assert_array_equal(S.variable(0), [[1], [2]])
    np.testing.assert_array_equal(S.variable(2), [[3], [2]])


def test_varfun_and_rowfun(it):
    run(it, "T = table([1;2;3],[4;5;6],'VariableNames',{'a','b'});"
            "V = varfun(@sum, T); R = rowfun(@(a,b) a*b, T);")
    V, R = val(it, "V"), val(it, "R")
    assert V.columns == ["sum_a", "sum_b"]
    assert V.variable(0) == 6 and V.variable(1) == 15
    np.testing.assert_array_equal(R.variable(0), [[4], [10], [18]])


def test_findgroups_splitapply(it):
    run(it, "g = findgroups([3;1;3;2]); s = splitapply(@sum, [1;2;3;4], g);")
    np.testing.assert_array_equal(val(it, "g").reshape(-1), [3, 1, 3, 2])
    np.testing.assert_array_equal(val(it, "s").reshape(-1), [2, 4, 4])


def test_head_tail_vertcat_and_variables(it):
    run(it, T3 + "h = head(T,2); t = tail(T,1); U = [T; T]; n = height(U);"
        "V = removevars(T,'s'); W = addvars(T,[1;2;3],'NewVariableNames',{'q'});"
        "X = renamevars(T,'n','nn');")
    assert val(it, "h").height == 2 and val(it, "t").height == 1
    assert val(it, "n") == 6
    assert val(it, "V").columns == ["n", "m"]
    assert val(it, "W").columns == ["n", "s", "m", "q"]
    assert val(it, "X").columns[0] == "nn"


def test_summary_prints_stats(it):
    out = run(it, "summary(table([1;2;6],'VariableNames',{'x'}))")
    assert "Min          1" in out and "Median       2" in out \
        and "Max          6" in out


# ── datetime ──────────────────────────────────────────────────

def test_datetime_components_and_rollover(it):
    run(it, "t = datetime(2024,13,35,10,20,30); y = year(t); m = month(t);"
            "d = day(t); h = hour(t); mi = minute(t); s = second(t);")
    # month 13 is January 2025; day 35 of it is 4 February
    assert [val(it, k) for k in ("y", "m", "d", "h", "mi", "s")] == \
        [2025, 2, 4, 10, 20, 30]


def test_datetime_display_and_format(it):
    out = run(it, "t = datetime(2024,1,15)")
    assert "t = 15-Jan-2024" in out
    out = run(it, "t = datetime(2024,1,15,13,5,9)")
    assert "15-Jan-2024 13:05:09" in out
    run(it, "t.Format = 'yyyy-MM-dd'; x = char(t);")
    assert val(it, "x") == "2024-01-15"


def test_datetime_arithmetic(it):
    run(it, "t = datetime(2024,2,28); u = t + days(2); d = datetime(2024,3,1) - t;"
            "n = days(d); h = hours(d); v = t + 1;")
    assert (val(it, "u").Month, val(it, "u").Day) == (3, 1)   # leap year
    assert val(it, "n") == 2 and val(it, "h") == 48
    assert val(it, "v").Day == 29


def test_calendar_month_clipping(it):
    run(it, "t = datetime(2024,1,31) + calmonths(1); a = month(t); b = day(t);"
            "u = datetime(2024,2,29) + calyears(1); c = day(u);")
    assert (val(it, "a"), val(it, "b")) == (2, 29)
    assert val(it, "c") == 28


def test_between_and_comparisons(it):
    run(it, "a = datetime(2024,1,15); b = datetime(2024,3,1,10,30,0);"
            "c = between(a,b); r = a + c; ok = r == b; lt = a < b; "
            "q = a == datetime('2024-01-15');")
    assert val(it, "ok") is True or val(it, "ok") == True  # noqa: E712
    assert val(it, "lt") and val(it, "q")
    assert repr(val(it, "c")).startswith("1mo 15d")


def test_datetime_vectors_sort_diff_min(it):
    run(it, "t = datetime(2024,1,1) + days([5 1 3]); s = sort(t); m = min(t);"
            "M = max(t); d = diff(s); x = days(d);")
    assert val(it, "s").Day.tolist() == [2, 4, 6]
    assert val(it, "m").Day == 2 and val(it, "M").Day == 6
    np.testing.assert_array_equal(np.ravel(val(it, "x")), [2, 2])


def test_datetime_from_text_and_numbers(it):
    run(it, "t = datetime('15/01/2024 08:30','InputFormat','dd/MM/yyyy HH:mm');"
            "h = hour(t); mi = minute(t); u = datetime(739000,'ConvertFrom','datenum');"
            "n = datenum(u);")
    assert val(it, "h") == 8 and val(it, "mi") == 30
    assert val(it, "n") == 739000


def test_dateshift_and_weekday(it):
    run(it, "t = datetime(2024,5,17,13,0,0); a = dateshift(t,'start','month');"
            "b = dateshift(t,'end','month'); [n, s] = weekday(t);")
    assert val(it, "a").Day == 1 and val(it, "b").Day == 31
    assert val(it, "n") == 6 and val(it, "s") == "Fri"      # a Friday


def test_nat_and_isnat(it):
    run(it, "x = NaT; b = isnat(x);")
    assert val(it, "b")


# ── duration ──────────────────────────────────────────────────

def test_duration_display_and_units(it):
    out = run(it, "d = duration(1,30,5)")
    assert "d = 01:30:05" in out
    assert "d = 1.5 hr" in run(it, "d = hours(1.5)")
    assert "5 sec" in run(it, "d = seconds(5)")
    run(it, "x = minutes(hours(2)); r = hours(3) / hours(2); "
            "s = seconds(hours(1) + minutes(30));")
    assert val(it, "x") == 120 and val(it, "r") == 1.5
    assert val(it, "s") == 5400


def test_duration_from_text_and_compare(it):
    run(it, "d = duration('02:30:00'); h = hours(d); lt = d < hours(3);"
            "e = d == hours(2.5);")
    assert val(it, "h") == 2.5 and val(it, "lt") and val(it, "e")


def test_duration_reductions(it):
    run(it, "d = hours([1 2 3]); s = hours(sum(d)); m = hours(mean(d));"
            "mx = hours(max(d)); a = hours(abs(-d(1)));")
    assert (val(it, "s"), val(it, "m"), val(it, "mx"), val(it, "a")) == \
        (6, 2, 3, 1)


def test_classes_and_questions(it):
    run(it, "a = class(datetime(2024,1,1)); b = class(hours(1)); "
            "c = class(table(1)); d = isdatetime(hours(1));"
            "e = class(timetable(hours(1),2));")
    assert (val(it, "a"), val(it, "b"), val(it, "c"), val(it, "e")) == \
        ("datetime", "duration", "table", "timetable")
    assert not val(it, "d")


def test_datetime_table_variable(it):
    run(it, "t = datetime(2024,1,1) + days([0;1;2]);"
            "T = table(t, [5;6;7], 'VariableNames', {'when','v'});"
            "U = T(T.when > datetime(2024,1,1), :); h = height(U);"
            "V = sortrows(T, 'when', 'descend'); x = V.v(1);")
    assert val(it, "h") == 2 and val(it, "x") == 7


# ── timetable ─────────────────────────────────────────────────

TT = ("t = datetime(2024,1,1) + days((0:4)');"
      "TT = timetable(t, (10:10:50)', (1:5)', 'VariableNames', {'a','b'});")


def test_timetable_basics(it):
    out = run(it, TT + "s = size(TT); h = height(TT); c = TT.Time(2);"
              "TT(1:2,:)")
    np.testing.assert_array_equal(val(it, "s"), [5, 2])
    assert val(it, "h") == 5 and val(it, "c").Day == 2
    assert "Time" in out and "02-Jan-2024" in out


def test_timetable_indexing_by_time(it):
    run(it, TT + "A = TT(timerange(t(2), t(4)), :); B = TT(timerange(t(2), t(4), 'closed'), :);"
        "C = TT(t(3), 'a'); D = TT(TT.Time > t(3), :);"
        "ha = height(A); hb = height(B); ca = C.a; hd = height(D);")
    assert val(it, "ha") == 2 and val(it, "hb") == 3
    assert val(it, "ca") == 30 and val(it, "hd") == 2


def test_timetable_conversions(it):
    run(it, TT + "T = timetable2table(TT); w = width(T); n = T.Properties.VariableNames;"
        "U = table2timetable(T); c = class(U); d = height(U);")
    assert val(it, "w") == 3 and list(val(it, "n"))[0] == "Time"
    assert val(it, "c") == "timetable" and val(it, "d") == 5


def test_timetable_with_duration_times_and_sort(it):
    run(it, "TT = timetable(hours([3;1;2]), [30;10;20]);"
            "S = sortrows(TT); x = S.Var1; c = S.Time(1);")
    np.testing.assert_array_equal(val(it, "x"), [[10], [20], [30]])
    assert val(it, "c").a[0, 0] == 3600.0


# ── fitlm ─────────────────────────────────────────────────────

def test_fitlm_exact_line(it):
    run(it, "x = [1;2;3;4]; y = 2*x + 1; m = fitlm(x, y);"
            "b = m.Coefficients.Estimate; r2 = m.Rsquared.Ordinary;"
            "p = predict(m, [5;6]);")
    np.testing.assert_allclose(val(it, "b").reshape(-1), [1, 2], atol=1e-10)
    assert val(it, "r2") == pytest.approx(1.0)
    np.testing.assert_allclose(val(it, "p").reshape(-1), [11, 13], atol=1e-9)


def test_fitlm_statistics_by_hand(it):
    # y = [1 2 2 4] on x = 1..4:  slope 0.9, intercept 0, SSE 0.7 ... worked
    # with the normal equations: Sxx = 5, Sxy = 4.5 (centred), so slope 0.9.
    run(it, "m = fitlm([1;2;3;4], [1;2;2;4]); b = m.Coefficients.Estimate;"
            "dfe = m.DFE; rmse = m.RMSE;")
    np.testing.assert_allclose(val(it, "b").reshape(-1), [0.0, 0.9],
                               atol=1e-12)
    sse = ((np.array([1, 2, 2, 4]) - 0.9 * np.arange(1, 5)) ** 2).sum()
    assert val(it, "dfe") == 2
    assert val(it, "rmse") == pytest.approx(math.sqrt(sse / 2))


def test_fitlm_table_formula_and_display(it):
    out = run(it, "T = table([1;2;3;4],[2;1;4;3],[3.1;3.9;7.2;7.8],"
                  "'VariableNames',{'u','v','y'});"
                  "m = fitlm(T,'y ~ u + v'); n = m.NumObservations;"
                  "names = m.Coefficients.Properties.RowNames; m")
    assert val(it, "n") == 4
    assert list(val(it, "names")) == ["(Intercept)", "u", "v"]
    assert "R-squared" in out and "Estimated Coefficients" in out
