import asyncio
from http.client import responses
import json
from contextlib import asynccontextmanager
from functools import partial
from inspect import getargs
from socketserver import BaseRequestHandler
import traceback
from typing import (Any, Awaitable, Callable, Dict, List, Literal, Optional,
                    Tuple, Union)

from json_rpc.model import (ArgsType, Error, JsonRpcModel, ParamType, ProcRequest,
                            RequestResult, ResponseError, ResponseResult)
from json_rpc.socket_base.send_recv import ClientRecvType, ClientSendType
import concurrent.futures as pool

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
    """JSON RPC wrapper for the client."""

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
        """
        :param send: message sending function
        :param recv: message receiving function
        addr: information (optional) about the client's IP and port
        """
        self.__send = send
        self.__recv = recv
        self.__id = 0
        self.__responses: Dict[int, asyncio.Queue] = {}
        self.notify = CallNotifyGasket(self, self.__notify)
        self.batch = BatchGasket(self, self.__batch)
        asyncio.create_task(self.find_response())

    async def send(self, message: str):
        """
            Sending a message.
        :param message: message to send
        :return
        """
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message)

    async def recv(self, request_id: int) -> str:
        """
            Receiving a message.
        :param request_id: request ID
        :return message
        """
        response = await self.__responses[request_id].get()
        if issubclass(type(response), Error):
            raise response
        del self.__responses[request_id]
        return response

    async def find_response(self):
        """
            the general task of finding all the responses from the server.
            Tries to parse as an error first and translate to Exception.
            In case of failure, parses as a result and writes it.
        :return
        """
        while True:
            rcv_bytes = await self.__recv()
            result_json = rcv_bytes.decode(
                self.default_encondig)
            if result_json is not None:
                print(f"Response: {result_json}")
                base_response = JsonRpcModel.parse_raw(result_json)
                try:
                    response = ResponseError.parse_raw(result_json).error
                    response = Error.from_error(response)
                except:
                    response = ResponseResult.parse_raw(result_json).result
                finally:
                    if base_response.id is not None:
                        await self.__responses[
                            base_response.id
                        ].put(response)  # type: ignore

    def __get_request(self, func_name: str, args: Union[ParamType, Any], send_id: bool = True) -> RequestResult:
        """
            Forming a new request
            Auto-increment works for call calls, arguments are given in dict or list format.
        :param func_name: name of function
        :param args: arguments of function
        :send_id: send as a call request
        :return Request result model
        """
        if send_id:
            self.__id += 1
            id = self.__id
            self.__responses[id] = asyncio.Queue()
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
        """
            Remote function call.
        :param func_name: name of function
        :param args: arguments of function
        :send_id: send as a call request
        :return Request result model  
        """
        request_result = self.__get_request(func_name, args, send_id)
        json_request = request_result["request"].json(by_alias=True)
        print(f"Send request: {json_request}")
        await self.send(json_request)
        return request_result

    def call(self, func_name: str, args: Union[ParamType, Any]) -> Any:
        """
            Call method.
        :param func_name: name of function
        :param args: arguments of function
        :return Any
        """
        async def callee():
            request_result = await self.__remote_call(func_name, args)
            if request_result["request_id"] is not None:
                return await self.recv(request_result["request_id"])

        future = asyncio.ensure_future(callee())
        return future

    async def __notify(self, name: str, *args, **kwargs):
        """
            The real notify method.
            Unlike a call, it sends a request without waiting for any response.
        :param name: name of function
        :param *args:
        :param **kwargs:
        :return
        """
        await self.__remote_call(
            name,
            get_args(*args, **kwargs)[0],  # type: ignore
            False
        )

    async def __batch(self, *args: BatchArg) -> List[Any]:
        """
            The current batch method.
        :param *args: Many parts defined as a sequence of the format that is transmitted with notify and call.
        :return
        """
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


class CallNotifyGasket():
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


class BatchGasket():
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
