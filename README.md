# mpl-multitab

> Tabbed figure manager for matplotlib using pyQt

<!-- 
TODO
[![Build Status](https://travis-ci.com/astromancer/mpl-multitab.svg?branch=main)](https://travis-ci.com/astromancer/mpl-multitab)
[![Documentation Status](https://readthedocs.org/projects/mpl-multitab/badge/?version=latest)](https://mpl-multitab.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/mpl-multitab.svg)](https://pypi.org/project/mpl-multitab)
[![GitHub](https://img.shields.io/github/license/astromancer/mpl-multitab.svg?color=blue)](https://mpl-multitab.readthedocs.io/en/latest/license.html)
 -->

Ever struggle to navigate between a myriad of open matplotlib figures? I know
your pain...

`mpl-multitab` is a simple application that allows you to embed mutliple figures
in a tabbed figure manager, keeping everything neatly in one place.


# Install
Using pip:
```shell
pip install mpl-multitab
```
Alternatively, clone the repo, then run the [`setup.py`](/setup.py) script
```shell
git clone https://github.com/astromancer/mpl-multitab.git
cd mpl-multitab
python setup.py install
```


# Use

## Interactive use
At the start of your `jupyter notebook`, or `ipython` session, run the line
magic to set the qt backend
```
%matplotlib qt5
```
Then
```python
# Example use of MplTabs
# Create a scatter plot of `n` random xy-points for each colour
from mpl_multitab import MplTabs


n = 100
colours = 'rgb'
#
ui = MplTabs()
for c in colours:
    fig = ui.add_tab(c)
    ax = fig.subplots()
    ax.scatter(*np.random.randn(2, n), color=c)

ui.set_focus(0)
ui.show()
```


![Demo GIF can be viewed at https://github.com/astromancer/mpl-multitab/blob/main/tests/demo.gif](/tests/demo.gif)


## In a script
```python
# Example using `MplTabs` in a standalone script.
import sys
from mpl_multitab import MplTabs


n = 100
colours = 'rgb'

app = QtWidgets.QApplication(sys.argv)
ui = MplTabs()
for c in colours:
    fig = ui.add_tab(c)
    ax = fig.subplots()
    ax.scatter(*np.random.randn(2, n), color=c)

ui.set_focus(0)
ui.show()
sys.exit(app.exec_())
```



## Groups of Figures

You can group multiple related figures together using the `MplMultiTab` class.
This is useful for visualising, for example, multiple datasets each having
multiple observations.

```python
# Example use for MplMultiTab for 2d collection of data sets
# This dataset is equal number observations per dataset. This need not be the
# case in general.
import itertools as itt
from mpl_multitab import MplMultiTab


n = 100
colours = 'rgb'
markers = '123'
#
ui = MplMultiTab(pos='W')
for c, m in itt.product(colours, markers):
    fig = ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')
    ax = fig.subplots()
    ax.scatter(*np.random.randn(2, n), color=c, marker=f'${m}$')

ui.set_focus(0, 0)
ui.link_focus()
ui.show()
```




![Demo GIF 2 can be viewed at https://github.com/astromancer/mpl-multitab/blob/main/tests/demo2.gif](/tests/demo2.gif)

In this example all the datasets contain the same number of obervations, but
this need not be the case in general.



## Performance considerations - Delayed plotting

Creating all the figures in one go at startup may take unreasonably long if you
have many figures or lots of data. This can be amortised by delaying the
plotting of individual figures until the user switches to that tab. This is 
demonstrated in the following example:

```python
# MplMultiTab with delayed plotting
import itertools as itt
from mpl_multitab import MplMultiTab


n = 10000
colours = 'rgb'
markers = '123'
#
# first create the figures, but don't do the plotting just yet
ui = MplMultiTab(pos='W')
for c, m in itt.product(colours, markers):
    ui.add_tab(f'Dataset {c.upper()}', f'Observation {m}')

# create plotting function
def plot(fig, indices):
    print('Doing plot:', indices)
    i, j = indices
    ax = fig.subplots()
    return ax.scatter(*np.random.randn(2, n),
                      color=colours[i],
                      marker=f'${markers[j]}$')

ui.add_callback(plot)   # add your plot worker
ui.set_focus(0, 0)      # this will trigger the plotting for group 0 tab 0
ui.link_focus()         # keep same tab in focus across group switches
ui.show()
```



## Arbitrary nesting

The `MplMultiTab` class is able to handle nested tabs to any depth. The
following example demonstrates the usage pattern for datasets grouped by 3
different features. The same pattern can be used to handle data of any
dimensionality. Tabs all the way down!

```python
# MplMultiTab with 3 tab levels
import itertools as itt
from mpl_multitab import MplMultiTab


n = 10
colours = 'rgb'
markers = 'H*P'
hatch = ('xx', '**')
#
ui = MplMultiTab()
for c, m, h in itt.product(colours, markers, hatch):
    # use "&" to tag letters for keyboard shortcuts which select the tab
    #   eg: using "&x" somewhere in the tab name means you can select it with "Alt+x"
    fig = ui.add_tab(f'Colour &{c.upper()}', f'Marker &{m}', f'Hatch &{h}')
    ax = fig.subplots()
    ax.scatter(*np.random.randn(2, n),
               s=750, marker=m, hatch=h,
               edgecolor=c,  facecolor='none')

ui.link_focus()             # keep same tab in focus across group switches
ui.set_focus(0, 0, 0)
ui.show()
```




![Demo GIF 3 can be viewed at https://github.com/astromancer/mpl-multitab/blob/main/tests/demo3.gif](/tests/demo3.gif)


<!-- For more examples see [Documentation]() -->

<!-- # Documentation -->


# Test

Testing is done with [pytest-qt](https://github.com/pytest-dev/pytest-qt/). 
This will run through all examples in the
 [examples](https://github.com/astromancer/mpl-multitab/tree/main/src/mpl_multitab/examples)
module:
```shell
pytest -vs tests/test_multitab.py
```

# Contribute
Contributions are welcome!

1. [Fork it!](https://github.com/astromancer/mpl-multitab/fork)
2. Create your feature branch\
    ``git checkout -b feature/rad``
3. Commit your changes\
    ``git commit -am 'Add some cool feature 😎'``
4. Push to the branch\
    ``git push origin feature/rad``
5. Create a new Pull Request

# Contact

* e-mail: hannes@saao.ac.za

<!-- ### Third party libraries
 * see [requirements.txt](https://github.com/username/sw-name/blob/master/requirements.txt) files -->

# License

* see [LICENSE](https://github.com/astromancer/mpl-multitab/blob/main/LICENSE)


# Version
This project uses [semantic versioning](https://semver.org/). The latest version
is
* 1.0.0

