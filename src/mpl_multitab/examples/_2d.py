
# std
import sys
import itertools as itt

# third-party
import numpy as np

# local
from mpl_multitab import QtWidgets, MplMultiTab

# ---------------------------------------------------------------------------- #
# ensure we don't use pyplot
sys.modules['matplotlib.pyplot'] = None


COLOURS = 'rgb'
MARKERS = '123'
# ---------------------------------------------------------------------------- #


def example_2d(n=100, colours=COLOURS, markers=MARKERS):
    # Example use for MplMultiTab for 2d collection of data sets
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.

    ui = MplMultiTab(pos='W')
    for c, m in itt.product(colours, markers):
        fig = ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')

    ui.set_focus(0, 0)
    ui.link_focus()
    return ui


def example_delay_draw(n=10_000, colours=COLOURS, markers=MARKERS):
    # MplMultiTab with delayed plotting

    # first create the figures, but don't do the plotting just yet
    ui = MplMultiTab(pos='W')
    for c, m in itt.product(colours, markers):
        ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')

    # create plotting function
    def plot(fig, indices):
        print('Doing plot:', indices)
        i, j = indices
        ax = fig.subplots()
        return ax.scatter(*np.random.randn(2, n),
                          color=colours[i],
                          marker=f'${markers[j]}$')

    ui.add_callback(plot)   # add your plot worker
    ui.set_focus(0, 0)      # this will trigger the plotting for group 0 tab 0
    ui.link_focus()         # keep same tab in focus across group switches
    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # ui = example_2d()
    ui = example_delay_draw()
    ui.show()
    sys.exit(app.exec_())
