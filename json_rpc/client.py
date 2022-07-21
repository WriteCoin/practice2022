import asyncio
import json
from contextlib import asynccontextmanager
from functools import partial
from inspect import getargs
import traceback
from typing import (Any, Awaitable, Callable, Dict, List, Literal, Optional,
                    Tuple, Union)

from json_rpc.model import (ArgsType, Error, JsonRpcModel, ParamType, ProcRequest,
                            RequestResult, ResponseError, ResponseResult,
                            exceptions)
from json_rpc.socket_base.send_recv import ClientRecvType, ClientSendType

BatchArg = Union[Tuple[str, Union[ParamType, Any]],
                 Tuple[str, Union[ParamType, Any], bool]]
BatchArgs = Tuple[BatchArg, ...]


def notification(
    func_name: str,
    params: Union[ParamType, Any]
) -> BatchArg:
    return (func_name, params, False)


def get_args(*args, **kwargs):
    return [*args] if len(args) else {**kwargs}


class ClientJsonRPC():
    default_version = "2.0"
    default_encondig = "UTF-8"
    default_request = ProcRequest(
        jsonrpc=default_version, id=None, method="", params=[]
    )
    notify_command = "notify"

    def __init__(
        self,
        send: ClientSendType,
        recv: ClientRecvType,
    ):
        self.__send = send
        self.__recv = recv
        self.__id = 0
        self.__tasks_queue: Dict[int, asyncio.Queue] = {}
        self.notify = CallNotifyDecorator(self, self.__notify)
        self.batch = BatchDecorator(self, self.__batch)
        asyncio.create_task(self.find_response())

    async def send(self, message: str):
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message)

    async def recv(self, request_id: int) -> str:
        result = await self.__tasks_queue[request_id].get()
        if issubclass(result, Exception):
            raise result
        return result

    async def find_response(self):
        while True:
            rcv_bytes = await self.__recv()
            result_json = rcv_bytes.decode(
                self.default_encondig)
            if result_json is not None:
                print(f"Response: {result_json}")
                base_response = JsonRpcModel.parse_raw(result_json)
                try:
                    result = ResponseError.parse_raw(result_json).error
                    if result["data"] is not None:
                        error_type = result["data"][0]["type"]
                        try:
                            result = exceptions[error_type]
                        except KeyError:
                            try:
                                result = exceptions[error_type.split('.')[0]]
                            except KeyError:
                                result = Error(
                                    result["code"], result["message"], result["data"])
                    else:
                        result = Error(result["code"], result["message"])
                except Exception as e:
                    result = ResponseResult.parse_raw(result_json).result
                finally:
                    if base_response.id is not None:
                        await self.__tasks_queue[
                            base_response.id
                        ].put(result)  # type: ignore

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

    async def __remote_call(
        self, func_name: str, args: Union[ParamType, Any], send_id: bool = True
    ) -> RequestResult:
        request_result = self.__get_request(func_name, args, send_id)
        json_request = request_result["request"].json(by_alias=True)
        print(f"Send request: {json_request}")
        await self.send(json_request)
        return request_result

    def call(self, func_name: str, args: Union[ParamType, Any]) -> Any:
        async def callee():
            request_result = await self.__remote_call(func_name, args)
            if request_result["request_id"] is not None:
                return await self.recv(request_result["request_id"])

        future = asyncio.ensure_future(callee())
        return future

    async def __notify(self, name: str, *args, **kwargs):
        await self.__remote_call(
            name,
            get_args(*args, **kwargs)[0],  # type: ignore
            False
        )

    async def __batch(self, *args: BatchArg) -> List[Any]:
        requests = [self.__get_request(*arg)["request"]  # type: ignore
                    for arg in args]
        json_requests = [request.json(by_alias=True) for request in requests]
        json_request = json.dumps(json_requests)
        print(f"Send batch request: {json_request}")
        await self.send(json_request)

        results = []
        for request in requests:
            if request.id is not None:
                result = await self.recv(request.id)
                results.append(result)

        return results

    async def __call(self, name: str, *args, **kwargs):
        return await self.call(name, get_args(*args, **kwargs))

    def __getitem__(self, name: str):
        return partial(self.__call, name)

    def __getattr__(self, name: str):
        return self[name]


FuncType = Callable[[str, ArgsType], Awaitable[Any]]
BatchFunc = Callable[[BatchArg], Awaitable[List[Any]]]


class CallNotifyDecorator():
    def __init__(self, client: ClientJsonRPC, func: FuncType):
        self.client = client
        self.func = func

    async def __func(self, name: str, *args, **kwargs):
        return await self.func(name, get_args(*args, **kwargs))

    def __getitem__(self, name: str):
        return partial(self.__func, name)

    def __getattr__(self, name: str):
        return self[name]

    async def __call__(self, name: str, *args, **kwargs):
        return await self.__func(name, *args, **kwargs)


class BatchDecorator():
    def __init__(self, client: ClientJsonRPC, func: BatchFunc, args: List[BatchArg] = [], call_available: bool = True, no_notify: bool = True):
        self.client = client
        self.func = func
        self.args = args
        self.call_available = call_available
        self.no_notify = no_notify
        if no_notify:
            self.notify = self.__class__(
                self.client, self.func, self.args, False, False)

    def accumulate(self, arg: BatchArg):
        self.args.append(arg)
        return self.__class__(self.client, self.func, self.args, False)

    def __func(self, name: str, *args, **kwargs):
        return self.accumulate((name, get_args(*args, **kwargs), self.no_notify))

    def __getitem__(self, name: str):
        return partial(self.__func, name)

    def __getattr__(self, name: str):
        return self[name]

    async def __call__(self, *args: BatchArg):
        if self.call_available:
            return await self.func(*args)
        else:
            print("Oops...")

    async def collect(self):
        return await self.func(*self.args)
