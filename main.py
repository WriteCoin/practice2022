import sys
from types import CodeType
from typing import Any, ClassVar, final


@final
class _Cella:
    __hash__: ClassVar[None]  # type: ignore[assignment]
    cell_contents: Any

# Doesn't exist at runtime, but deleting this breaks mypy. See #2999


@final
class Fu:
    # Make sure this class definition stays roughly in line with `types.FunctionType`
    @property
    def __closure__(self) -> tuple[_Cella, ...] | None: ...
    __code__: CodeType
    __defaults__: tuple[Any, ...] | None
    __dict__: dict[str, Any]
    @property
    def __globals__(self) -> dict[str, Any]: ...
    __name__: str
    __qualname__: str
    __annotations__: dict[str, Any]
    __kwdefaults__: dict[str, Any]
    if sys.version_info >= (3, 10):
        @property
        def __builtins__(self) -> dict[str, Any]: ...

    __module__: str
    # mypy uses `builtins.function.__get__` to represent methods, properties, and getset_descriptors so we type the return as Any.
    def __get__(self, obj: object | None, type: type | None = ...) -> Any: ...

    def __getitem__(self, name):
        print(name)

    def __getattr__(self, name):
        return self[name]


if __name__ == '__main__':
    def sample_func():
        pass

    # sample_func = Fu()

    # setattr(sample_func, '__getitem__', lambda name: print(name))

    # setattr(sample_func, '__getattr__', lambda name: print(name))

    # print(sample_func.abc)
    # print(type(sample_func))
