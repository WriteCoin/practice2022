from functools import partial
import inspect
from typing import Any, Awaitable, Callable, Literal, TypeAlias
from unicodedata import decimal
from pydantic import BaseModel
from practice2022.json_rpc.socket_base.send_recv import RecvType, SendType


FuncType: TypeAlias = Awaitable[Callable] | Callable

ParamType: TypeAlias = list[Any] | dict[str, Any]


class ProcRequest(BaseModel):
    method: str
    params: ParamType


class ResponseWithError(BaseModel):
    error: dict[Literal["message"], str]


class Response(BaseModel):
    result: Any


def get_func_name(func: FuncType) -> str:
    func_full_path = str(func).split(" ")[1]
    if func_full_path.find(".<locals>.") != -1:
        paths_to_func = func_full_path.split(".<locals>.")
        path_to_func = paths_to_func[len(paths_to_func) - 1]
    else:
        path_to_func = func_full_path
    func_parts = path_to_func.split(".")
    name_func = func_parts[len(func_parts) - 1]
    return name_func


def validate_func_args(func: FuncType, args: ParamType):
    func_spec = inspect.getfullargspec(func)
    anno_types = func_spec.annotations
    arg_types = {k: v for k, v in anno_types.items() if k != "return"}
    for i, (key, anno) in enumerate(arg_types.items()):
        value = args[i] if isinstance(args, list) else args[key]
        if not issubclass(type(value), anno):
            raise ValueError


class JsonRPC:
    def __init__(self, send: SendType, recv: RecvType):
        self.__send = send
        self.__recv = recv
        self.__functions: dict[str, FuncType] = {}

    def register(self, func=None, *, name: str | None = None):
        if func is None:
            return partial(self.register, name=name)
        key = get_func_name(func) if name is None else name
        self.__functions[key] = func

        async def wrapper(*args, **kwargs):
            return (
                await func(*args, **kwargs)
                if isinstance(func, Awaitable)
                else func(*args, **kwargs)
            )

        return wrapper

    def call(self, data: ProcRequest) -> Any:
        pass

    def schema(self) -> dict:
        return {}

    async def run(self):
        response = None
        try:
            bytes = await self.__recv()
            data = bytes.decode("UTF-8")
            request = ProcRequest.parse_raw(data)
            func = self.__functions[request.method]
            validate_func_args(func, request.params)
            result = (
                func(*request.params)
                if isinstance(request.params, list)
                else func(**request.params)
            )
        except Exception as err:
            error_data = {"error": {"message": str(err)}}
            response = ResponseWithError(**error_data)
        else:
            result_data = {"result": result}
            response = Response(**result_data)
        await self.__send(response.json().encode("UTF-8"))
