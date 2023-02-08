
# std
import sys
import itertools as itt
from collections import defaultdict

# third-party
import numpy as np
from matplotlib.figure import Figure
from mpl_multitab import MplMultiTab, QtWidgets


#
sys.modules['matplotlib.pyplot'] = None


COLOURS = 'rgb'
MARKERS = 'd*P'
HATCH = ('xxx', 'ooo')


def test_nd(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # Example use for MplTabs2D
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.

    ui = MplMultiTab()

    for c, m, h in itt.product(colours, markers, hatch):
        fig = ui.add_tab(f'Colour {c.upper()}', f'Marker {m}', f'Hatch {h}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), edgecolor=c, marker=m, hatch=h,
                   s=750, facecolor='none')
    
    ui.link_focus()
    ui.set_focus(0, 0, 0)
    # from IPython import embed
    # embed(header="Embedded interpreter at 'tests/test_multitab_nested.py':36")
    assert np.equal([tuple(q._current_index()) for q in ui], 0).all()
    
    return ui


def test_delay_plot(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # Example use for MplTabs2D
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.

    ui = MplMultiTab()

    for c, m, h in itt.product(colours, markers, hatch):
        fig = ui.add_tab(f'Colour {c.upper()}', f'Marker {m}', f'Hatch {h}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), edgecolor=c, marker=m, hatch=h,
                   s=750, facecolor='none')
    
    ui.link_focus()
    ui.set_focus(0, 0, 0)
    return ui

def test_figures_predef(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # Example use for MplTabs2D
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.

    figures = defaultdict(lambda: defaultdict(dict))
    for c, m, h in itt.product(colours, markers, hatch):
        fig = Figure()
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), edgecolor=c, marker=m, hatch=h,
                   s=750, facecolor='none')
        figures[f'Colour {c.upper()}'][f'Marker {m}'][f'Hatch {h}'] = fig
    
    ui.link_focus()
    return MplMultiTab(figures)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = test_nd()
    # ui = test_figures_predef()
    ui.show()
    sys.exit(app.exec_())
