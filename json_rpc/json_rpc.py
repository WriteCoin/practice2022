from functools import partial
import inspect
from typing import Any, Awaitable, Optional
from pydantic import ValidationError
from json_rpc.model import (
    Error,
    FuncType,
    InternalError,
    InvalidParamsError,
    InvalidRequestError,
    MethodNotFoundError,
    ParamType,
    ParseError,
    ProcRequest,
    ResponseError,
    ResponseResult,
)
from json_rpc.socket_base.send_recv import RecvType, SendType
from accessify import protected


class JsonRPC:
    default_version = "2.0"
    default_encondig = "UTF-8"
    default_request = ProcRequest(
        jsonrpc=default_version, id=None, method="", params=[]
    )

    def __init__(self, send: SendType, recv: RecvType, addr: Optional[str] = None):
        self.__send = send
        self.__recv = recv
        self.__addr = addr
        self.__functions: dict[str, FuncType] = {}
        self.__id = 0

    def get_addr(self):
        return "" if self.__addr is None else f"{self.__addr}: "

    @protected
    @staticmethod
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

    @protected
    @staticmethod
    def validate_func_args(func: FuncType, args: ParamType):
        func_spec = inspect.getfullargspec(func)
        anno_types = func_spec.annotations
        arg_types = {k: v for k, v in anno_types.items() if k != "return"}
        for i, (key, anno) in enumerate(arg_types.items()):
            value = args[i] if isinstance(args, list) else args[key]
            if not issubclass(type(value), anno):
                raise ValueError

    @protected
    async def send(self, message: str, request: ProcRequest = default_request):
        b_message = message.encode(self.default_encondig)
        try:
            await self.__send(b_message)
        except:
            await self.send_error(InternalError, request)

    @protected
    async def recv(self, request: ProcRequest = default_request) -> str | None:
        try:
            data = await self.__recv()
        except:
            await self.send_error(InternalError, request)
            return None
        else:
            return data.decode(self.default_encondig)

    @protected
    async def send_error(self, err: Error, request: ProcRequest = default_request):
        response = ResponseError(
            jsonrpc=request.json_rpc, error=err, id=request.id
        ).json(by_alias=True)
        print(f"{self.get_addr()} Response with error: {response}")
        await self.send(response, request)

    @protected
    async def send_result(self, result: Any, request: ProcRequest = default_request):
        response = ResponseResult(
            jsonrpc=request.json_rpc, result=result, id=request.id
        ).json(by_alias=True)
        print(f"{self.get_addr()} Response: {response}")
        await self.send(response, request)

    def register(self, func=None, *, name: str | None = None):
        if func is None:
            return partial(self.register, name=name)
        key = self.get_func_name(func) if name is None else name
        self.__functions[key] = func

        async def wrapper(*args, **kwargs):
            return (
                await func(*args, **kwargs)
                if isinstance(func, Awaitable)
                else func(*args, **kwargs)
            )

        return wrapper

    async def call(self, func_name: str, args: ParamType | Any) -> Any:
        try:
            self.__id += 1
            params = (
                args if isinstance(args, list) or isinstance(args, dict) else [args]
            )
            request = ProcRequest(
                jsonrpc=self.default_version,
                method=func_name,
                params=params,
                id=self.__id,
            )
            await self.send(request.json(by_alias=True), request)
            result_json = await self.recv(request)
            try:
                return ResponseError.parse_raw(result_json).error
            except:
                return ResponseResult.parse_raw(result_json).result
        except:
            await self.send_error(InternalError)

    def schema(self) -> dict:
        return {}

    async def run(self):
        try:
            data = await self.recv()
            try:
                print(f"{self.get_addr()} Request: {data}")
                request = ProcRequest.parse_raw(data)
            except ValidationError as e:
                await self.send_error(InvalidRequestError)
                return
            except Exception:
                await self.send_error(ParseError)
                return
            try:
                func = self.__functions[request.method]
            except KeyError:
                await self.send_error(MethodNotFoundError, request)
                return
            try:
                self.validate_func_args(func, request.params)
            except:
                await self.send_error(InvalidParamsError, request)
                return
            result = (
                await func(*request.params)
                if inspect.iscoroutinefunction(func)
                else func(*request.params)
                if isinstance(request.params, list)
                else await func(**request.params)
                if inspect.iscoroutinefunction(func)
                else func(**request.params)
            )
            if issubclass(type(result), type(Error)):
                await self.send_error(result)
        except:
            await self.send_error(InternalError)
        else:
            await self.send_result(result, request)
