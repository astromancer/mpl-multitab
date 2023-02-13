
# std
import itertools as itt

# third-party
import pytest
from mpl_multitab import QtCore, examples


@pytest.fixture(params=['1', '2', 'n'])
def example(request):
    # runs through the example gallery
    return getattr(examples, f'_{request.param}d')


def _change_tab(qtbot, mgr, i):
    # simulate tab change through mouse interaction
    if i == mgr._current_index():
        return

    tabs = mgr.tabs
    bar = tabs.tabBar()
    with qtbot.waitSignal(tabs.currentChanged, timeout=1000):
        qtbot.mouseClick(bar, QtCore.Qt.LeftButton,
                         pos=bar.tabRect(i + mgr.index_offset).center())


def _test_cycle_tabs(qtbot, ui):
    # cycle through the tabs, check figure draws
    *branch, _ = ui.tabs._active_branch()
    shape = map(len, branch)
    itr = itt.product(*map(range, shape))
    start = next(itr)  # already done above

    # check figure (0, ...) already drawn
    with qtbot.waitActive(ui):
        assert ui[start]._drawn

    # cycle through the tabs, check figure draws
    for indices in itr:
        mgr = ui.tabs
        for i in indices:
            # switch tab
            _change_tab(qtbot, mgr, i)
            mgr = mgr[i]

        # check canvas drawn
        assert ui[indices]._drawn


@pytest.fixture
def cycle_tabs():
    # this "fixture" returns the generic test
    return _test_cycle_tabs
