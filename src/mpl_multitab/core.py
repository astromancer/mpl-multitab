"""
This library uses PyQt to create a gui which embeds matplotlib figures in a
tabbed window manager allowing easy navigation between many active figures.
"""

# std
import sys
import numbers
import operator as op
import itertools as itt
import contextlib as ctx
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


def get_figure(ui=None, *keys, **kws):
    if ui:
        tab = ui.add_tab(*keys, fig=kws)
        return tab.figure

    if plt := sys.modules.get('matplotlib.pyplot'):
        return plt.figure(**kws)

    return Figure(**kws)


def is_template_string(s):
    if not isinstance(s, str):
        return False

    if '{' in s:
        # NOTE: this is a fairly weak test, but hopefully no one actually wants
        # curly braces in a actualy file name
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
    # Base class for tab items

    # ------------------------------------------------------------------------ #
    def __repr__(self):
        pre = index = ''
        level = f'{self._level()}/{self._root()._height()}'
        if parent := self._parent():
            index = parent.tabs.indexOf(self)
            pre = f'{parent.tabs.tabText(index)!r}, '
            index = f'{index=}, '

        return (f'<{self.__class__.__name__}: {pre}'
                f'level={level}, {index}'
                f'depth={self._height()}>')

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
            if key:
                i, *key = key
                return self[i][tuple(key)]

            # empty tuple, returns object itself...
            return self

        raise NotImplementedError()

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        yield from self.values()

    def keys(self):
        yield from ()

    def values(self):
        yield from ()

    # ------------------------------------------------------------------------ #
    def _children(self):
        yield from self.values()

    def _descendants(self):
        for child in self._children():
            yield child
            yield from child._descendants()

    # alias
    _descendents = _descendants

    def _siblings(self):
        return tuple(set(parent) - {self}) if (parent := self._parent()) else ()

    def _parent(self):
        if parent := self.parent():
            parent = parent.parent().parent()    # ^_^
            if isinstance(parent, TabNode):
                return parent

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

    def _is_root(self):
        return

    def _level(self):
        return len(list(self._ancestors()))

    _depth = _level

    def _height(self):
        if self._is_leaf():
            return 0

        return max(node._height() for node in self.values()) + 1

    def _is_leaf(self):
        return next(self.values(), None) is None

    def _leaves(self):
        yield from (x for x in self._descendants() if x._is_leaf())

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
    def _current_indices(self):
        for node in tuple(self._active_branch())[:-1]:
            yield node._current_index()

    def _current_index(self):
        raise NotImplementedError()

    def _rindex(self):
        # index of this node widget wrt root node
        child = self
        for parent in child._ancestors():
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

    def add_callback(self, func, *args, **kws):
        # connect plot callback
        if not (func and callable(func)):
            self.logger.debug('Invalid object for callback: {!r}', func)
            return

        # add plot function
        self.logger.debug('Adding plot method to {}: {}', self, func)

    def _plot(self):

        # self._root()._index(self)
        indices = list(self._index())
        self.logger.debug('Checking if plot needed: {}', indices)

        if self.figure.axes:
            self.logger.debug('Plot {} already initialized.', indices)
            return

        if not self.plot:
            self.logger.debug('No plot method defined for {}.', indices)
            return

        # Connect draw calllback
        self._cid_draw0 = self.canvas.mpl_connect('draw_event', self._on_draw)

        self.logger.debug('Calling plot method {} for {}.', self.plot, indices)
        return self.plot(self.figure, indices)

    def _on_draw(self, event):
        logger.debug('Running first draw action.')
        self._drawn = True
        self.canvas.mpl_disconnect(self._cid_draw0)
        logger.debug('Disconnected first draw action.')


class TabManager(TabNode):

    plot = False
    _tab_name_template = 'Tab {}'

    def __init__(self, figures=(), pos='N', parent=None):

        super().__init__(parent)
        self.tabs = QtWidgets.QTabWidget(self)
        #
        self._cid = None
        self._link_focus = False
        self._previous = -1
        #
        self.index_offset = 0
        self.pos = pos.upper()
        self._layout(pos)

        # resolve figures
        if isinstance(figures, abc.Sequence):
            items = itt.zip_longest((), figures)
        else:
            items = dict(figures or {}).items()

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
        self.tabs.setTabPosition(TAB_POS[pos])

        # if pos == 'W':
        #     space_tab = self._insert_spacer()

    def _insert_spacer(self):
        # add inactive spacer tab
        self.logger.debug('Adding inactive spacer tab.')
        space_tab = QtWidgets.QTabWidget(self)
        space_tab.setVisible(False)
        space_tab.setEnabled(False)
        self.tabs.addTab(space_tab, ' ')
        self.tabs.setTabEnabled(0, False)
        # tabs.setTabVisible(0, False)
        self.index_offset = 1
        return space_tab

    def __len__(self):
        return self.tabs.count() - self.index_offset

    def __getitem__(self, key):
        with ctx.suppress(NotImplementedError):
            return super().__getitem__(key)

        return self.tabs.widget(self._resolve_index(key))

    def __setitem__(self, tab_name, figure):
        if tab_name in self:
            raise NotImplementedError

        self.add_tab(tab_name, fig=figure)

    def __delitem__(self, key):
        self.tabs.removeTab(self._resolve_index(key))

    def keys(self):
        for i in range(self.index_offset, self.tabs.count()):
            yield self.tabs.tabText(i)

    def values(self):
        for i in range(self.index_offset, self.tabs.count()):
            yield self.tabs.widget(i)

    # ------------------------------------------------------------------------ #
    def _is_uniform(self):
        return len({tuple(_.keys()) for _ in self._children()}) == 1

    # ------------------------------------------------------------------------ #
    def _current_index(self):
        return self.tabs.currentIndex() - self.index_offset

    def _resolve_index(self, key):
        if isinstance(key, str):
            for i, trial in enumerate(self.keys(), self.index_offset):
                if key == trial:
                    return i

            raise KeyError(f'Could not resolve tab index {key!r}. '
                           f'Available tabs: {tuple(self.keys())}')

        if not isinstance(key, numbers.Integral):
            raise TypeError(f'Invalid type object ({key}) for indexing {self!r}.')

        n = len(self)
        if key >= n or key < -n:
            raise IndexError(f'Index {key} out of range for '
                             f'{self.__class__.__name__} with {n} tabs.')

        return (key % n) + self.index_offset

    def resolve_indices(self, *keys):
        node = self
        for key in keys:
            yield node._resolve_index(key)
            node = node[key]

    def _deresolve_indices(self, indices):
        node = self
        for i in indices:
            yield i - (0 if node._is_leaf() else node.index_offset)

    def _index_offsets(self):
        node = self
        while not node._is_leaf():
            yield node.index_offset
            node = next(node._children(), None)

    def _find(self, item):
        if (i := self.tabs.indexOf(item)) != -1:
            i -= self.index_offset
        return i

    # ------------------------------------------------------------------------ #
    def _active(self):
        if self.tabs.currentIndex() < self.index_offset:
            return None
        return self.tabs.currentWidget()

    def _inactive(self):
        return active._siblings() if (active := self._active()) else self.values()

    # ------------------------------------------------------------------------ #
    def _factory(self, name, fig, **kws):
        # create tab name if needed
        if name is None:
            name = self._tab_name_template.format(
                self.tabs.count() - self.index_offset + 1
            )

        # create figure if needed
        if isinstance(fig, abc.MutableMapping):
            fig = Figure(**fig, **kws)

        fig = fig or Figure(**kws)
        assert isinstance(fig, Figure)

        # if pyplot gui is active, make it close the figure
        if plt := sys.modules.get('matplotlib.pyplot'):
            plt.close(fig)

        # convert to str required by pyside
        return str(name), MplTabbedFigure(fig, parent=self)

    def add_tab(self, name=None, position=-1, *, fig=None, focus=False,
                **kws):
        """
        Dynamically add a tab with embedded matplotlib canvas.
        """
        name, obj = self._factory(name, fig, **kws)
        self._add_tab(name, obj, position, focus)

        return obj

    def _add_tab(self, name, obj, pos, focus):
        # add tab
        self.logger.debug('{!r} Adding tab {!r} at position {}.', self, name, pos)
        if pos == -1:
            self.tabs.addTab(obj, name)
        else:
            self.tabs.insertTab(pos, obj, name)

        if focus:
            index = self.tabs.currentIndex() + 1
            logger.debug('focussing on {}', index)
            self.tabs.setCurrentIndex(index)

    def remove_tab(self, key):
        return self.tabs.removeTab(self.tabs.indexOf(self._resolve_index(key)))

    def replace_tab(self, key, fig, focus=False, **kws):
        index = self._resolve_index(key)
        name = self.tabs.tabText(key)
        self.tabs.removeTab(index)
        tab = self.add_tab(name, index, fig=fig, focus=focus, **kws)
        self.tabs.setCurrentIndex(index)
        return tab

    # ------------------------------------------------------------------------ #
    def add_callback(self, func=None, *args, **kws):
        # add plot callback for all children
        if func and not callable(func):
            self.logger.debug('Invalid object for callback: {}', func)
            return

        # Connect function
        if self._cid:
            self.logger.debug('A callback is already active. Not connecting.', self)
            return

        self.logger.debug('{} connecting tab change callback.', self)
        self._cid = self.tabs.currentChanged.connect(self._on_change)

        # propagate down
        for node in self.values():
            node.add_callback(func, *args, **kws)

    def _on_change(self, *indices):
        self.logger.debug('Tab change to {} (internal)', indices)

        indices = tuple(self._deresolve_indices(indices))
        self.logger.debug('Tab change to {} (user)', indices)

        # focus
        if self._link_focus:
            self.match_sibling_focus(*indices)

            if self._depth() > 1:
                top = self
                for parent in self._ancestors():
                    if parent._is_uniform():
                        top = parent
                    else:
                        break

                # If the UI is composed of tabs all having the same substructure,
                # we co-focus the parent's siblings
                top = top._active()
                top.match_sibling_focus(*top._current_indices())

        # plot init for next active tab
        # i, *indices = indices
        # indices = (i - self.index_offset, *indices)
        fig = self[indices]
        if ((active := self in (active_branch := self._root()._active_branch()))
                and fig._is_active() and fig.plot):
            #
            names = self._root().tab_text((*self._index(), *indices))
            self.logger.debug(
                'Launching plot callback for active tab at index {}', names
            )
            fig._plot()

            if not fig._drawn:
                self.logger.debug('Drawing figure: {}', names)
                fig.canvas.draw()

            return True

        # Nothing done
        self.logger.opt(lazy=True).debug(
            'Callback did not execute since: {}',
            lambda: [f'{l} = {on}' for l, on in
                     dict(active=active,
                          active_branch=active_branch,
                          plot=fig.plot).items()
                     if not on])

        return False

    # ------------------------------------------------------------------------ #
    def set_focus(self, key, force_callback=True):
        self.logger.debug('Focus: {}. cid: {}, linking: {}',
                          key, self._cid, self._link_focus)
        target = self._resolve_index(key)
        if self.tabs.currentIndex() == target:
            if force_callback:
                # fire events even when tab changes to current
                self._on_change(target)
        else:
            self.tabs.setCurrentIndex(target)

    def link_focus(self):
        if self._cid:
            if self._link_focus:
                self.logger.debug('Focus matching already active on {}. Nothing to '
                                  'do here.', self)
                return

            self._link_focus = True
            return

        self.logger.debug('{} adding tab change callback {}.')
        self._cid = self.tabs.currentChanged.connect(self._on_change)
        self._link_focus = True

    def unlink_focus(self):
        if not (self._cid and self._link_focus):
            self.logger.debug('No focus matching active on {!r}. Nothing to do '
                              'here.', self)
            return

        self.logger.debug('Focus linking turned off for {}.', self)
        self._link_focus = False

    def match_sibling_focus(self, key):
        """Match focus (active tabs) between siblings."""

        self.logger.debug('Matching focus {!r}: {!r}', self, key)

        *current, _ = self._index()
        # self.logger.debug('Current: {}. Target: {}', [*current, _])

        # disonnect parent callbacks
        self.logger.debug('Unlinking focus at active toplevel.')
        root = self._root()
        top = root._active()
        top.unlink_focus()
        root.set_focus(*current, None)

        # focus = (*current, i)
        # target = tuple(top._active()._current_indices())
        self.logger.debug('Callback co-focussing {!r} siblings to: {}.',
                          top, key)
        for mgr in self._siblings():
            mgr.set_focus(key, force_callback=False)

        self.logger.debug('Reconnecting focus matching at active toplevel.')
        top.link_focus()

    # ------------------------------------------------------------------------ #
    def _tab_text(self, indices):

        tabs = self
        for i in indices:
            yield tabs.tabs.tabText(i + tabs.index_offset)
            tabs = tabs[i]

    def tab_text(self, indices):
        return tuple(self._tab_text(indices))

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

            filename = filename.resolve()
            logger.debug('Saving figure: {}')
            self[i].figure.savefig(filename, **kws)

    save_figures = save

    def _check_filenames(self, filenames):

        if isinstance(filenames, Path):
            filenames = str(filenames / '{}')

        n = self.tabs.count()
        if isinstance(filenames, abc.Sequence):
            if (m := len(filenames)) != n:
                raise ValueError(
                    f'Incorrect number of filenames {m}. There are {n} figure '
                    f'groups in this {self.__class__.__name__}.'
                )

            if isinstance(filenames, abc.MutableMapping):
                filenames = filenames.get

            return filenames

        if isinstance(filenames, abc.Iterable):
            return filenames

        if is_template_string(filenames):
            self.logger.debug('Saving {} figures with filename template: {!r}',
                              n, filenames)
            filenames = filenames.format

        if callable(filenames):
            # partial format string with dataset name
            return ((filenames(self.tabs.tabText(i))) for i in range(n))

        raise TypeError(f'Invalid filenames: {filenames!r}')


class NestedTabsManager(TabManager):

    _tab_name_template = 'Group {}'
    _factory_kws = {}

    def __new__(cls, figures, *args, **kws):
        # catch for figures being 1d sequence or mapping, use plain TabManager
        if figures and depth(figures) == 1:
            return TabManager(figures)

        return super().__new__(cls)

    def __init__(self, figures=(), pos='N', parent=None):

        pos, *rest = pos
        self._factory_kws = {'pos': ''.join(rest) or pos}

        # initialise empty
        TabManager.__init__(self, (), pos, parent)

        # tabs switches the group being displayed in central panel which may
        # itself be NestedTabsManager or TabManager at lowest level
        figures = dict(figures or ())
        for name, figs in figures.items():
            self.add_group(name, figs)

        if self.plot:
            self.logger.debug('Detected figure initializer method {}. '
                              'Connecting group tab change callback to this '
                              'method.', self.plot)
            self.add_callback(self, self.plot)

        if figures:
            self.link_focus()

    # ------------------------------------------------------------------------ #
    def _factory(self, keys, fig, **kws):

        assert (n := len(keys))

        if n == 1:
            return super()._factory(*keys, fig, **kws)

        # add nested tabs
        gid, *_ = keys
        kls = TabManager if (n == 2) else type(self)
        return str(gid), kls(fig, parent=self, **self._factory_kws)

    def _add_tab(self, name, obj, pos, focus):
        if (isinstance(obj, TabManager)
                and (self.pos in 'EW')
                and obj.pos == 'N'
                and not self.index_offset):
            self._insert_spacer()

        super()._add_tab(name, obj, pos, focus)

    def add_tab(self, *keys, fig=(), position=-1, focus=None, **kws):
        """
        Add a (nested) tab.
        """
        self.logger.debug('Adding tab: {!r} at position {}.', keys, position)
        kws = dict(position=position, focus=focus, **kws)

        gid, *other = keys
        gid = str(gid)  # required by pyside
        if gid not in self:
            # new tab/group
            focus = focus or (self.tabs.count() == self.index_offset)
            tab = super().add_tab(keys, **kws)

        # add to existing group
        if other:
            return self[gid].add_tab(*other, fig=fig, **kws)

        return tab

    def add_group(self, name=None, figures=(), position=-1):
        """
        Add a (nested) tab group.
        """
        nested = type(self)(figures, parent=self)
        super()._add_tab(name,
                         nested,
                         position,
                         self.tabs.count() == self.index_offset)
        return nested

    # ------------------------------------------------------------------------ #
    def _on_change(self, index):
        # This will run *before* qt switches the tabs on mouse click
        self.logger.debug('Tab change callback {}: index = {}.', self, index)

        upcoming = index - self.index_offset

        # disconnect callback from previously active tab
        if self._previous == -1:  # first change
            self.logger.debug('First tab change at level {}.', self._level())
            # current = [-1] * (h := self[upcoming]._height())
            target = self[upcoming]._index_offsets()
        else:
            # turn of the focus linking for inactive groups else infinite loop
            self.logger.debug('Remove focus linking for previously active tab.')
            previous = self.tabs.widget(self._previous)
            previous.unlink_focus()

            # current = list(previous._current_indices())
            target = list(self[upcoming]._current_indices())

        # target indices wrt to GUI tabs (including posible spacer at position 0)
        new = (upcoming, *target)
        # old = (self._previous, *current)

        # self.logger.debug(f'{old = }, {new = }')
        # indices = [index, *target]
        if len(self):
            # if len(current) == self[upcoming]._height():
            #     self.logger.info('PING!!')
            #     indices += current
            # logger.debug(f'{indices = }')
            super()._on_change(*new)

        #
        self._previous = index

    # ------------------------------------------------------------------------ #
    def set_focus(self, *indices, force_callback=True):

        if not indices:
            return

        #
        i, *below = indices

        # None can be used as sentinel to mean keep focus the same below
        if i is None:
            return

        self.logger.debug('{!r} focussing on {}', self, indices)

        i = self._resolve_index(i)
        self.tabs.setCurrentIndex(i)   # NOTE: will trigger _on_change
        self._previous = i

        if not self._link_focus and (active := self._active()):
            itr = [active]
        else:
            itr = self.values()

        for mgr in itr:
            mgr.set_focus(*below, force_callback=force_callback)

    def match_sibling_focus(self, *indices):

        self.logger.debug('Matching focus {!r}: {!r}', self, indices)

        # set focus of the new target group same as previous
        i, *new = indices

        target = self[i]
        self.logger.debug('{!r} setting target manager {} focus to: {}',
                          self, i, new)

        # if list(target._current_indices()) != new:
        target.set_focus(*new, force_callback=False)

        #  also set focus of siblings
        # indices = i, *new
        self.logger.debug('{!r} setting sibling managers focus to: {}',
                          self, indices)
        h = self._height()
        for mgr in self._siblings():
            if mgr._height() == h:
                mgr.set_focus(*indices, force_callback=False)

        # add focus linking callback to new group
        target.link_focus()

    def link_focus(self, *indices):
        super().link_focus()
        if indices:
            i, *indices = indices
            target = self[i]
        else:
            target = self._active()

        if target:
            target.link_focus(*indices)

    def unlink_focus(self, *indices):
        super().unlink_focus()
        if indices:
            i, *indices = indices
            target = self[i]
        else:
            target = self._active()

        if target:
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


class MplTabGUI(QtWidgets.QMainWindow, LoggingMixin):

    plot = None

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

        # Tab method aliases
        self.add_tab = self.tabs.add_tab
        self.set_focus = self.tabs.set_focus
        self.add_callback = self.tabs.add_callback

        # Plotting callback
        if self.plot:
            self.logger.debug('Detected plot method. Adding callback.')
            self.add_callback(self.plot)

    def __repr__(self):
        name = f'{self.__class__.__name__}: '
        if (title := self.windowTitle()) != name:
            name += repr(title)
        return f'<{name}, levels={self.tabs._height()}, pos={self.tabs.pos}>'

    def __getitem__(self, key):
        return self.tabs[key]

    def __setitem__(self, key, fig):
        self.tabs[key] = fig

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.show()

    def link_focus(self):
        pass  # only meaningful for MultiTab

    def show(self):
        # This is needed so the initial plot is done when launching the gui
        mgr = self.tabs
        if len(mgr) and mgr._active() is None:
            # an inactive tab is selected??
            logger.debug('Focussing before show.')
            mgr.set_focus(*([0] * mgr._height()))
        else:
            mgr._on_change(mgr.tabs.currentIndex())

        return super().show()


# aliases
MplTabs = MplTabGui = MplTabGUI


class MplMultiTab(MplTabGUI):
    """
    Nested tab gui for displaying matplotlib figures.
    """

    def __init__(self, figures=(), title=None, pos='N',
                 manager=NestedTabsManager,
                 parent=None, **kws):
        #
        super().__init__(figures, title, pos, manager, parent, **kws)

        # self.add_group = self.tabs.add_group

    def link_focus(self):
        self.tabs.link_focus()


class MplMultiTab2D(MplMultiTab):
    def __init__(self, figures=(), title=None, pos='W', parent=None):
        super().__init__(figures, title, pos, parent=parent)
