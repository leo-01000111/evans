"""
The side panel on its own (R2): tabs, holders, open and closed, width.

The window's use of it (one per workspace, Cedric moving between them, the
layout keys) is in ``test_ui_layout.py`` and ``test_cedric_ui.py``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QWidget

from evans.ui.side_panel import SidePanel, page_with_panel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _settle(app, rounds: int = 10) -> None:
    for _ in range(rounds):
        app.processEvents()


def test_tabs_have_keys_titles_and_holders(app):
    panel = SidePanel("test")
    label = QLabel("inside")
    holder = panel.add_tab("one", "One", label)
    panel.add_tab("two", "Two")
    assert panel.keys == ("one", "two")
    assert panel.title("two") == "Two"
    assert panel.holder("one") is holder and holder.isAncestorOf(label)
    assert panel.current == "one"
    with pytest.raises(ValueError):
        panel.add_tab("one", "Again")


def test_every_page_scrolls(app):
    """Word-wrapped text gets taller as it narrows: it must not push."""
    panel = SidePanel()
    holder = panel.add_tab("one", "One")
    assert isinstance(holder.parentWidget().parentWidget(), QScrollArea)
    scroll = holder.parentWidget().parentWidget()
    assert scroll.widgetResizable()


def test_set_current_emits_and_ignores_unknown_keys(app):
    panel = SidePanel()
    panel.add_tab("one", "One")
    panel.add_tab("two", "Two")
    seen = []
    panel.tab_changed.connect(seen.append)
    panel.set_current("two")
    panel.set_current("an older build's tab")
    assert panel.current == "two" and seen == ["two"]


def test_a_widget_moves_between_holders(app):
    first, second = SidePanel(), SidePanel()
    a = first.add_tab("cedric", "Cedric")
    b = second.add_tab("cedric", "Cedric")
    moving = QWidget()
    a.layout().addWidget(moving)
    b.layout().addWidget(moving)
    assert moving.parentWidget() is b
    assert a.layout().count() == 0


def test_open_and_closed_are_its_own_state(app):
    """Not isHidden(): a child counts as hidden until its window shows."""
    panel = SidePanel()
    assert panel.is_open
    states = []
    panel.toggled.connect(states.append)
    panel.set_open(False)
    panel.set_open(False)
    panel.set_open(True)
    assert states == [False, True]
    assert panel.is_open and not panel.isHidden()


def test_the_close_button_closes_it(app):
    page = page_with_panel(QWidget(), panel := SidePanel())
    page.resize(900, 400)
    page.show()
    _settle(app)
    assert panel.isVisible()
    assert panel._close.accessibleName() and panel._close.toolTip()
    panel._close.click()
    assert not panel.is_open and not panel.isVisible()
    page.close()


def test_width_default_minimum_and_restore(app):
    content = QWidget()
    panel = SidePanel()
    page = page_with_panel(content, panel)
    page.resize(1000, 400)
    page.show()
    _settle(app)
    assert panel.minimumWidth() == SidePanel.MINIMUM_WIDTH == 240
    assert panel.width() == SidePanel.DEFAULT_WIDTH == 320
    panel.set_preferred_width(100)                     # below the minimum
    assert panel.preferred_width == 240
    panel.set_preferred_width(400)
    _settle(app)
    assert panel.width() == 400
    panel.set_open(False)
    _settle(app)
    assert content.width() > 900
    panel.set_open(True)
    _settle(app)
    assert panel.width() == 400                         # came back as it was
    page.close()


def test_a_dragged_width_is_kept(app):
    content = QWidget()
    panel = SidePanel()
    page = page_with_panel(content, panel)
    page.resize(1000, 400)
    page.show()
    _settle(app)
    page.moveSplitter(1000 - 360 - page.handleWidth(), 1)   # as a drag does
    _settle(app)
    assert panel.preferred_width == panel.width()
    assert abs(panel.preferred_width - 360) <= 2
    page.close()


def test_a_tab_can_go_before_another_and_be_removed_and_renamed(app):
    """R6 docks a scope as a tab in front of Cedric, and takes it out again."""
    panel = SidePanel()
    panel.add_tab("one", "One")
    panel.add_tab("cedric", "Cedric")
    label = QLabel("scope")
    panel.add_tab("scope:a", "Scope: a", label, before="cedric")
    panel.add_tab("scope:b", "Scope: b", before="not a tab")     # last
    assert panel.keys == ("one", "scope:a", "cedric", "scope:b")
    assert panel._bar.tabText(1) == "Scope: a"
    panel.set_current("scope:a")
    panel.set_title("scope:a", "Scope: renamed")
    assert panel.title("scope:a") == "Scope: renamed"

    label.setParent(None)                          # keep the widget alive
    panel.remove_tab("scope:a")
    assert panel.keys == ("one", "cedric", "scope:b")
    assert panel.current in panel.keys
    assert panel._stack.count() == 3
    assert label.text() == "scope"
    panel.remove_tab("scope:a")                    # already gone: no error
