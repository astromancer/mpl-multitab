# std
import inspect, stat
import operator as op
import textwrap as txw
from pathlib import Path
from collections import defaultdict

# third-party
from mpl_multitab import examples


class Example:
    __slots__ = ('comment', 'imports', 'variables', 'prelim', 'code', 'show')

    def __init__(self, **kws):
        for key in ('self', 'kws', '__class__'):
            kws.pop(key, None)

        kws.setdefault('show', 'ui.show()')
        kws.setdefault('prelim', '#')
        for key in type(self).__slots__:
            setattr(self, key, kws.get(key, ''))

    def __str__(self) -> str:
        return txw.dedent(
            '''\
            ```python
            {body}
            ```
            '''
        ).format(
            body='\n'.join(filter(None, op.attrgetter(*self.__slots__)(self)))
        )

    def clone(self):
        return type(self)(**{key: getattr(self, key) for key in self.__slots__})


def get_variables(func):
    defaults = func.__defaults__
    names = func.__code__.co_varnames[:func.__code__.co_argcount]
    return names, defaults


def get_imports(code):
    imports = ''
    if 'itt.' in code:
        imports = 'import itertools as itt\n'
    i = code.index('ui = ')
    j = code.index('(', i)
    imports += f'from mpl_multitab import {code[i + 5:j]}\n\n'
    return imports


example_code = defaultdict(dict)
for i in ('1', '2', 'n'):
    for f in (f'{i}d', 'delay_draw', ):
        source_code_lines, start_line_nr = inspect.getsourcelines(
            func := op.attrgetter(f'_{i}d.example_{f}')(examples)
        )

        lines = source_code_lines[1:-1]
        for s, line in enumerate(lines):
            if not line.lstrip().startswith('#'):
                break

        example_code[f'{i}d'][f] = Example(
            comment=txw.dedent(''.join(lines[:s])).strip(),
            variables='\n'.join(map('{} = {!r}'.format, *get_variables(func))),
            code=(code := txw.dedent(''.join(lines[s:])).strip()),
            imports=get_imports(code),
        )

        # example_code[f'_{i}'][f] = '\n'.join((variables, '', code, 'ui.show()')).strip()
        # example_code[f'_{i}'][f'{f}_comment'] =

scripting = example_code['1d']['1d'].clone()
scripting.comment = '# Example using `MplTabs` in a standalone script.'
scripting.imports = f'import sys\n{scripting.imports}'
scripting.prelim = '\napp = QtWidgets.QApplication(sys.argv)'
scripting.show += '\nsys.exit(app.exec_())'
example_code['1d']['scripting'] = scripting

# print(pp.pformat(example_code, rhs=str))
stub = (Path(__file__).parent / 'README.stub')
readme = stub.with_suffix('.md')
readme.chmod(stat.S_IWUSR)
readme.write_text(stub.read_text().format(EXAMPLES=example_code))
readme.chmod(stat.S_IRUSR)
