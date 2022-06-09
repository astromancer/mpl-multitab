# mpl-multitab

> Tabbed figure manager for matplotlib using pyQt

<!-- 
TODO
[![Build Status](https://travis-ci.com/astromancer/mpl-multitab.svg?branch=master)](https://travis-ci.com/astromancer/mpl-multitab)
[![Documentation Status](https://readthedocs.org/projects/mpl-multitab/badge/?version=latest)](https://mpl-multitab.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/mpl-multitab.svg)](https://pypi.org/project/mpl-multitab)
[![GitHub](https://img.shields.io/github/license/astromancer/mpl-multitab.svg?color=blue)](https://mpl-multitab.readthedocs.io/en/latest/license.html)
 -->

Ever struggle to navigate between a million open figures. I know your pain...

`mpl-multitab` is a simple application that allows you to embed mutliple figures
in a tabbed figure manager. 


# Install
Clone the repo, then run the setup.py script
```shell
git clone https://github.com/astromancer/mpl-multitab.git
cd mpl-multitab
python setup.py
```

# Use

## Interactive use
At the start of your `jupyter notebook`, or `ipython` session, run the line magic to set the qt5 backend
```
%matplotlib qt5
```
Then
```python
from mpl_multitab import MplMultiTab


ui = MplMultiTab()

n = 100
colours = 'rgb'
for c in colours:
    fig, ax = plt.subplots()
    ax.scatter(*np.random.randn(2, n), color=c)
    ui.add_tab(fig, c)
ui.show()
```

![Demo GIF](/tests/demo.gif)


## In a script:
```python
import sys
from mpl_multitab import MplMultiTab, QtWidgets


app = QtWidgets.QApplication(sys.argv)
ui = MplMultiTab()

n = 100
colours = 'rgb'
for c in colours:
    fig, ax = plt.subplots()
    ax.scatter(*np.random.randn(2, n), color=c)
    ui.add_tab(fig, c)
ui.show()
sys.exit(app.exec_())
```

<!-- ![Example Image](https://github.com/astromancer/mpl-multitab/blob/master/tests/images/example_0.png "Example Image") -->


<!-- For more examples see [Documentation]() -->

<!-- # Documentation -->


# Test

<!-- The [`test suite`](./tests) contains further examples of how
`mpl-multitab` can be used.  Testing is done with `pytest`: -->
Current [tests](/tests) are just the examples above
```shell
python test_multitab.py
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
 * see [LIBRARIES](https://github.com/username/sw-name/blob/master/LIBRARIES.md) files -->

# License

* see [LICENSE](https://github.com/astromancer/mpl-multitab/blob/master/LICENSE)


# Version
This project uses [semantic versioning](https://semver.org/). The 
latest version is
* 0.0.1

