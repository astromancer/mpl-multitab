
# std
import sys
import itertools as itt

# third-party
import numpy as np

# local
from mpl_multitab import QtWidgets, MplMultiTab

# ensure we don't use pyplot
sys.modules['matplotlib.pyplot'] = None


def example_2d(n=100, colours='rgb', markers='123'):
    # Example use for MplTabs2D
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.

    ui = MplMultiTab(pos='W')

    for c, m in itt.product(colours, markers):
        fig = ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')

    ui.link_focus()
    ui.set_focus(0, 0)

    return ui


# def test_2d(qtbot):
#     ui = example_2d()
#     ui.show()
#     # register ui
#     qtbot.addWidget(ui)


def example_delay_draw(n=10_000, colours='rgb', markers='123'):

    #
    ui = MplMultiTab()
    # first create the figures, but don't do the plotting just yet
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

    ui.link_focus()         # link focus tabs between groups
    ui.add_callback(plot)   # add our worker
    ui.set_focus(0, 0)      # this will trigger the plotting for group 0 tab 0
    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = example_2d()
    # ui = test_delay_draw()
    ui.show()
    sys.exit(app.exec_())
