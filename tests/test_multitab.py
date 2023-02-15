

# std
import operator as op, sys
import itertools as itt
from collections import defaultdict

# third-party
import pytest
import numpy as np
from matplotlib.figure import Figure
from mpl_multitab import MplMultiTab, MplTabs, QtCore, examples, QtWidgets


# ---------------------------------------------------------------------------- #
FEATURES = dict(
    color='rgb',
    marker='H*P',
    hatch=('xx', '**')
)
STYLE = dict(
    s=750,
    facecolor='none'
)
STRUCT = {
    1: (dict, ()),
    2: (defaultdict, dict),
    3: (defaultdict, lambda: defaultdict(dict))
    # dict, defaultdict
}


# ---------------------------------------------------------------------------- #

@pytest.fixture(params=range(1, 4))
def level(request):
    return request.param


def get_example(level, name):
    return op.attrgetter(f'_{level}d.example_{name}')(examples)
    #  getattr(examples, f'_{level}d').example_delay_draw()


def generate_features(level):
    features = dict(tuple(FEATURES.items())[:level])
    for values in itt.product(*features.values()):
        yield dict(zip(features.keys(), values))


def generate_datasets(level, n=100):
    for kws in generate_features(level):
        yield kws, np.random.randn(2, n)


def create_figures(level):
    kls, args = STRUCT[level]
    figures = kls(args)
    for kws, data in generate_datasets(level):
        struct = figures
        *values, leaf = kws.values()
        for v in values:
            struct = struct[v]

        struct[leaf] = fig = Figure()
        ax = fig.subplots()
        ax.scatter(*data, **kws, **STYLE)

    return figures


# ---------------------------------------------------------------------------- #


def _change_tab(qtbot, mgr, i):
    # simulate tab change through mouse interaction
    if i == mgr._current_index():
        return

    tabs = mgr.tabs
    bar = tabs.tabBar()
    with qtbot.waitSignal(tabs.currentChanged, timeout=1000):
        qtbot.mouseClick(bar, QtCore.Qt.LeftButton,
                         pos=bar.tabRect(i + mgr.index_offset).center())


def _test_cycle_tabs(qtbot, ui, check=lambda: ()):
    # cycle through the tabs, check figure draws
    *branch, _ = ui.tabs._active_branch()
    shape = map(len, branch)
    itr = itt.product(*map(range, shape))
    start = next(itr)

    # check figure (0, ...) already drawn
    with qtbot.waitActive(ui):
        check(ui, start)  # check canvas drawn before any tab change

    # cycle through the tabs, check figure draws
    for indices in itr:
        mgr = ui.tabs
        for i in indices:
            # switch tab
            _change_tab(qtbot, mgr, i)
            mgr = mgr[i]

        # check canvas drawn
        check(ui, indices)

# ---------------------------------------------------------------------------- #
# Test init with predefined figures


def check_indices(ui, indices):
    assert ui[indices]._index() == indices


def test_figures_predefined(qtbot, level):
    #
    ui = MplMultiTab(create_figures(level))
    ui.show()

    # register ui
    qtbot.addWidget(ui)

    # test
    _test_cycle_tabs(qtbot, ui, check_indices)


# ---------------------------------------------------------------------------- #
# Test delayed plot

def _plot(fig, indices, n=10):
    kws = {key: vals[i] for i, (key, vals) in zip(indices, FEATURES.items())}
    return fig.subplots().scatter(*np.random.randn(2, n), **kws, **STYLE)


def check_figure_drawn(ui, indices):
    assert ui[indices]._drawn


def test_delay_draw(qtbot, level):
    #
    kls = MplTabs if level == 1 else MplMultiTab
    ui = kls()
    
    for kws in generate_features(level):
        ui.add_tab(*kws.values())
    
    ui.add_callback(_plot)      # add plot worker
    ui.set_focus(*([0] * level))   # trigger the plotting for [group 0, ...] tab 0
    ui.link_focus()            # keep same tab in focus across group switches
    ui.show()
    # return ui
    
    # register ui
    qtbot.addWidget(ui)

    # test
    _test_cycle_tabs(qtbot, ui, check_figure_drawn)




