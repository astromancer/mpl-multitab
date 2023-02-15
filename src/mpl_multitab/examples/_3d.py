
# std
import sys
import itertools as itt
from collections import defaultdict

# third-party
import numpy as np
from matplotlib.figure import Figure
from mpl_multitab import MplMultiTab, QtWidgets


# ---------------------------------------------------------------------------- #
# ensure we don't use pyplot
sys.modules['matplotlib.pyplot'] = None


COLOURS = 'rgb'
MARKERS = 'H*P'
HATCH = ('xx', '**')

# ---------------------------------------------------------------------------- #


def example_nd(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # MplMultiTab with 3 tab levels
    ui = MplMultiTab()
    for c, m, h in itt.product(colours, markers, hatch):
        # use "&" to tag letters for keyboard shortcuts which select the tab
        #   eg: using "&x" somewhere in the tab name means you can select it with "Alt+x"
        fig = ui.add_tab(f'Colour &{c.upper()}', f'Marker &{m}', f'Hatch &{h}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n),
                   s=750, marker=m, hatch=h,
                   edgecolor=c,  facecolor='none')

    ui.link_focus()             # keep same tab in focus across group switches
    ui.set_focus(0, 0, 0)
    return ui


def example_figures_predefined(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # MplMultiTab with 3 tab levels, initialised from a predefined collection
    # of figures that define the tab structure

    figures = defaultdict(lambda: defaultdict(dict))
    for c, m, h in itt.product(colours, markers, hatch):
        fig = Figure()
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n),
                   s=750, marker=m, hatch=h,
                   edgecolor=c,  facecolor='none')
        figures[f'Colour {c.upper()}'][f'Marker {m}'][f'Hatch {h}'] = fig

    return MplMultiTab(figures)


def example_delay_draw(n=10, colours=COLOURS, markers=MARKERS, hatch=HATCH):
    # MplMultiTab with 3 tab levels, delayed plotting

    ui = MplMultiTab()
    for c, m, h in itt.product(colours, markers, hatch):
        ui.add_tab(f'Colour {c.upper()}', f'Marker {m}', f'Hatch {h}')

    # create plotting function
    def plot(fig, indices):
        print('Doing plot:', indices)
        i, j, k = indices
        ax = fig.subplots()
        return ax.scatter(*np.random.randn(2, n),
                          s=750, marker=markers[j], hatch=hatch[k],
                          edgecolor=colours[i],  facecolor='none')

    ui.add_callback(plot)   # add your plot worker
    ui.set_focus(0, 0, 0)   # this will trigger the plotting for group 0 tab 0
    ui.link_focus()         # keep same tab in focus across group switches
    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # ui = example_nd()
    ui = example_delay_draw()
    # ui = example_figures_predefined()
    ui.show()
    sys.exit(app.exec_())
