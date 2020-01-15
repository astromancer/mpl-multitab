from matplotlib import pylab as plt
from superplot.multitab import MplMultiTab
import numpy as np

fig, ax = plt.subplots()
ax.plot( np.random.randn(100,2), 'mp' )

fig2, ax2 = plt.subplots()
ax2.plot( np.random.randn(100,2), 'bx' )

ui = MplMultiTab( None, [fig], [] )
ui.show()