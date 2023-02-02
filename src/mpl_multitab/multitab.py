"""
This script uses PyQt to create a gui which embeds matplotlib figures in a
simple tabbed window manager allowing easy navigation between many active
figures.
"""

# std
import sys
import numbers
import itertools as itt
from pathlib import Path
from collections import abc

# third-party
from loguru import logger
from matplotlib import use
from matplotlib.figure import Figure
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import (
    NavigationToolbar2QT as NavigationToolbar)


# ---------------------------------------------------------------------------- #
use('QTAgg')


TAB_POS = {'N': QtWidgets.QTabWidget.North,
           'W': QtWidgets.QTabWidget.West}

# ---------------------------------------------------------------------------- #


def is_template_string(s):
    if not isinstance(s, str):
        return False

    if '{' in s:  # NOTE: this is a weak test
        return True

    raise ValueError('Not a valid template string. Expected format string '
                     'syntax (curly braces).')

# ---------------------------------------------------------------------------- #


class MplTabbedFigure(QtWidgets.QWidget):

    def __init__(self, figure, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # initialise FigureCanvas
        self.figure = figure
        self.canvas = canvas = FigureCanvas(figure)
        canvas.setParent(self)
        canvas.setFocusPolicy(QtCore.Qt.ClickFocus)

        # Create the navigation toolbar
        navtool = NavigationToolbar(canvas, self)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(navtool)
        self.vbox.addWidget(canvas)
        self.setLayout(self.vbox)


class TabManager(QtWidgets.QWidget):  # QTabWidget??

    _tab_name_template = 'Tab {}'

    def __init__(self, figures=(), labels=(), parent=None):

        super().__init__(parent)
        self._items = {}
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setMovable(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        # make horizontal and vertical tab widgets overlap fully
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

        # resolve figures
        if isinstance(figures, abc.Sequence):
            items = itt.zip_longest(labels, figures)
        else:
            items = dict(figures).items()

        # add tabs
        for name, fig in items:
            self.add_tab(name, fig=fig)

    def __getitem__(self, key):
        if isinstance(key, numbers.Integral):
            key = list(self._items.keys())[key]
        return self._items[key]

    def __setitem__(self, tab_name, figure):
        if tab_name in self._items:
            raise NotImplementedError

        self.add_tab(tab_name, fig=figure)

    def add_tab(self, name=None, *, fig=None):
        """
        Dynamically add a tab with embedded matplotlib canvas.
        """
        fig = fig or Figure()

        if plt := sys.modules.get('matplotlib.pyplot'):
            plt.close(fig)

        # set the default tab name
        if name is None:
            name = self._tab_name_template.format(self.tabs.count() + 1)

        tfig = MplTabbedFigure(fig)
        self.tabs.addTab(tfig, name)
        self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)
        self._items[name] = tfig

        return fig

    def save(self, filenames=(), folder='', **kws):
        """

        Parameters
        ----------
        template
        filenames
        path

        Returns
        -------

        """
        n = self.tabs.count()
        if n == 1:
            logger.warning('No figures embedded yet, nothing to save!')
            return

        folder = Path(folder)

        for i, filename in enumerate(self._check_filenames(filenames)):
            if not (filename := Path(filename)).is_absolute():
                filename = folder / filename

            figure = self[self.tabs.tabText(i)].canvas.figure
            figure.savefig(filename.resolve(), **kws)

    save_figures = save

    def _check_filenames(self, filenames):
        n = self.tabs.count()
        if is_template_string(filenames):
            logger.info('Saving {} figures with filename template: {!r}',
                        n, filenames)
            # partial format string with dataset name
            return ((filenames.format(self.tabs.tabText(_))) for _ in range(n))

        if isinstance(filenames, abc.Sequence):
            if (m := len(filenames)) != n:
                raise ValueError(
                    f'Incorrect number of filenames {m}. There are {n} figure '
                    f'groups in this {self.__class__.__name__}.'
                )

            if isinstance(filenames, abc.MutableMapping):
                return (filenames[self.tabs.tabText(_)]
                        for _ in range(n))
            return filenames

        if isinstance(filenames, abc.Iterable):
            return filenames

        raise TypeError(f'Invalid filenames: {filenames!r}')


class MplMultiTab(QtWidgets.QMainWindow):

    def __init__(self, figures=(), labels=(), title=None, parent=None):

        super().__init__(parent)
        self.setWindowTitle(title or self.__class__.__name__)
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        #
        self.canvases = []

        self.main_frame = QtWidgets.QWidget(self)
        self.main_frame.setFocus()
        self.setCentralWidget(self.main_frame)

        self.tabs = TabManager(figures, parent=self.main_frame)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        self.main_frame.setLayout(layout)

        # self.create_menu()
        # self.create_status_bar()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.show()

    def add_tab(self, name=None, *, fig=None):
        return self.tabs.add_tab(name, fig=fig)

    def on_about(self):
        QtWidgets.QMessageBox.about(self, self.__class__.__name__,
                                    'Tabbed FigureCanvas Manager')

    def create_status_bar(self):
        self.status_text = QtWidgets.QLabel('')
        self.statusBar().addWidget(self.status_text, 1)



class TabManager2D(TabManager):

    _tab_name_template = 'Group {}'
    _filename_template = '{:s}-{:s}.png'

    def __init__(self, figures=(), labels=(), group_pos='W', parent=None):

        # initialise empty
        TabManager.__init__(self, parent=parent)

        # tab bars group switches the dataset
        # being displayed in central panel which contains multiple observations
        # that can be switched separately with nested tabs
        group_pos = group_pos.upper()
        self.tabs.setTabPosition(TAB_POS[group_pos])
        self.tabs.setMovable(True)
        
        if group_pos == 'W':
            # add dead spacer tab
            space_tab = QtWidgets.QTabWidget(self)
            space_tab.setVisible(False)
            space_tab.setEnabled(False)
            self.tabs.addTab(space_tab, ' ')
            self.tabs.setTabEnabled(0, False)
            # tabs.setTabVisible(0, False)

        figures = dict(figures)
        for group_name, figs in figures.items():
            for tab_name, fig in figs.items():
                self.add_tab(group_name, tab_name, fig=fig)

    def __setitem__(self, group_name, figure):
        raise NotImplementedError('TODO')

    def add_group(self, figures=(), name=None):
        i = self.tabs.count()
        if name is None:
            name = self._tab_name_template.format(i)

        htabs = TabManager(figures)
        self.tabs.addTab(htabs, name)
        if i == 1:
            self.tabs.setCurrentIndex(i)
        self._items[name] = htabs

    def add_tab(self, group_name=None, tab_name=None, *, fig=None):
        """
        Add a tab with embedded matplotlib canvas, return the figure.
        """
        if isinstance(fig, abc.Sequence):
            return self.add_group(fig, group_name)

        fig = fig or Figure()
        if plt := sys.modules.get('matplotlib.pyplot'):
            plt.close(fig)

        i = self.tabs.currentIndex()  # 0 if no tabs yet
        group_name = (group_name
                      or self.tabs.tabText(i)
                      or self._tab_name_template.format(0))

        if group_name in self._items:
            self[group_name].add_tab(tab_name, fig=fig)
        else:
            self.add_group({tab_name: fig}, group_name)

        return fig

    def save(self, filenames=(), folder='', **kws):
        n = self.tabs.count()
        if n == 1:
            logger.warning('No figures embedded yet, nothing to save!')
            return

        if is_template_string(filenames):
            raise NotImplementedError()

        filenames = self._check_filenames(filenames)
        for filenames, tabs in zip(filenames, self._items.values()):
            tabs.save(filenames, folder, **kws)



class MplMultiTab2D(QtWidgets.QMainWindow):
    """
    Combination tabs display matplotlib canvas.
    """

    def __init__(self, figures=(), title=None, group_pos='W', parent=None):
        """ """
        super().__init__(parent)
        self.setWindowTitle(title or self.__class__.__name__)
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # create main widget
        self.main_frame = QtWidgets.QWidget(self)
        self.main_frame.setFocus()
        self.setCentralWidget(self.main_frame)

        self.groups = TabManager2D(figures, group_pos=group_pos)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.groups)
        layout.setSpacing(0)
        self.main_frame.setLayout(layout)

    def __getitem__(self, groupname):
        return self.groups[groupname]

    def add_group(self, figures=(), name=None):
        self.groups.add_group(figures, name)

    def add_tab(self, group_name=None, tab_name=None, *, fig=None):
        """
        Add a tab to a tab group.
        """
        return self.groups.add_tab(group_name, tab_name, fig=fig)
