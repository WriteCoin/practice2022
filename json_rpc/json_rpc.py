import asyncio
from contextlib import asynccontextmanager
from functools import partial
import inspect
import traceback
from typing import Any, AsyncGenerator, Awaitable, Optional
from pydantic import ValidationError
from json_rpc.model import (
    Error,
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
    ResponseError,
    ResponseResult,
)
from json_rpc.socket_base.send_recv import (
    RecvType,
    SendType,
    Token,
)


class JsonRPC:
    default_version = "2.0"
    default_encondig = "UTF-8"
    default_request = ProcRequest(
        jsonrpc=default_version, id=None, method="", params=[]
    )
    notify_command = "notify"

    def __init__(
        self,
        send: SendType,
        recv: RecvType,
        addr: Optional[str] = None,
    ):
        self.__send = send
        self.__recv = recv
        self.__addr = addr
        self.__functions: dict[str, FuncType] = {}
        self.__id = 0
        self.__tasks: dict[int, Error | Any | None] = {}
        self.__tasks_queue: asyncio.Queue = asyncio.Queue()
        if len(inspect.signature(send).parameters) == 1:
            task_get_token = asyncio.gather(asyncio.create_task(self.get_token()))
            task_get_token

    async def get_token(self):
        pass

    def get_addr(self):
        return "" if self.__addr is None else f"{self.__addr}: "

    @staticmethod
    def __get_func_name(func: FuncType) -> str:
        func_full_path = str(func).split(" ")[1]
        if func_full_path.find(".<locals>.") != -1:
            paths_to_func = func_full_path.split(".<locals>.")
            path_to_func = paths_to_func[len(paths_to_func) - 1]
        else:
            path_to_func = func_full_path
        func_parts = path_to_func.split(".")
        name_func = func_parts[len(func_parts) - 1]
        return name_func

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
        await self.__send(b_message, token)

    async def recv(self) -> tuple[Token, str] | None:
        token, data = await self.__recv()
        result = data.decode(self.default_encondig)
        return (token, result)

    async def __send_error(
        self, err: Error, token: Token, request: ProcRequest = default_request
    ):
        response = ResponseError(
            jsonrpc=request.json_rpc, error=err, id=request.id
        ).json(by_alias=True)
        print(f"{self.get_addr()} Response with error: {response}")
        await self.send(response, token)

    async def __send_result(
        self, result: Any, token: Token, request: ProcRequest = default_request
    ):
        response = ResponseResult(
            jsonrpc=request.json_rpc, result=result, id=request.id
        ).json(by_alias=True)
        print(f"{self.get_addr()} Response: {response}")
        await self.send(response, token)

    def register(self, func=None, *, name: str | None = None):
        if func is None:
            return partial(self.register, name=name)
        key = func.__name__ if name is None else name
        self.__functions[key] = func

        async def wrapper(*args, **kwargs):
            return (
                await func(*args, **kwargs)
                if isinstance(func, Awaitable)
                else func(*args, **kwargs)
            )

        return wrapper

    @asynccontextmanager
    async def __remote_call(
        self, func_name: str, args: ParamType | Any, send_id: bool = True
    ) -> AsyncGenerator[tuple[ProcRequest, int | None], None]:
        def part_send():
            return partial(
                self.__send, request.json(by_alias=True).encode(self.default_encondig)
            )

        try:
            if send_id:
                self.__id += 1
                id = self.__id
            else:
                id = None
            params = (
                args if isinstance(args, list) or isinstance(args, dict) else [args]
            )
            request = ProcRequest(
                jsonrpc=self.default_version,
                method=func_name,
                params=params,
                id=self.__id,
            )
            print(f"Send request: {request.json(by_alias=True)}")
            await part_send()()
            yield (request, id)
        except:
            print(traceback.format_exc())
            raise InternalErrorException

    def call(self, func_name: str, args: ParamType | Any):
        async def callee():
            async with self.__remote_call(func_name, args) as (request, request_id):
                request_id = 0 if request_id is None else request_id
                self.__tasks[request_id] = None
                # await self.__tasks_queue.put(None)
                # self.__tasks_queue.join()
                async def get_response():
                    # while True:
                        _, rcv_bytes = await self.__recv()
                        result_json = rcv_bytes.decode(self.default_encondig)
                        if not result_json is None:
                            print(f"Response: {result_json}")
                            base_response = JsonRpcModel.parse_raw(result_json)
                            # if base_response.id != id:
                            #     continue
                            try:
                                result = ResponseError.parse_raw(result_json).error
                            except:
                                result = ResponseResult.parse_raw(result_json).result
                            finally:
                                self.__tasks[base_response.id] = result
                                # return result
                        else:
                            print("No response")
                # async def find_response():
                while True:
                    await get_response()
                    for id, response in self.__tasks.items():
                        if id == request_id:
                            return response
        future = asyncio.ensure_future(callee())
        return future
                # async for id, response in self.__tasks.items():
                #     await get_response()
                #     if id == request_id:
                #         return response
        # return await callee()
        # future = asyncio.ensure_future(callee())
        # return await future

    async def notify(self, func_name: str, args: ParamType | Any) -> None:
        async with self.__remote_call(func_name, args):
            return None

    def schema(self) -> dict:
        return {}

    async def __handle_request(self, data: str, token: Token):
        try:
            try:
                print(f"{self.get_addr()} Request: {data}")
                request = ProcRequest.parse_raw(data)
            except ValidationError as e:
                await self.__send_error(InvalidRequestError, token)
                return
            except Exception:
                await self.__send_error(ParseError, token)
                return
            try:
                func = self.__functions[request.method]
            except KeyError:
                await self.__send_error(MethodNotFoundError, token, request)
                return
            try:
                self.__validate_func_args(func, request.params)
            except:
                await self.__send_error(InvalidParamsError, token, request)
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
                await self.__send_error(result, token)
        except asyncio.CancelledError:
            print(f"{self.get_addr()} Task for request: {data} cancelled")
        except:
            await self.__send_error(InternalError, token)
        else:
            await self.__send_result(result, token, request)

    async def run(self):
        while True:
            try:
                req = await self.recv()
            except Exception as e:
                print(f"{self.get_addr()} Internal error: {e}")
                print(traceback.format_exc())
            else:
                token, data = req
                task_request = asyncio.create_task(self.__handle_request(data, token))
                task_request
