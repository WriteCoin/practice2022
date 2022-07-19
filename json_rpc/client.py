import asyncio
from contextlib import asynccontextmanager
from functools import partial
from inspect import getargs
import json
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple, Union
from json_rpc.model import ArgsType, JsonRpcModel, ParamType, ProcRequest, RequestResult, ResponseError, ResponseResult
from json_rpc.socket_base.send_recv import ClientRecvType, ClientSendType


def notification(
    func_name: str,
    params: Union[ParamType, Any]
) -> Tuple[str, Union[ParamType, Any], Literal[False]]:
    return (func_name, params, False)


def new_class():
    return type('notify', (object, ), dict())


def get_args(*args, **kwargs):
    return [*args] if len(args) else {**kwargs}


FuncType = Callable[[str, ArgsType], Awaitable[Any]]
BatchArgs = Union[Tuple[str, Union[ParamType, Any]],
                  Tuple[str, Union[ParamType, Any], bool]]


class ItemAttrDecorator():
    def __init__(self, func: FuncType):
        self.func = func

    async def __func(self, name: str, *args, **kwargs):
        return await self.func(name, get_args(*args, **kwargs))

    def __getitem__(self, name: str):
        return partial(self.__func, name)

    def __getattr__(self, name: str):
        return self[name]

    def __str__(self):
        return self.func

    async def __call__(self, name: str, *args, **kwargs):
        return await self.__func(name, *args, **kwargs)


class BatchDecorator(ItemAttrDecorator):
    def __init__(self, func: FuncType):
        super().__init__(func)


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
        self.__batch_args = []
        self.is_batch = False
        self.no_notify = True
        asyncio.create_task(self.find_response())

    async def send(self, message: str):
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message)

    async def recv(self, request_id: int) -> str:
        return await self.__tasks_queue[request_id].get()

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

    async def __batch(self, *args: Union[Tuple[str, Union[ParamType, Any]], Tuple[str, Union[ParamType, Any], bool]]) -> List[Any]:
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

    async def __notify(self, name: str, *args, **kwargs):
        await self.__remote_call(
            name,
            get_args(*args, **kwargs)[0],  # type: ignore
            False
        )

    def accumulate(self, name: str, *args, **kwargs):
        self.__batch_args.append(
            (name, get_args(*args, **kwargs), self.no_notify)
        )
        self.no_notify = not self.no_notify if not self.no_notify else self.no_notify
        return self

    async def __call__(self, *args: Union[Tuple[str, Union[ParamType, Any]], Tuple[str, Union[ParamType, Any], bool]]):
        return await self.__batch(*args)

    def __getitem__(self, name: str):
        if not self.is_batch:
            if name == 'notify':
                return ItemAttrDecorator(self.__notify)
            elif name == 'batch':
                self.is_batch = True
                return self
            else:
                return partial(self.__call, name)
        elif name == 'notify':
            self.no_notify = False
            return self
        else:
            return partial(self.accumulate, name)

    def __getattr__(self, name: str):
        return self[name]

    async def collect(self):
        self.is_batch = False
        result = await self.__batch(*self.__batch_args)
        self.__batch_args.clear()
        return result
