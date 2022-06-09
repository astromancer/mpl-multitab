
# std
import sys
import itertools as itt

# third-party
import numpy as np
from matplotlib import pylab as plt

# local
from mpl_multitab import MplMultiTab2D, QtWidgets


# Example use

# This dataset is equal number observations per dataset. This need not be the
# case in general.
app = QtWidgets.QApplication(sys.argv)
ui = MplMultiTab2D()

n = 100
colours = 'rgb'
markers = '123'
for c, m in itt.product(colours, markers):
    fig, ax = plt.subplots()
    ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')
    ui.add_tab(fig, f'Dataset {c.upper()}', f'Observation {m}')
ui.show()

if __name__ == '__main__':
    sys.exit(app.exec_())
