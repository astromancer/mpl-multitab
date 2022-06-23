
# std
import sys
import itertools as itt

# third-party
import numpy as np

# local
from mpl_multitab import MplMultiTab2D, QtWidgets

#
sys.modules['matplotlib.pyplot'] = None


def test_multitab_2d(n=100, colours='rgb', markers='123'):
    # Example use for MplMultiTab2D
    # This dataset is equal number observations per dataset. This need not be the
    # case in general.
    
    ui = MplMultiTab2D()

    for c, m in itt.product(colours, markers):
        fig = ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')
        ax = fig.subplots()
        ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')

    return ui


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = test_multitab_2d()
    ui.show()
    sys.exit(app.exec_())
