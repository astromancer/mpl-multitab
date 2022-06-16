
# std
import sys
import itertools as itt

# third-party
import numpy as np

# local
from mpl_multitab import MplMultiTab2D, QtWidgets

sys.modules['matplotlib.pyplot'] = None

# Example use

# This dataset is equal number observations per dataset. This need not be the
# case in general.
app = QtWidgets.QApplication(sys.argv)
ui = MplMultiTab2D()

n = 100
colours = 'rgb'
markers = '123'
for c, m in itt.product(colours, markers):
    fig = ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')
    ax = fig.subplots()
    ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')

ui.show()

if __name__ == '__main__':
    sys.exit(app.exec_())
