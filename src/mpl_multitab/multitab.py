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


def depth(obj, _depth=0):
    if isinstance(obj, abc.MutableMapping):
        return max((_depth, *(depth(v, _depth + 1) for v in obj.values())))

    elif isinstance(obj, abc.Sequence):
        return 1

    return _depth

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

    def __init__(self, figures=(), pos='N', parent=None):

        super().__init__(parent)
        self._items = {}
        self._focus_link_ids = []
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setMovable(True)

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        # make horizontal and vertical tab widgets overlap fully
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # tab position
        self.pos = pos = pos.upper()
        self.tabs.setTabPosition(TAB_POS[pos])
        self.tabs.setMovable(True)

        if pos == 'W':
            # add inactive spacer tab
            space_tab = QtWidgets.QTabWidget(self)
            space_tab.setVisible(False)
            space_tab.setEnabled(False)
            self.tabs.addTab(space_tab, ' ')
            self.tabs.setTabEnabled(0, False)
            # tabs.setTabVisible(0, False)

        # resolve figures
        if isinstance(figures, abc.Sequence):
            items = itt.zip_longest((), figures)
        else:
            items = dict(figures).items()

        # add tabs
        for name, fig in items:
            self.add_tab(name, fig=fig)

    def __getitem__(self, key):
        if isinstance(key, numbers.Integral):
            return self.tabs.widget(key)
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


class NestedTabsManager(TabManager):
    _tab_name_template = 'Group {}'
    # _filename_template = '{:s}-{:s}.png'

    def __new__(cls, figures, *args, **kws):
        # catch for figures being 1d sequence or mapping, use plain TabManager
        if figures and depth(figures) == 1:
            return TabManager(figures)

        return super().__new__(cls)

    def __init__(self, figures=(), pos='N', parent=None):

        # initialise empty
        TabManager.__init__(self, pos=pos, parent=parent)

        # tabs switches the group
        # being displayed in central panel which may itself be NestedTabsManager
        # or TabManager at lowest level

        figures = dict(figures)
        for name, figs in figures.items():
            self.add_group(name, figs)

    def add_group(self, name=None, figures=(), kls=None):
        i = self.tabs.count()
        if name is None:
            name = self._tab_name_template.format(i)

        print(f'Adding group {name!r}')

        kls = kls or type(self)
        self._items[name] = nested = kls(figures)
        self.tabs.addTab(nested, name)

        if i == (self.pos == 'W'):
            self.tabs.setCurrentIndex(i)

    def add_tab(self, *keys, fig=None):
        gid, *keys = keys
        print('Adding tab', gid, keys)

        if gid not in self._items:
            if not keys:
                raise NotImplementedError

            # add nested tabs
            self.add_group(gid,
                           (fig or {}).get(gid, ()),
                           kls=NestedTabsManager if (len(keys) > 1) else TabManager)

        return self[gid].add_tab(*keys, fig=fig)

    def link_focus(self):
        assert not self._focus_link_ids
        
        if not self._items:
            return
        
        managers = list(self._items.values())
        for pairs in itt.combinations(managers, 2):
            for direction in (list, reversed):
                mgr1, mgr2 = direction(pairs)
                mgr1._focus_link_ids.append(
                    mgr1.tabs.currentChanged.connect(mgr2.tabs.setCurrentIndex)
                )

        for mgr in managers:
            if isinstance(mgr, NestedTabsManager):
                mgr.link_focus()
                
        mgr = managers[0]
        mgr.tabs.setCurrentIndex(mgr.tabs.currentIndex())
                

    def unlink_focus(self):
        for cid in self._focus_link_ids:
            self.tabs.currentChanged.disconnect(cid)
            
    # def save(self, filenames=(), folder='', **kws):
    #     n = self.tabs.count()
    #     if n == 1:
    #         logger.warning('No figures embedded yet, nothing to save!')
    #         return

    #     if is_template_string(filenames):
    #         raise NotImplementedError()

    #     filenames = self._check_filenames(filenames)
    #     for filenames, tabs in zip(filenames, self._items.values()):
    #         tabs.save(filenames, folder, **kws)


class MplTabGui(QtWidgets.QMainWindow):

    def __init__(self, figures=(), title=None, manager=TabManager, parent=None, **kws):

        super().__init__(parent)
        self.setWindowTitle(title or self.__class__.__name__)
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # create main widget
        self.main_frame = QtWidgets.QWidget(self)
        self.main_frame.setFocus()
        self.setCentralWidget(self.main_frame)

        self.tabs = manager(figures, parent=self.main_frame, **kws)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        self.main_frame.setLayout(layout)

        # self.create_menu()
        # self.create_status_bar()

    def __getitem__(self, key):
        return self.tabs[key]

    def __setitem__(self, key, fig):
        self.tabs[key] = fig

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.show()

    def add_tab(self, name=None, *, fig=None):
        return self.tabs.add_tab(name, fig=fig)

    # def on_about(self):
    #     QtWidgets.QMessageBox.about(self, self.__class__.__name__,
    #                                 'Tabbed FigureCanvas Manager')

    # def create_status_bar(self):
    #     self.status_text = QtWidgets.QLabel('')
    #     self.statusBar().addWidget(self.status_text, 1)


class MplMultiTab(MplTabGui):
    """
    Combination tabs for displaying matplotlib figures.
    """

    def __init__(self, figures=(), title=None,  pos='N', parent=None, **kws):
        super().__init__(figures, title, NestedTabsManager, parent, **kws)

    def add_group(self, name=None, figures=()):
        self.tabs.add_group(name, figures)

    def add_tab(self, *keys, fig=None):
        """
        Add a tab to a tab group.
        """
        return self.tabs.add_tab(*keys, fig=fig)

    def set_focus(self, *indices):
        widget = self.tabs.tabs
        for i in indices:
            widget.setCurrentIndex(i)
            widget = getattr(widget.currentWidget(), 'tabs', None)

    def link_focus(self):
        return self.tabs.link_focus()


class MplMultiTab2D(MplMultiTab):
    def __init__(self, figures=(), title=None, pos='W', parent=None):
        super().__init__(figures, title, pos, parent)
