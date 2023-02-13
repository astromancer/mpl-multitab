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

# relative
from ._logging import LoggingMixin


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


class TabNode(QtWidgets.QWidget, LoggingMixin):

    # ------------------------------------------------------------------------ #
    def __repr__(self):
        pre = post = ''
        if parent := self._parent():
            index = parent.tabs.indexOf(self)
            name = parent.tabs.tabText(index)
            pre = f'{name!r}, '
            post = f', {index=}'
        return f'<{self.__class__.__name__}: {pre}level={self._level()}{post}>'

    def __getitem__(self, _):
        return self

    # ------------------------------------------------------------------------ #
    def _siblings(self):
        return tuple(set(parent) - {self}) if (parent := self._parent()) else ()

    def _parent(self):
        return self.parent().parent().parent()  # ^_^

    def _ancestors(self):
        manager = self
        while parent := manager._parent():
            yield parent
            manager = parent

    def _root(self):
        if self._parent():
            *_, root = self._ancestors()
            return root
        return self

    def _level(self):
        return len(list(self._ancestors()))

    _depth = _level

    def _height(self):
        return 0

    def is_leaf(self):
        return self._height() == 0

    # ------------------------------------------------------------------------ #
    def _active(self):
        return None

    def _active_branch(self):
        yield self

        node = self
        while (node := node._active()):
            yield node

    def _is_active(self):
        return (parent._active() is self) if (parent := self._parent()) else True

    # ------------------------------------------------------------------------ #
    def _rindex(self):
        # index of this node widget wrt root node
        child = self
        for parent in self._ancestors():
            yield parent._find(child)
            child = parent

    def _index(self):
        return tuple(self._rindex())[::-1]


class MplTabbedFigure(TabNode):

    plot = None

    def __init__(self, figure, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # initialise FigureCanvas
        self.figure = figure
        self.canvas = canvas = FigureCanvas(figure)
        canvas.setParent(self)
        canvas.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Create the navigation toolbar
        navtool = NavigationToolbar(canvas, self)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(navtool)
        self.vbox.addWidget(canvas)
        self.setLayout(self.vbox)

        self._drawn = False

    def add_callback(self, func):
        # connect plot callback
        if not (func and callable(func)):
            self.logger.debug('Invalid object for callback: {}', func)
            return

        # add plot function
        self.logger.debug('Attaching callback to {}: {}', self, func)
        self.plot = func

    def _plot(self, *args, **kws):

        # self._root()._index(self)
        indices = list(self._index())
        self.logger.debug('Checking if plot needed: {}', indices)

        if self.figure.axes:
            self.logger.debug('Plot {} already initialized.', indices)
            return

        if not self.plot:
            self.logger.debug('No plot method defined for {}.', indices)
            return

        self.logger.debug('Creating plot {}.', indices)
        self._cid_draw0 = self.canvas.mpl_connect('draw_event', self._on_draw)
        return self.plot(self.figure, indices, *args, **kws)

    def _on_draw(self, event):
        self._drawn = True
        self.canvas.mpl_disconnect(self._cid_draw0)


class TabManager(TabNode):

    _tab_name_template = 'Tab {}'

    def __init__(self, figures=(), pos='N', parent=None):

        super().__init__(parent)
        self.tabs = QtWidgets.QTabWidget(self)
        #
        self._cid = None
        self._link_focus = False
        self._previous = -1
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

    def __len__(self):
        return self.tabs.count() - self.index_offset

    def __getitem__(self, key):

        if key is ...:
            return tuple(self.values())

        if key == '*':
            return self._active()

        if isinstance(key, tuple):
            # reduce
            if (n := len(key)) > (h := self._height()):
                raise IndexError(f'Invalid number of indices {n} for {self!r} '
                                 f'with {h} levels.')
            i, *key = key
            return self[i][tuple(key)]

        return self.tabs.widget(self._resolve_index(key))

    def __setitem__(self, tab_name, figure):
        if tab_name in self:
            raise NotImplementedError

        self.add_tab(tab_name, fig=figure)

    def __delitem__(self, key):
        self.tabs.removeTab(self._resolve_index(key))

    def __contains__(self, key):
        return key in self.keys()

    def keys(self):
        for i in range(self.index_offset, self.tabs.count()):
            yield self.tabs.tabText(i)

    def values(self):
        for i in range(self.index_offset, self.tabs.count()):
            yield self.tabs.widget(i)

    def _resolve_index(self, key):
        if isinstance(key, str):
            for i, trial in enumerate(self.keys(), self.index_offset):
                if key == trial:
                    return i
            raise KeyError(f'Could not resolve tab index {key!r}.')

        if not isinstance(key, numbers.Integral):
            raise TypeError(f'Invalid type object ({key}) for indexing {self!r}.')

        n = len(self)
        if key >= n or key < -n:
            raise IndexError(f'Index {key} out of range for '
                             f'{self.__class__.__name__} with {n} tabs.')

        return (key % n) + self.index_offset

    # ------------------------------------------------------------------------ #
    @property
    def index_offset(self):
        return int(self.pos in 'EW')

    def _current_index(self):
        return self.tabs.currentIndex() - self.index_offset

    def _current_indices(self):
        if not (branch := tuple(self._active_branch())):
            return

        for node in branch[:-1]:
            yield node._current_index()

    def _find(self, item):
        if (i := self.tabs.indexOf(item)) != -1:
            i -= self.index_offset
        return i

    # ------------------------------------------------------------------------ #
    def _active(self):
        return self.tabs.currentWidget()

    def _inactive(self):
        return self._active()._siblings()

    def _height(self):
        return len(tuple(self._current_indices()))

    # def _children(self):
    #     return ()

    # def _descendants(self):
    #     yield

    # # alias
    # _descendents = _descendants

    # ------------------------------------------------------------------------ #
    def add_callback(self, func):
        # connect plot callback
        if not (func and callable(func)):
            self.logger.debug('Invalid object for callback: {}', func)
            return

        # Connect function
        self.logger.debug('Adding callback to {}: {}', self, self._on_change)
        self._cid = self.tabs.currentChanged.connect(self._on_change)

        # propagate down
        for node in self.values():
            node.add_callback(func)

    def remove_callback(self, cid):
        return self.tabs.currentChanged.disconnect(cid)

    def _on_change(self, i):
        self.logger.debug('Tab change {}', i)

        # focus
        if self._link_focus:
            self._match_focus(i)

        # plot init for next active tab
        if self._is_active() and (fig := self[i]).plot:
            fig._plot()

            if not fig._drawn:
                self.logger.debug('Drawing figure: {}', i)
                fig.canvas.draw()

    # ------------------------------------------------------------------------ #

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

        tab = MplTabbedFigure(fig)
        self.tabs.addTab(tab, name)

        if focus:
            logger.debug('focussing on {}', self.tabs.currentIndex() + 1)
            self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)

        return fig

    def remove_tab(self, key):
        return self.tabs.remove(self.tabs.indexOf(self._resolve_index(key)))

    # ------------------------------------------------------------------------ #
    def set_focus(self, key):
        self.tabs.setCurrentIndex(self._resolve_index(key))

    def link_focus(self):
        if self._cid:
            if self._link_focus:
                self.logger.debug('Focus matching already active on {}. Nothing to '
                                  'do here.', self)
                return

            self._link_focus = True
            return

        self.logger.debug('Adding callback {} to group: {!r}',
                          self._on_change, self)
        self._cid = self.tabs.currentChanged.connect(self._on_change)
        self._link_focus = True

    def unlink_focus(self):
        if not (self._cid and self._link_focus):
            self.logger.debug('No focus matching active on {!r}. Nothing to do '
                              'here.', self)
            return

        self._link_focus = False

    def _match_focus(self, i):
        i = i - self.index_offset
        self.logger.debug('Callback {!r}: {}', self, i)

        *current, _ = self._index()
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

        self.logger.debug('Reconnecting focus matching at active toplevel.')
        toplevel.link_focus()

    # ------------------------------------------------------------------------ #
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

            self[i].figure.savefig(filename.resolve(), **kws)

    save_figures = save

    def _check_filenames(self, filenames):
        n = self.tabs.count()
        if is_template_string(filenames):
            self.logger.info('Saving {} figures with filename template: {!r}',
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
    plot = False

    def __new__(cls, figures, *args, **kws):
        # catch for figures being 1d sequence or mapping, use plain TabManager
        if figures and depth(figures) == 1:
            return TabManager(figures)

        return super().__new__(cls)

    def __init__(self, figures=(), pos='N', parent=None):

        # initialise empty
        TabManager.__init__(self, (), pos, parent)

        # tabs switches the group being displayed in central panel which may
        # itself be NestedTabsManager or TabManager at lowest level
        figures = dict(figures)
        for name, figs in figures.items():
            self.add_group(name, figs)

        if self.plot:
            self.logger.debug('Detected figure initializer method {}. '
                              'Connecting group tab change callback to this method.',
                              self.plot)
            self.add_callback(self, self.plot)

        if figures:
            self.link_focus()

    # ------------------------------------------------------------------------ #
    def _on_change(self, i):
        # This will run *before* qt switches the tabs on mouse click
        self.logger.debug('Tab change callback level {}. CURRENT indices: {}',
                          self._level(), [tuple(q._current_indices()) for q in self])

        i = i - self.index_offset
        logger.debug('{!r} {}', self, i)
        # disconnect callback from previously active tab
        if self._previous == -1:  # first change
            current = [0] * self._height()
        else:
            # turn of the focus linking for inactive groups else infinite loop
            self.logger.debug('Unlinking previously active tab {}', self._previous)
            previous = self.tabs.widget(self._previous + self.index_offset)
            previous.unlink_focus()
            current = tuple(previous._current_indices())
        self._previous = i

        # self.logger.debug()
        super()._on_change((i, *current))

        self.logger.debug('Callback completed successfully.')

    # ------------------------------------------------------------------------ #
    def add_tab(self, *keys, fig=None, focus=True):
        """
        Add a (nested) tab.
        """
        self.logger.debug('Adding tab: {}', keys)

        gid, *keys = keys
        if gid not in self:
            if not keys:
                raise NotImplementedError

            # add nested tabs
            self.add_group(gid,
                           (fig or {}).get(gid, ()),
                           kls=TabManager if (len(keys) == 1) else type(self))

        return self[gid].add_tab(*keys, fig=fig, focus=focus)

    def add_group(self, name=None, figures=(), kls=None):
        """
        Add a (nested) tab group.
        """
        i = self.tabs.count()
        if name is None:
            name = self._tab_name_template.format(i)

        self.logger.debug(f'Adding group {name!r}')

        kls = kls or type(self)
        nested = kls(figures, parent=self)
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

        self.tabs.setCurrentIndex(i + self.index_offset)
        self._previous = i

        itr = self if self._link_focus else [self._active()]
        for mgr in itr:
            mgr.set_focus(*indices)

    def _match_focus(self, i):

        # set focus of the new target group same as previous
        i, *new = i
        target = self[i]
        self.logger.debug('{!r} matching target group {} focus with new: {}',
                          self, i, new)
        target.set_focus(*new)

        #  also set focus of siblings
        self.logger.debug('{!r} matching sibling groups focus with : {}',
                          self, [i, *new])
        for mgr in self._siblings():
            mgr.set_focus(i, *new)

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
        self.tabs.add_callback(func)


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


class MplMultiTab2D(MplMultiTab):
    def __init__(self, figures=(), title=None, pos='W', parent=None):
        super().__init__(figures, title, pos, parent=parent)
