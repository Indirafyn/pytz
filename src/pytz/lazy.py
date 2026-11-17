from threading import RLock
try:
    from collections.abc import Mapping as DictMixin
except ImportError:  # Python < 3.3
    try:
        from UserDict import DictMixin  # Python 2
    except ImportError:  # Python 3.0-3.3
        from collections import Mapping as DictMixin


# With lazy loading, we might end up with multiple threads triggering
# it at the same time. We need a lock.
_fill_lock = RLock()


def _fill_if_needed(instance):
    # Refactoring: centralize the repeated thread-safe lazy initialization.
    if instance.data is None:
        _fill_lock.acquire()
        try:
            if instance.data is None:
                instance._fill()
        finally:
            _fill_lock.release()


class LazyDict(DictMixin):
    """Dictionary populated on first use."""
    data = None

    def __getitem__(self, key):
        _fill_if_needed(self)
        return self.data[key.upper()]

    def __contains__(self, key):
        _fill_if_needed(self)
        return key in self.data

    def __iter__(self):
        _fill_if_needed(self)
        return iter(self.data)

    def __len__(self):
        _fill_if_needed(self)
        return len(self.data)

    def keys(self):
        _fill_if_needed(self)
        return self.data.keys()


def _lazy_container(container_type, props, fill_iter, populate):
    # Refactoring: share the lazy proxy factory used by lists and sets.
    if fill_iter is None:
        return container_type()

    class LazyContainer(container_type):
        pass

    pending = [fill_iter]

    def lazy(name):
        def _lazy(self, *args, **kw):
            _fill_lock.acquire()
            try:
                if pending:
                    populate(self, pending.pop())
                    for method_name in props:
                        delattr(LazyContainer, method_name)
            finally:
                _fill_lock.release()
            return getattr(container_type, name)(self, *args, **kw)
        return _lazy

    for name in props:
        setattr(LazyContainer, name, lazy(name))
    return LazyContainer()


class LazyList(list):
    """List populated on first use."""

    _props = [
        '__str__', '__repr__', '__unicode__',
        '__hash__', '__sizeof__', '__cmp__',
        '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',
        'append', 'count', 'index', 'extend', 'insert', 'pop', 'remove',
        'reverse', 'sort', '__add__', '__radd__', '__iadd__', '__mul__',
        '__rmul__', '__imul__', '__contains__', '__len__', '__nonzero__',
        '__getitem__', '__setitem__', '__delitem__', '__iter__',
        '__reversed__', '__getslice__', '__setslice__', '__delslice__']

    def __new__(cls, fill_iter=None):
        return _lazy_container(
            list, cls._props, fill_iter,
            lambda instance, values: list.extend(instance, values))

# Not all versions of Python declare the same magic methods.
# Filter out properties that don't exist in this version of Python
# from the list.
LazyList._props = [prop for prop in LazyList._props if hasattr(list, prop)]


class LazySet(set):
    """Set populated on first use."""

    _props = (
        '__str__', '__repr__', '__unicode__',
        '__hash__', '__sizeof__', '__cmp__',
        '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',
        '__contains__', '__len__', '__nonzero__',
        '__getitem__', '__setitem__', '__delitem__', '__iter__',
        '__sub__', '__and__', '__xor__', '__or__',
        '__rsub__', '__rand__', '__rxor__', '__ror__',
        '__isub__', '__iand__', '__ixor__', '__ior__',
        'add', 'clear', 'copy', 'difference', 'difference_update',
        'discard', 'intersection', 'intersection_update', 'isdisjoint',
        'issubset', 'issuperset', 'pop', 'remove',
        'symmetric_difference', 'symmetric_difference_update',
        'union', 'update')

    def __new__(cls, fill_iter=None):
        return _lazy_container(
            set, cls._props, fill_iter,
            lambda instance, values: [
                set.add(instance, value) for value in values])

# Not all versions of Python declare the same magic methods.
# Filter out properties that don't exist in this version of Python
# from the list.
LazySet._props = [prop for prop in LazySet._props if hasattr(set, prop)]
