"""
This script uses PyQt to create a gui which embeds matplotlib figures in a
simple tabbed window navigator.
"""

import sys
from six.moves import zip_longest  # python 2 compat

# from PyQt4 import QtCore
from matplotlib.backends.qt_compat import QtGui, QtCore, QtWidgets

from matplotlib import use

use('QT5Agg')

from matplotlib.backends.backend_qt5 import (
    FigureCanvasQT as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
from matplotlib import pyplot as plt

import numpy as np

# from PyQt5 import QtCore, QtGui, QtWidgets
SIGNAL = QtCore.Signal


# from decor import expose, profile

# __all__ = []

class MultiTabNavTool(QtWidgets.QWidget):
    def __init__(self, canvases, tabs, parent=None):
        """
        Create one navigation toolbar per tab, switching between them upon
        tab  change
        """
        QtWidgets.QWidget.__init__(self, parent)
        self.canvases = canvases
        self.tabs = tabs
        self.toolbars = [NavigationToolbar(canvas, parent) for canvas in
                         self.canvases]

        self.vbox = QtWidgets.QVBoxLayout()

        for toolbar in self.toolbars:
            self.add(toolbar)
        self.setLayout(self.vbox)

        # switch between toolbars when tab is changed
        self.tabs.currentChanged.connect(self.switch_toolbar)

    def add(self, canvas, parent):
        tool = NavigationToolbar(canvas, parent)
        self.toolbars.append(tool)
        self.vbox.addWidget(tool)
        tool.setVisible(False)

    def switch_toolbar(self):
        # print('Hello1')
        for toolbar in self.toolbars:
            toolbar.setVisible(False)
        # print('Hello2')
        self.toolbars[self.tabs.currentIndex()].setVisible(True)
        # print('Hello3')


class MplMultiTab(QtWidgets.QMainWindow):

    def __init__(self, parent=None, figures=(), labels=(), title=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        title = title or 'MplMultiTab'
        self.setWindowTitle(title)

        #
        self.canvases = []

        self.main_frame = QtWidgets.QWidget()
        self.tabWidget = QtWidgets.QTabWidget(self.main_frame)

        # Create the navigation toolbar - still empty
        self.mpl_toolbar = MultiTabNavTool(self.canvases, self.tabWidget,
                                           self.main_frame)

        self.create_tabs(figures, labels)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.mpl_toolbar)
        self.vbox.addWidget(self.tabWidget)
        # vbox.addLayout(hbox)

        self.main_frame.setLayout(self.vbox)
        self.setCentralWidget(self.main_frame)

        # self.create_menu()
        # self.create_main_frame(figures, labels)
        # self.create_status_bar()

        # self.textbox.setText('1 2 3 4')
        # self.on_draw()

    def on_about(self):
        msg = """ doom dooom doom... doom di doom DOOOOOOM!!!!
        """
        QtWidgets.QMessageBox.about(self, "About the demo", msg.strip())

    # def on_pick(self, event):
    ## The event received here is of the type
    ## matplotlib.backend_bases.PickEvent
    ##
    ## It carries lots of information, of which we're using
    ## only a small amount here.
    ##
    # box_points = event.artist.get_bbox().get_points()
    # msg = "You've clicked on a bar with coords:\n %s" % box_points

    # QMessageBox.information(self, "Click!", msg)

    # def on_draw(self):
    # """ Redraws the figure
    # """
    # string = str(self.textbox.text())
    # self.data = list(map(int, string.split()))

    # x = list(range(len(self.data)))

    ## clear the axes and redraw the plot anew
    # self.axes.clear()
    # self.axes.grid(self.grid_cb.isChecked())

    # self.axes.bar(
    # left=x,
    # height=self.data,
    # width=self.slider.value() / 100.0,
    # align='center',
    # alpha=0.44,
    # picker=5)

    # self.canvas.draw()

    # @print_args()
    def create_tabs(self, figures, labels):

        # TODO: Maybe use
        # figs = list(map(plt.figure, plt.get_fignums()))
        # to embed all current figures if list is empty ???

        for fig, lbl in zip_longest(figures, labels):
            self.add_tab(fig, lbl)

    # @print_args()
    def create_main_frame(self, figures, labels):

        self.main_frame = QtWidgets.QWidget()
        self.tabWidget = QtWidgets.QTabWidget(self.main_frame)

        # Create the navigation toolbar NOTE: still empty
        self.mpl_toolbar = MultiTabNavTool(self.canvases, self.tabWidget,
                                           self.main_frame)

        # NavigationToolbar(canvas, parent) for canvas in self.canvases

        # tabs = QtWidgets.QTabWidget()

        self.create_tabs(figures, labels)

        # Bind the 'pick' event for clicking on one of the bars
        # canvas.mpl_connect('pick_event', self.on_pick)

        # Other GUI controls
        # self.textbox = QtWidgets.QLineEdit()
        # self.textbox.setMinimumWidth(200)
        # self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)

        # self.draw_button = QtWidgets.QPushButton("&Draw")
        # self.connect(self.draw_button, SIGNAL('clicked()'), self.on_draw)

        # self.grid_cb = QtWidgets.QCheckBox("Show &Grid")
        # self.grid_cb.setChecked(False)
        # self.connect(self.grid_cb, SIGNAL('stateChanged(int)'), self.on_draw)

        # slider_label = QtWidgets.QLabel('Bar width (%):')
        # self.slider = QtWidgets.QSlider(Qt.Horizontal)
        # self.slider.setRange(1, 100)
        # self.slider.setValue(20)
        # self.slider.setTracking(True)
        # self.slider.setTickPosition(QSlider.TicksBothSides)
        # self.connect(self.slider, SIGNAL('valueChanged(int)'), self.on_draw)

        # Layout with box sizers
        # hbox = QHBoxLayout()

        # for w in [  self.textbox, self.draw_button, self.grid_cb,
        # slider_label, self.slider]:
        # hbox.addWidget(w)
        # hbox.setAlignment(w, Qt.AlignVCenter)

        # print( self.mpl_toolbar.toolbars )

        self.vbox = vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.mpl_toolbar)
        vbox.addWidget(self.tabWidget)
        # vbox.addLayout(hbox)

        self.main_frame.setLayout(vbox)
        self.setCentralWidget(self.main_frame)

    # @print_args()
    def add_tab(self, fig, name=None):
        """
        dynamically add tabs with embedded matplotlib canvas
        """

        # set the default tab name
        if name is None:
            name = 'Tab %i' % (self.tabWidget.count() + 1)

        # initialise FigureCanvas
        canvas = fig.canvas or FigureCanvas(fig)
        canvas.setParent(self.tabWidget)
        canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvases.append(canvas)

        self.mpl_toolbar.add(canvas, self.main_frame)
        self.tabWidget.addTab(canvas, name)

        plt.close(fig)

        return canvas

    # def add_figure(self):
    #     """
    #     Create a figure from data and add_tab.  To be over-written by subclass.
    #     Useful when multiple figures of the same kind populate the tabs.
    #     """
    #     fig = Figure()
    #     fig.add_subplot(111)
    #     # Since we have only one plot, we can use add_axes instead of add_subplot, but then the subplot
    #     # configuration tool in the navigation toolbar wouldn't  work.
    #
    #     self.add_tab(fig)

    def create_status_bar(self):
        self.status_text = QtWidgets.QLabel("This is a demo")
        self.statusBar().addWidget(self.status_text, 1)

    # def create_menu(self):
    #     self.file_menu = self.menuBar().addMenu("&File")
    #
    #     load_file_action = self.create_action("&Save plot",
    #     shortcut="Ctrl+S", slot=self.save_plots,
    #     tip="Save the plot")
    #     quit_action = self.create_action("&Quit", slot=self.close,
    #     shortcut="Ctrl+Q", tip="Close the application")
    #
    #     self.add_actions(self.file_menu,
    #     (load_file_action, None, quit_action))
    #
    #     self.help_menu = self.menuBar().addMenu("&Help")
    #     about_action = self.create_action("&About",
    #     shortcut='F1', slot=self.on_about,
    #     tip='About the demo')
    #
    #     self.add_actions(self.help_menu, (about_action,))

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    # def create_action(  self, text, slot=None, shortcut=None,
    #     icon=None, tip=None, checkable=False,
    #     signal="triggered()"):
    #     action = QtWidgets.QAction(text, self)
    #     if icon is not None:
    #         action.setIcon(QIcon(":/%s.png" % icon))
    #     if shortcut is not None:
    #         action.setShortcut(shortcut)
    #     if tip is not None:
    #         action.setToolTip(tip)
    #         action.setStatusTip(tip)
    #     if slot is not None:
    #         self.connect(action, SIGNAL(signal), slot)
    #     if checkable:
    #         action.setCheckable(True)
    #     return action

    def save_figures(self, template=None, filenames=(), path=''):
        """

        Parameters
        ----------
        template
        filenames
        path

        Returns
        -------

        """
        from pathlib import Path

        # file_choices = "PNG (*.png)|*.png"
        # path = str(QFileDialog.getSaveFileName(self, 'Save file', '',
        #            file_choices))
        path = Path(path)
        n_tabs = len(self.canvases)
        if not filenames and template:
            filenames = list(map(template.format, range(n_tabs)))

        for i, canvas in enumerate(self.canvases):
            filename = Path(filenames[i])
            if not filename.is_absolute():
                filename = path / filename

            canvas.figure.savefig(filename)

        # if path:
        # self.canvas.print_figure(path, dpi=self.dpi)
        # self.statusBar().showMessage('Saved to %s' % path, 2000)


class MplMultiTab2D(QtWidgets.QMainWindow):
    """Combination tabs display matplotlib canvas"""

    # TODO: data that is not uniform square

    def __init__(self, figures=[], labels=[], shape=None, title=None):
        # TODO: add_row, add_column
        """ """
        super().__init__()
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle(title or self.__class__.__name__)

        self.figures = np.array(figures).reshape(shape)
        self.labels = labels  # np.array(labels).reshape(self.figures.shape)

        # create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        # Create the navigation toolbar stack
        self.toolstack = QtWidgets.QStackedWidget(self.main_widget)

        # stack switches display for central panel
        self.stack = QtWidgets.QStackedWidget(self.main_widget)

        # create the tab bars
        self.tabbars = []
        wn = (QtWidgets.QTabBar.RoundedWest, QtWidgets.QTabBar.RoundedNorth)
        for loc, labels in zip(wn, self.labels):
            tabs = self._create_tabs(loc, labels)
            tabs.currentChanged.connect(self.tab_change)
            self.tabbars.append(tabs)
        self.tabsWest, self.tabsNorth = self.tabbars

        # define layout
        grid = QtWidgets.QGridLayout(self.main_widget)
        # grid.setSpacing(10)

        # add widgets to layout
        grid.addWidget(self.toolstack, 0, 0, 1, 2)
        grid.addWidget(self.tabsNorth, 1, 1, 1, 1, QtCore.Qt.AlignLeft)
        grid.addWidget(self.tabsWest, 2, 0, 1, 1, QtCore.Qt.AlignTop)
        grid.addWidget(self.stack, 2, 1)

        # add canvasses to stack
        for row in self.figures:
            for fig in row:
                # print(self._rows*i + j)
                # print(fig)
                canvas = fig.canvas
                nav_tool = NavigationToolbar(canvas, self.toolstack)
                self.stack.addWidget(canvas)
                self.toolstack.addWidget(nav_tool)

                plt.close()

        # self.show()

    def _create_tabs(self, loc, labels):
        """create the tab bars at location with labels"""
        tabs = QtWidgets.QTabBar(self.main_widget)
        tabs.setShape(loc)
        for i, d in enumerate(labels):
            tabs.addTab(d)

        return tabs

    def tab_change(self):
        """Called upon change of tab"""
        i, j = self.tabsWest.currentIndex(), self.tabsNorth.currentIndex()
        n_rows, n_cols = self.figures.shape
        ix = i * n_cols + j
        # print( 'shape:', self.figures.shape )
        # print(i,j, ix)
        # print()
        # print(self.stack.currentWidget())

        self.stack.setCurrentIndex(ix)
        self.toolstack.setCurrentIndex(ix)

    def save_plots(self, filenames, path=''):

        # TODO: maybe connect to save button ??

        import os
        # file_choices = "PNG (*.png)|*.png"
        # path = str(QFileDialog.getSaveFileName(self,
        # 'Save file', '',
        # file_choices))
        path = os.path.realpath(path) + os.path.sep
        n_tabs = len(self.canvases)
        if isinstance(filenames, str):
            if '{' not in filenames:  # no format str specifier
                filenames = filenames + '{}'  # append numerical
            filenames = [filenames.format(i) for i in range(n_tabs)]

        for i, canvas in enumerate(self.canvases):
            filename = filenames[i]
            root, name = os.path.split(filename)
            if not root:
                filename = os.path.join(path, filename)

            canvas.figure.savefig(filename)
