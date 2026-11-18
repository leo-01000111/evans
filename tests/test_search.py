"""The palette's matching and ordering (Qt-free)."""

from __future__ import annotations

from enum import Enum

from evans.ui.search import LIMIT, RECENT_LIMIT, Entry, rank, remember, score


class W(str, Enum):
    A = "Analyse"
    M = "Model"
    C = "Console"


def entry(id_, title, workspace=None, keywords=()):
    return Entry(id_, title, "Test", workspace, "", tuple(keywords))


def titles(entries):
    return [e.title for e in entries]


# ── score ──

def test_empty_query_matches_everything_with_zero():
    assert score("", "anything") == 0.0
    assert score("   ", "") == 0.0


def test_no_match_is_none():
    assert score("xyz", "Bode") is None
    assert score("edob", "Bode") is None          # the letters, but not in order
    assert score("bodee", "Bode") is None         # more letters than the text has


def test_subsequence_and_case():
    assert score("bod", "Bode") is not None
    assert score("BOD", "bode") is not None
    assert score("svas", "Save as…") is not None
    assert score("sa", "Save as…") is not None


def test_start_beats_middle():
    assert score("bo", "Bode") > score("bo", "Show Bode")


def test_word_starts_beat_scattered_letters():
    assert score("sa", "Save as") > score("sa", "Disable")
    assert score("ss", "Save session") > score("ss", "Assess")


def test_consecutive_beats_split():
    assert score("step", "Step response") > score("step", "Show the pole")


def test_shorter_text_wins_on_a_tie():
    assert score("bode", "Bode") > score("bode", "Bode and more words")


# ── rank ──

def test_group_order_current_then_global_then_other():
    entries = [
        entry("m", "Gain model", W.M),
        entry("g", "Gain global"),
        entry("a", "Gain analyse", W.A),
    ]
    assert titles(rank(entries, "gain", W.A)) == [
        "Gain analyse", "Gain global", "Gain model"]
    assert titles(rank(entries, "gain", W.M)) == [
        "Gain model", "Gain global", "Gain analyse"]


def test_a_better_match_wins_inside_a_group_not_across():
    entries = [
        entry("a", "Show the gain somewhere", W.A),
        entry("m", "Gain", W.M),
    ]
    # The exact title is in the other workspace: still after the current one.
    assert titles(rank(entries, "gain", W.A)) == ["Show the gain somewhere", "Gain"]
    group = [entry("1", "Gain staging", W.A), entry("2", "Gain", W.A)]
    assert titles(rank(group, "gain", W.A)) == ["Gain", "Gain staging"]


def test_recency_breaks_ties_then_title():
    entries = [entry("x", "Alpha"), entry("y", "Beta"), entry("z", "Gamma")]
    # No query letters favour any of them: the same text length and the
    # same keyword, so only recency and then title decide.
    same = [Entry(i, t, "S", None, "", ("zzz",)) for i, t in
            (("x", "Alpha"), ("y", "Beta"), ("z", "Gamma"))]
    assert titles(rank(same, "zz", None)) == ["Alpha", "Beta", "Gamma"]
    assert titles(rank(same, "zz", None, ["z", "y"])) == [
        "Gamma", "Beta", "Alpha"]
    assert len(entries) == 3


def test_keywords_match_too():
    entries = [Entry("p", "Plant preset", "Analyse", None, "", ("bode",)),
               entry("o", "Other")]
    assert titles(rank(entries, "bod", None)) == ["Plant preset"]


def test_no_match_returns_empty():
    assert rank([entry("a", "Bode")], "qqq", None) == []
    assert rank([], "a", None) == []


def test_bod_finds_bode_and_svas_finds_save_as():
    entries = [entry("a", "Show Bode"), entry("b", "Save as…"),
               entry("c", "Step response")]
    assert titles(rank(entries, "bod", None)) == ["Show Bode"]
    assert titles(rank(entries, "svas", None)) == ["Save as…"]


def test_empty_query_puts_recent_first_then_current_workspace():
    entries = [entry("g", "Global"), entry("m", "Model one", W.M),
               entry("a", "Analyse one", W.A), entry("r", "Remembered", W.M)]
    got = rank(entries, "", W.A, ["r"])
    assert titles(got) == ["Remembered", "Analyse one", "Global", "Model one"]


def test_at_most_fifty():
    entries = [entry(str(n), f"Item {n}") for n in range(120)]
    assert len(rank(entries, "", None)) == LIMIT == 50
    assert len(rank(entries, "item", None)) == 50


def test_remember_moves_to_front_and_caps():
    ids = [str(n) for n in range(RECENT_LIMIT)]
    got = remember(ids, "5")
    assert got[0] == "5" and got.count("5") == 1 and len(got) == RECENT_LIMIT
    got = remember(ids, "new")
    assert got[0] == "new" and len(got) == RECENT_LIMIT and "19" not in got
