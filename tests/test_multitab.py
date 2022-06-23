# std
import sys

# third-party
import numpy as np

# local
from mpl_multitab import MplMultiTab, QtWidgets

#
sys.modules['matplotlib.pyplot'] = None


def test_multitab(n=100, colours='rgb'):
    # Example use for MplMultiTab
    # Create a scatter plot of `n` random xy-points for each colour
    ui = MplMultiTab()
    for c in colours:
        fig = ui.add_tab(c)
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c)

    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = test_multitab()
    ui.show()
    sys.exit(app.exec_())
