import sys
from types import CodeType
from typing import Any, ClassVar, final
from pydantic import ValidationError, validate_arguments

if __name__ == '__main__':
    def sample_func(a: int):
        pass

    func = validate_arguments(sample_func)

    try:
        # validate_arguments(sample_func("a"))
        # sample_func("a")
        func("a")  # type: ignore
    except ValidationError as e:
        print(e.json())

    # sample_func = Fu()

    # setattr(sample_func, '__getitem__', lambda name: print(name))

    # setattr(sample_func, '__getattr__', lambda name: print(name))

    # print(sample_func.abc)
    # print(type(sample_func))
