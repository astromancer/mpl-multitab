"""
This library uses PyQt to create a gui which embeds matplotlib figures in a
tabbed window manager allowing easy navigation between many active figures.
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

# local
import recipes.pprint as pp
from recipes.logging import LoggingMixin


# ---------------------------------------------------------------------------- #
use('QTAgg')


TAB_POS = {
    'N': QtWidgets.QTabWidget.North,
    'W': QtWidgets.QTabWidget.West,
    'S': QtWidgets.QTabWidget.South,
    'E': QtWidgets.QTabWidget.East,
}

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

#


class TabManager(QtWidgets.QWidget, LoggingMixin):  # TabNode # QTabWidget??

    _tab_name_template = 'Tab {}'
    plot = None

    def __init__(self, figures=(), pos='N', parent=None):

        super().__init__(parent)
        self._items = {}
        self.tabs = QtWidgets.QTabWidget(self)
        #
        self._cid_focus_match = None

        #
        self._layout(pos)

        # resolve figures
        if isinstance(figures, abc.Sequence):
            items = itt.zip_longest((), figures)
        else:
            items = dict(figures).items()

        # add tabs
        for name, fig in items:
            self.add_tab(name, fig=fig)

    def _layout(self, pos):
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

        if pos == 'W':
            # add inactive spacer tab
            space_tab = QtWidgets.QTabWidget(self)
            space_tab.setVisible(False)
            space_tab.setEnabled(False)
            self.tabs.addTab(space_tab, ' ')
            self.tabs.setTabEnabled(0, False)
            # tabs.setTabVisible(0, False)

    def __repr__(self):
        pre = post = ''
        if parent := self._parent():
            index = parent.tabs.indexOf(self)
            name = parent.tabs.tabText(index)
            pre = f'{name!r}, '
            post = f', {index=}'
        return f'<{self.__class__.__name__}: {pre}level={self._level()}{post}>'

    def __len__(self):
        return self.tabs.count() - self.index_offset

    def __getitem__(self, key):

        if not isinstance(key, numbers.Integral):
            return self._items[key]

        n = len(self)
        key = key
        if key >= n or key < -n:
            raise IndexError(f'Index {key} out of range for '
                             f'{self.__class__.__name__} with {n} tabs.')

        return self.tabs.widget((key % n) + self.index_offset)

    def __setitem__(self, tab_name, figure):
        if tab_name in self._items:
            raise NotImplementedError

        self.add_tab(tab_name, fig=figure)

    # ------------------------------------------------------------------------ #
    @property
    def index_offset(self):
        return int(self.pos == 'W')

    def _index_up(self):
        # index of this manager widget wrt MplMultiTab
        indices = []
        manager = self
        while parent := manager._parent():
            indices.append(parent.tabs.indexOf(manager))
            manager = parent
        return indices[::-1]

    def _current_index(self):
        return (self.tabs.currentIndex() - self.index_offset, )

    def _parent(self):
        return self.parent().parent().parent()  # ^_^

    def _ancestors(self):
        manager = self
        while parent := manager._parent():
            yield parent
            manager = parent

    def _root(self):
        *_, root = self._ancestors()
        return root

    def _level(self):
        return len(list(self._ancestors()))

    def _height(self):
        return len(list(self._current_index()))

    # def _descendants(self):
    #     return

    # # alias
    # _descendents = _descendants

    def _siblings(self):
        return tuple(set(parent) - {self}) if (parent := self._parent()) else ()

    def _is_active(self):
        return (parent._active() is self) if (parent := self._parent()) else True

    def _active(self):
        return self.tabs.currentWidget()

    def _inactive(self):
        return self._active()._siblings()

    # ------------------------------------------------------------------------ #
    def set_focus(self, i):
        self.tabs.setCurrentIndex(i + self.index_offset)

    def link_focus(self):
        if self._cid_focus_match:
            self.logger.debug('Focus matching already active on {}. Nothing to '
                              'do here.', self)
            return

        self.logger.debug('Adding callback {} to group: {!r}',
                          pp.caller(self._match_focus), self)
        self._cid_focus_match = self.tabs.currentChanged.connect(self._match_focus)

    def unlink_focus(self):
        if not self._cid_focus_match:
            self.logger.debug('No focus matching active on {!r}. Nothing to do '
                              'here.', self)
            return

        self.logger.debug('Removing focus callback from group: {!r}', self)
        self.tabs.currentChanged.disconnect(self._cid_focus_match)
        self._cid_focus_match = None

    def _match_focus(self, i):
        i = i - self.index_offset
        self.logger.debug('Callback {!r}: {}', self, i)

        *current, _ = self._index_up()
        self.logger.debug('Current: {}', [*current, _])

        # disonnect parent callbacks
        self.logger.debug('Unlinking focus at active toplevel.')
        root = self._root()
        toplevel = root._active()
        toplevel.unlink_focus()
        root.set_focus(*current, None)

        focus = (*current, i)
        self.logger.debug('Callback setting {!r} sibling focus to: {}',
                          self, focus)
        for mgr in self._siblings():
            mgr.set_focus(i)

        self.logger.debug('Linking focus at active toplevel.')
        toplevel.link_focus()

        # for mgr, idx in zip(branch[::-1], current

        # for mgr, idx in zip(branch, current[::-1]):

        # for mgr, idx in zip(branch, current[::-1]):  # bottom up
        #     if next(mgr._current_index()) != idx:
        #         # disconnect focus callback
        #         if mgr._cid_focus_match:
        #             mgr.unlink_focus()

        #         self.logger.debug('{}: {}', mgr, idx)
        #         mgr.tabs.setCurrentIndex(idx)
        #         mgr.link_focus()

        # focus = (*current, i)
        # self.logger.debug('Callback setting {!r} inactive parents focus to: {}',
        #                   self, focus)
        # for mgr in self._root()._inactive():
        #     mgr.set_focus(*focus)

    # ------------------------------------------------------------------------ #

    def add_callback(self, func):
        # connect plot callback
        if not (func and callable(func)):
            self.logger.debug('Invalid object for callback: {}', func)
            return

        self.logger.debug('Adding callback: {}', pp.caller(func))
        self.plot = func
        self.tabs.currentChanged.connect(self._plot)

    def add_tab(self, name=None, *, fig=None, focus=True):
        """
        Dynamically add a tab with embedded matplotlib canvas.
        """
        self.logger.debug('Adding tab {!r}', name)
        fig = fig or Figure()

        if plt := sys.modules.get('matplotlib.pyplot'):
            plt.close(fig)

        # set the default tab name
        if name is None:
            name = self._tab_name_template.format(self.tabs.count() - self.index_offset + 1)

        self._items[name] = tab = MplTabbedFigure(fig)
        self.tabs.addTab(tab, name)

        if focus:
            logger.debug('focussing on {}', self.tabs.currentIndex() + 1)
            self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)

        return fig

    # ------------------------------------------------------------------------ #
    def get_figure(self, i):
        return self[i].figure

    def _plot(self, i, *args, **kws):
        self.logger.debug('Checking if plot needed: {!r}', i)

        indices = [*self._index_up(), i]
        if (fig := self.get_figure(indices)).axes:
            self.logger.debug('Plot {!r} already initialized.', i)
            return

        if not self.plot:
            self.logger.debug('No plot method defined.')
            return

        
        self.logger.debug('Creating plot {!r}.', indices)
        return self.plot(fig, indices, *args, **kws)

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
        TabManager.__init__(self, (), pos, parent)
        #
        self._previous = -1
        self._cid_otc = None

        # tabs switches the group being displayed in central panel which may
        # itself be NestedTabsManager or TabManager at lowest level
        figures = dict(figures)
        for name, figs in figures.items():
            self.add_group(name, figs)

        if self.plot:
            self.logger.debug('Detected figure initializer method {}. '
                              'Connecting group tab change callback to this method.',
                              pp.caller(self.plot))
            self.add_callback(self, self.plot)

        # if figures:
        #     self.link_focus()

    # ------------------------------------------------------------------------ #        
    def get_figure(self, key):
        obj = self
        for k in key:
            obj = obj[k]
        return obj.figure


    def _current(self):
        widget = self
        while not isinstance(widget, MplTabbedFigure):
            i = widget.tabs.currentIndex() - self.index_offset
            widget = widget.tabs.currentWidget()
            yield i, widget

    def _current_index(self):
        for i, _ in self._current():
            yield i

    # def _descendants(self):
    #     for mgr in self:
    #         yield mgr
    #         yield from mgr.descendants()

    # ------------------------------------------------------------------------ #

    # def add_callback(self, func):

    #     if not self._is_active():
    #         return

    #     # Connect method that plots active figure
    #     self.logger.debug('Adding callback to active group: {}',
    #                       pp.caller(self._on_tab_change))
    #     self._cid_otc = self.tabs.currentChanged.connect(self._on_tab_change)

        # propagate down
        # for mgr, self._current_index())
        # for mgr in self:
        #     mgr.add_callback(func)

    def remove_callback(self, cid):
        return self.tabs.currentChanged.disconnect(cid)

    def _on_tab_change(self, i):
        # This will run *before* qt switches the tabs on mouse click
        before = [tuple(q._current_index()) for q in self]

        self.logger.info('Tab change callback level {}! CURRENT indices:{}',
                         self._level(), before)

        # if self._cid_focus_match:

        after = [tuple(q._current_index()) for q in self]
        self.logger.info('AFTER Tab change callback indices:\n{}', after)

        # do plot
        self._plot_active_tab(i)

    def _plot_active_tab(self, i):
        self.logger.debug('Plot callback initiated by group switch. New group is {}', i)
        #
        indices, (*_, active_mgr, _) = zip(*self._current())
        self.logger.debug('new index: {}', indices)
        active_mgr._plot(indices[-1])

    # ------------------------------------------------------------------------ #
    def add_tab(self, *keys, fig=None, focus=True):
        """
        Add a (nested) tab.
        """
        self.logger.debug('Adding tab: {}', keys)

        gid, *keys = keys
        if gid not in self._items:
            if not keys:
                raise NotImplementedError

            # add nested tabs
            self.add_group(gid,
                           (fig or {}).get(gid, ()),
                           kls=TabManager if (len(keys) == 1) else type(self))

        return self[gid].add_tab(*keys, fig=fig, focus=not self.plot)

    def add_group(self, name=None, figures=(), kls=None):
        """
        Add a (nested) tab group.
        """
        i = self.tabs.count()
        if name is None:
            name = self._tab_name_template.format(i)

        self.logger.debug(f'Adding group {name!r}')

        kls = kls or type(self)
        self._items[name] = nested = kls(figures, parent=self)
        self.tabs.addTab(nested, name)

        if i == self.index_offset:
            self.tabs.setCurrentIndex(i)

        return nested

    # -------------------------------------------------------------------- #
    def set_focus(self, *indices):
        self.logger.debug('{!r} focus {}', self, indices)
        i, *indices = indices

        # None can be used as sentinel to mean keep focus the same below
        if i is None:
            return

        self.tabs.setCurrentIndex(idx := i + self.index_offset)
        self._previous = idx

        itr = self if self._cid_focus_match else [self._active()]
        for mgr in itr:
            mgr.set_focus(*indices)

    def _match_focus(self, i):
        i = i - self.index_offset
        logger.debug('{!r} {}', self, i)
        # disconnect callback from previously active tab
        if self._previous != -1:
            previous = self.tabs.widget(self._previous + self.index_offset)
            previous.unlink_focus()
            current = list(previous._current_index())
        else:
            current = [0] * self._height()
        self._previous = i

        # set focus of the new target group same as previous
        target = self[i]
        self.logger.debug('{!r} matching target group {} focus with current: {}',
                          self, i, current)
        target.set_focus(*current)

        #  also set focus of siblings
        focus = i, *current
        self.logger.debug('{!r} matching sibling groups focus with current: {}',
                          self, focus)
        for mgr in self._siblings():
            mgr.set_focus(*focus)

        # add focus linking callback to new group
        target.link_focus()

    def link_focus(self, *indices):
        super().link_focus()
        if indices:
            i, *indices = indices
            target = self[i]
        else:
            target = self._active()
        target.link_focus(*indices)

    def unlink_focus(self, *indices):
        super().unlink_focus()
        if indices:
            i, *indices = indices
            target = self[i]
        else:
            target = self._active()
        target.unlink_focus(*indices)

    # def save(self, filenames=(), folder='', **kws):
    #     n = self.tabs.count()
    #     if n == 1:
    #         logger.warning('No figures embedded yet, nothing to save!')
    #         return

    #     if is_template_string(filenames):
    #         raise NotImplementedError()

    #     filenames = self._check_filenames(filenames)
    #     for filenames, tabs in zip(filenames, self):
    #         tabs.save(filenames, folder, **kws)


class MplTabGUI(QtWidgets.QMainWindow):

    def __init__(self, figures=(), title=None, pos='N',
                 manager=TabManager, parent=None, **kws):

        super().__init__(parent)
        self.setWindowTitle(title or self.__class__.__name__)

        # create main widget
        self.main_frame = QtWidgets.QWidget(self)
        self.main_frame.setFocus()
        self.setCentralWidget(self.main_frame)

        self.tabs = manager(figures, pos, parent=self.main_frame, **kws)
        self.tabs.tabs.setMovable(True)  # outer tabs movable

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        self.main_frame.setLayout(layout)

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

    def set_focus(self, *indices):
        self.tabs.set_focus(*indices)

    def add_callback(self, func):
        return self.tabs.add_callback(func)


# aliases
MplTabs = MplTabGui = MplTabGUI


class MplMultiTab(MplTabGUI):
    """
    Combination tabs for displaying matplotlib figures.
    """

    def __init__(self, figures=(), title=None, pos='N',
                 manager=NestedTabsManager,
                 parent=None, **kws):
        #
        super().__init__(figures, title, pos, manager, parent, **kws)

    def add_group(self, name=None, figures=()):
        self.tabs.add_group(name, figures)

    def add_tab(self, *keys, fig=None):
        """
        Add a (nested) tab.
        """
        return self.tabs.add_tab(*keys, fig=fig)

    def link_focus(self):
        self.tabs.link_focus()
        # self.tabs.add_callback()


class MplMultiTab2D(MplMultiTab):
    def __init__(self, figures=(), title=None, pos='W', parent=None):
        super().__init__(figures, title, pos, parent=parent)
