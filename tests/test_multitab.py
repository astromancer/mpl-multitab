from matplotlib import pylab as plt
from scrawl.multitab import MplMultiTab
import numpy as np

fig, ax = plt.subplots()
ax.plot(np.random.randn(100, 2), 'mp')

fig2, ax2 = plt.subplots()
ax2.plot(np.random.randn(100, 2), 'bx')

ui = MplMultiTab(None, [fig], [])
# ui.show()


import numpy as np

# Example use
colours = 'rgb'
figures, labels = [], []
for i in range(3):
    fig, ax = plt.subplots()
    ax.plot(np.random.randn(100), colours[i])
    figures.append(fig)
    labels.append('Tab %i' % i)

# app = QtWidgets.QApplication(sys.argv)
ui = MplMultiTab(figures=figures, labels=labels)
# ui.show()
# from IPython import embed
# embed()
# sys.exit(app.exec_())

# main()

# # FIXME: doesn't seem to work!!
# # import numpy as np
# from matplotlib import cm
#
# # Example use
# r, c, N = 4, 3, 100
# colours = iter(cm.spectral(np.linspace(0, 1, r * c)))
# figures = []
# row_labels, col_labels = [], []
# for i in range(r):
#     for j in range(c):
#         fig, ax = plt.subplots()
#         ax.plot(np.random.randn(N), color=next(colours))
#         figures.append(fig)
#
# row_labels = ['Row %i' % i for i in range(r)]
# col_labels = ['Col %i' % i for i in range(c)]
# labels = row_labels, col_labels
#
# app = QtGui.QApplication(sys.argv)
# ui = MplMultiTab2D(figures, labels, shape=(r, c))
# ui.show()
# sys.exit(app.exec_())