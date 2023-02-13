# std
import inspect
import functools as ftl
from types import MethodType

# third-party
from loguru import logger


class LoggingMixin:
    class Logger:

        # use descriptor so we can access the logger via logger and cls().logger
        # Making this attribute a property also avoids pickling errors since
        # `logging.Logger` cannot be picked

        parent = None
        """This attribute allows you to optionally set the parent dynamically 
        which is sometimes useful"""

        # @staticmethod
        # def get_name(fname, parent):

        @staticmethod
        def add_parent(record, parent):
            """Prepend the class name to the function name in the log record."""
            # TODO: profile this function to see how much overhead you are adding
            fname = record['function']

            if fname.startswith('<cell line:'):
                # catch interactive use
                return

            parent = get_defining_class(getattr(parent, fname))
            parent = '' if parent is None else parent.__name__
            record['function'] = f'{parent}.{fname}'

        def __get__(self, obj, kls=None):
            return logger.patch(
                ftl.partial(self.add_parent, parent=(kls or type(obj)))
            )

    logger = Logger()


def get_defining_class(method: MethodType):
    """
    Get the class that defined a method.

    Parameters
    ----------
    method : types.MethodType
        The method for which the defining class will be retrieved.

    Returns
    -------
    type
        Class that defined the method.
    """
    # source: https://stackoverflow.com/questions/3589311/#25959545

    # handle bound methods
    if inspect.ismethod(method):
        for cls in inspect.getmro(method.__self__.__class__):
            if cls.__dict__.get(method.__name__) is method:
                return cls
        method = method.__func__  # fallback to __qualname__ parsing

    # handle unbound methods
    if inspect.isfunction(method):
        name = method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        cls = getattr(inspect.getmodule(method), name)
        if isinstance(cls, type):
            return cls

    # handle special descriptor objects
    return getattr(method, '__objclass__', None)
