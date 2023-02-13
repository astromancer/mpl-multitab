# std
import sys

# third-party
import numpy as np

# local
from mpl_multitab import MplTabs, QtWidgets

# ---------------------------------------------------------------------------- #
# ensure we don't use pyplot
sys.modules['matplotlib.pyplot'] = None

COLOURS = 'rgb'

# ---------------------------------------------------------------------------- #


def example_1d(n=100, colours=COLOURS):
    # Example use of MplTabs
    # Create a scatter plot of `n` random xy-points for each colour
    ui = MplTabs()
    for c in colours:
        fig = ui.add_tab(c)
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c)

    ui.set_focus(0)
    return ui


def example_delay_draw(n=10_000, colours=COLOURS):
    #
    # first create the figures, but don't do the plotting just yet
    ui = MplTabs()
    for c in colours:
        ui.add_tab(c)

    # create plotting function
    def plot(fig, indices):
        i, = indices
        print('Doing plot:', i)
        ax = fig.subplots()
        return ax.scatter(*np.random.randn(2, n), color=colours[i])

    ui.add_callback(plot)   # add your plot worker
    ui.set_focus(0)         # this will trigger the plotting for group 0 tab 0
    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = example_delay_draw()
    ui.show()
    sys.exit(app.exec_())
