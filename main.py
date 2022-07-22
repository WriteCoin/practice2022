import json
import sys
import traceback
from types import CodeType
from typing import Any, ClassVar, TypedDict, final
from pydantic import ValidationError, validate_arguments


class A():
    a: int

    def __init__(self, a: int) -> None:
        self.a = a
        self.__class__.a = a

    @classmethod
    def method(cls):
        for subclass in cls.__subclasses__():
            print(subclass.a)


class B(A):
    pass


class Values(TypedDict):
    val1: int
    val2: str


def test2():
    try:
        # a = 1 / 0
        json.loads("{ a: n }")
    except json.JSONDecodeError as e:
        d = e.__dict__
        d["traceback"] = traceback.format_exc()
        print(d)
        # print("JSON Error", e)
        # print({
        #     e.__dict__,
        #     traceback.format_exc()
        # })
        # print(e.__str__())
    except Exception as e:
        print(e.args)
        print(e.__dict__)


def test1():
    def sample_func(a: int):
        pass

    func = validate_arguments(sample_func)

    try:
        # validate_arguments(sample_func("a"))
        # sample_func("a")
        func("a")  # type: ignore
    except ValidationError as e:
        # print(e.raw_errors)
        # print(e.model)
        print(e.errors())
        # print(e.json())
        # err = ValidationError(e.raw_errors, e.model)
        # print(err.json())

    # sample_func = Fu()

    # setattr(sample_func, '__getitem__', lambda name: print(name))

    # setattr(sample_func, '__getattr__', lambda name: print(name))

    # print(sample_func.abc)
    # print(type(sample_func))


class C:
    a: int

    def __init__(self, a: int) -> None:
        self.__class__.a = a
        self.a = a


if __name__ == '__main__':
    # print(A.__subclasses__())

    # print(json.dumps(Values(val1=1, val2="a")))

    # c = C(1)

    # print(c.a)
    # print(C.a)

    # d = {}
    # try:
    #     d["a"]
    # except KeyError as e:
    #     print(traceback.format_exc())

    a = A(5)

    a.method()
    # for subclass in A.__subclasses__():
    #     print(subclass.a)
