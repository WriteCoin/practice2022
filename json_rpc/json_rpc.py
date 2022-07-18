import asyncio
from contextlib import asynccontextmanager
from functools import partial
import inspect
import json
import threading
import traceback
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Literal, Mapping, Optional, Tuple, Union
from unittest import FunctionTestCase
from pydantic import ValidationError
from json_rpc.model import (
    BatchParam,
    BatchRequest,
    Error,
    FuncSchema,
    FuncType,
    InternalError,
    InternalErrorException,
    InvalidParamsError,
    InvalidRequestError,
    JsonRpcModel,
    MethodNotFoundError,
    ParamType,
    ParseError,
    ProcRequest,
    RequestResult,
    ResponseError,
    ResponseResult,
)
from json_rpc.socket_base.send_recv import (
    ClientRecvType,
    ClientSendType,
    SendType,
    RecvType,
    Token,
)


def notification(
    func_name: str,
    params: Union[ParamType, Any]
) -> Tuple[str, Union[ParamType, Any], Literal[False]]:
    return (func_name, params, False)


def new_class():
    return type('notify', (object, ), dict())


def get_args(*args, **kwargs):
    return [*args] if len(args) else {**kwargs}


class aobject(object):
    """Inheriting this class allows you to define an async __init__.

    So you can create objects by doing something like 'await MyClass(params)'
    """
    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)  # type: ignore
        return instance

    async def __init__(self):
        pass


class JsonRPC(aobject):
    default_version = "2.0"
    default_encondig = "UTF-8"
    default_request = ProcRequest(
        jsonrpc=default_version, id=None, method="", params=[]
    )
    notify_command = "notify"

    async def __init__(
        self,
        send: Union[SendType, ClientSendType],
        recv: Union[RecvType, ClientRecvType],
        addr: Optional[str] = None,
    ):
        self.__send = send
        self.__recv = recv
        self.__addr = addr
        self.__functions: Dict[str, FuncType] = {}
        self.__id = 0
        self.__tasks_queue: Dict[int, asyncio.Queue] = {}
        if addr is None:
            self.__find_response_task = asyncio.create_task(
                self.find_response())
            await self.alloc_ui()

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def cond_client(self):
        return self.__addr is None and not self.__find_response_task.cancelled()

    def get_addr(self):
        return "" if self.__addr is None else f"{self.__addr}: "

    def register(
        self,
        func=None,
        *,
        name: Optional[str] = None
    ) -> Callable:  # type: ignore
        if self.cond_client():
            self.__find_response_task.cancel()

        if func is None:
            return partial(self.register, name=name)
        key = func.__name__ if name is None else name
        self.__functions[key] = func

    @staticmethod
    def __validate_func_args(func: FuncType, args: ParamType):
        func_spec = inspect.getfullargspec(func)
        anno_types = func_spec.annotations
        arg_types = {k: v for k, v in anno_types.items() if k != "return"}
        for i, (key, anno) in enumerate(arg_types.items()):
            value = args[i] if isinstance(args, list) else args[key]
            if not issubclass(type(value), anno):
                raise ValueError

    async def send(self, message: str, token: Token):
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message, token)  # type: ignore

    async def recv(self) -> Tuple[Token, str]:
        token, data = await self.__recv()
        result = data.decode(self.default_encondig)  # type: ignore
        return (token, result)  # type: ignore

    async def __send_error(
        self, err: ResponseError, token: Token
    ):
        response = err.json(by_alias=True)
        print(f"{self.get_addr()} Response with error: {response}")
        await self.send(response, token)

    async def __handle_error(
        self, err: Error, token: Token, request: ProcRequest = default_request
    ):
        response = ResponseError(
            jsonrpc=request.json_rpc, error=err, id=request.id
        )
        if request.id is not None:
            await self.__send_error(response, token)
        else:
            print(
                f"{self.get_addr()} Error for request: {response.json(by_alias=True)}")

    async def __send_result(
        self, response: ResponseResult, token: Token
    ):
        result = response.json(by_alias=True)
        print(f"{self.get_addr()} Response: {result}")
        await self.send(result, token)

    async def __handle_result(
        self, result: Any, token: Token, request: ProcRequest = default_request
    ):
        response = ResponseResult(
            jsonrpc=request.json_rpc, result=result, id=request.id
        )
        if request.id is not None:
            await self.__send_result(response, token)
        else:
            print(
                f"{self.get_addr()} Result for request: {response.json(by_alias=True)}")

    async def alloc_ui(self):
        print("Аллокация интерфейсных вызовов")
        schema = await self.call('schema', [])
        notify_class = new_class()
        for alias_func_name in schema['functions']:
            async def func_call(func_name: str, *args, **kwargs):
                print("Вызов call")
                args = get_args(*args, **kwargs)
                print(f"Аргументы: {args}")
                print(f"Функция: {func_name}")
                return await self.call(func_name, args)

            async def func_notify(func_name: str, *args, **kwargs):
                print("Вызов notify")
                args = get_args(*args, **kwargs)
                print(f"Аргументы: {args}")
                print(f"Функция: {func_name}")
                await self.notify(func_name, args)
            setattr(self, alias_func_name, partial(
                func_call, alias_func_name))
            setattr(notify_class, alias_func_name, partial(
                func_notify, alias_func_name))

        setattr(self, "notify", notify_class())

    async def find_response(self):
        while True:
            rcv_bytes = await self.__recv()
            result_json = rcv_bytes.decode(  # type: ignore
                self.default_encondig)
            if result_json is not None:
                print(f"Response: {result_json}")
                base_response = JsonRpcModel.parse_raw(result_json)
                try:
                    result = ResponseError.parse_raw(result_json).error
                except:
                    result = ResponseResult.parse_raw(result_json).result
                finally:
                    if base_response.id is not None:
                        await self.__tasks_queue[base_response.id].put(result)

    def __get_request(self, func_name: str, args: Union[ParamType, Any], send_id: bool = True) -> RequestResult:
        if send_id:
            self.__id += 1
            id = self.__id
            self.__tasks_queue[id] = asyncio.Queue()
        else:
            id = None
        params = (
            args if isinstance(args, list) or isinstance(
                args, dict) else [args]
        )
        request = ProcRequest(
            jsonrpc=self.default_version,
            method=func_name,
            params=params,
            id=id,
        )
        return RequestResult(request=request, request_id=id)

    async def client_send(self, message: str):
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message)  # type: ignore

    async def client_recv(self, request_id: int):
        return await self.__tasks_queue[request_id].get()

    async def __remote_call(
        self, func_name: str, args: Union[ParamType, Any], send_id: bool = True
    ) -> RequestResult:
        request_result = self.__get_request(func_name, args, send_id)
        json_request = request_result["request"].json(by_alias=True)
        print(f"Send request: {json_request}")
        await self.client_send(json_request)
        return request_result

    def call(self, func_name: str, args: Union[ParamType, Any]) -> Any:
        async def callee():
            request_result = await self.__remote_call(func_name, args)
            if request_result["request_id"] is not None:
                return await self.client_recv(request_result["request_id"])

        future = asyncio.ensure_future(callee())
        return future

    async def notify(self, func_name: str, args: Union[ParamType, Any]):
        await self.__remote_call(func_name, args, False)

    async def batch(self, *args: Union[Tuple[str, Union[ParamType, Any]], Tuple[str, Union[ParamType, Any], bool]]) -> List[Any]:
        requests = [self.__get_request(*arg)["request"]  # type: ignore
                    for arg in args]
        json_requests = [request.json(by_alias=True) for request in requests]
        json_request = json.dumps(json_requests)
        print(f"Send batch request: {json_request}")
        await self.client_send(json_request)

        results = []
        for request in requests:
            if request.id is not None:
                result = await self.client_recv(request.id)
                results.append(result)

        return results

    def schema(self) -> dict:
        result: Dict[str, dict] = {}
        for alias_func_name, func in self.__functions.items():
            arg_spec = inspect.getfullargspec(func)
            parameters = arg_spec._asdict()
            del parameters["annotations"]
            anno = {k: str(v) if v != None else v for k,
                    v in arg_spec.annotations.items()}
            parameters["annotations"] = anno
            result[alias_func_name] = FuncSchema(
                funcName=func.__name__,
                parameters=parameters
            ).dict(by_alias=True)

        dict_base = {
            "title": f"JSON-RPC {self.default_version}",
            "mode": "client" if self.cond_client() else "server",
            "functions": result
        }
        return dict_base

    async def __handle_request(self, data: str, token: Token):
        try:
            try:
                print(f"{self.get_addr()} Request: {data}")
                request_data = json.loads(data)
                if isinstance(request_data, list):
                    for request in request_data:
                        asyncio.create_task(
                            self.__handle_request(request, token))
                    return
                request = ProcRequest.parse_raw(data)
            except ValidationError as e:
                print("ValidationError", e.json())
                await self.__handle_error(InvalidRequestError, token)
                return
            except Exception:
                await self.__handle_error(ParseError, token)
                return
            try:
                func = self.__functions[request.method]
            except KeyError:
                await self.__handle_error(MethodNotFoundError, token, request)
                return
            try:
                self.__validate_func_args(func, request.params)
            except:
                await self.__handle_error(InvalidParamsError, token, request)
                return
            result = (
                (await func(*request.params)
                 if inspect.iscoroutinefunction(func)
                 else func(*request.params))
                if isinstance(request.params, list)
                else await func(**request.params)
                if inspect.iscoroutinefunction(func)
                else func(**request.params)
            )
            if issubclass(type(result), type(Error)):
                await self.__handle_error(
                    result_err,  # type: ignore
                    token,
                    request
                )

        except asyncio.CancelledError:
            print(f"{self.get_addr()} Task for request: {data} cancelled")
        except Exception as e:
            print("Internal Error", e)
            print(traceback.format_exc())
            await self.__handle_error(
                InternalError,
                token,
                request  # type: ignore
            )
        else:
            try:
                if request.id is not None:
                    await self.__handle_result(result, token, request)
            except Exception as e:
                print("Internal Error", e)
                print(traceback.format_exc())
                await self.__handle_error(InternalError, token, request)

    async def run(self):
        while True:
            try:
                req = await self.recv()
            except Exception as e:
                print(f"{self.get_addr()} Internal error: {e}")
                print(traceback.format_exc())
            else:
                token, data = req
                asyncio.create_task(self.__handle_request(data, token))
