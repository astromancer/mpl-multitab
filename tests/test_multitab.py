# std
import sys

# third-party
import numpy as np

# local
from mpl_multitab import MplTabs, QtWidgets

#
sys.modules['matplotlib.pyplot'] = None


def test_simple_tabs(n=100, colours='rgb'):
    # Example use for MplTabs
    # Create a scatter plot of `n` random xy-points for each colour
    ui = MplTabs()
    for c in colours:
        fig = ui.add_tab(c)
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c)

    ui.set_focus(0)
    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = test_simple_tabs()
    ui.show()
    sys.exit(app.exec_())
