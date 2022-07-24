import asyncio
import inspect
import json
import traceback
from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import ValidationError, validate_arguments
from pydantic.typing import AnyCallable

from json_rpc.model import (ErrorDataType,
                            InvalidRequestError,
                            Error, JsonRpcError, FuncSchema, FuncType, ParamType,
                            ProcRequest, ResponseError, ResponseResult, get_internal_error, get_invalid_params_error, get_invalid_request_error, get_method_not_found_error, get_parse_error)
from json_rpc.socket_base.send_recv import RecvType, SendType, Token


class ServerJsonRPC():
    """JSON RPC wrapper for the server."""

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
        """
        :param send: message sending function
        :param recv: message receiving function
        addr: information (optional) about the client's IP and port
        """
        self.__send = send
        self.__recv = recv
        self.__addr = addr
        self.__functions: Dict[str, tuple[AnyCallable, FuncType]] = {}

    def get_addr(self):
        """address getter."""
        return "" if self.__addr is None else f"{self.__addr}: "

    def register(
        self,
        func=None,
        *,
        name: Optional[str] = None
    ) -> Callable:

        if func is None:
            return partial(self.register, name=name)
        key = func.__name__ if name is None else name
        pydantic_func = validate_arguments(func)
        self.__functions[key] = (pydantic_func, func)
        return func

    async def send(self, message: str, token: Token):
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message, token)

    async def recv(self) -> Tuple[Token, str]:
        token, data = await self.__recv()
        result = data.decode(self.default_encondig)
        return (token, result)

    async def __send_error(
        self, err: ResponseError, token: Token
    ):
        response = err.json(by_alias=True)
        print(f"{self.get_addr()} Response with error: {response}")
        await self.send(response, token)

    async def __handle_error(
        self, err: JsonRpcError, token: Token, request: ProcRequest = default_request
    ):
        try:
            response = ResponseError(
                jsonrpc=request.json_rpc, error=err, id=request.id
            )
        except ValidationError as e:
            print("ValidationError", e.json())
            return
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

    def schema(self) -> dict:
        result: Dict[str, dict] = {}
        for alias_func_name, (_, func) in self.__functions.items():
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
                print("Base validation values model error", e.json())
                error = get_invalid_request_error(e.errors)
                await self.__handle_error(error, token)
                return
            except json.JSONDecodeError as e:
                print("Parse JSON error", e)
                error_info = e.__dict__
                error_info["traceback"] = traceback.format_exc()
                await self.__handle_error(get_parse_error(error_info), token)
                return
            try:
                pydantic_func, func = self.__functions[request.method]
            except KeyError as e:
                error = get_method_not_found_error(traceback.format_exc())
                await self.__handle_error(error, token, request)
                return
            if isinstance(request.params, list):
                pydantic_func = partial(pydantic_func, *request.params)
            else:
                pydantic_func = partial(pydantic_func, **request.params)

            if inspect.iscoroutinefunction(func):
                result = await pydantic_func()
            else:
                result = pydantic_func()
        except ValidationError as err:
            print("Validation types error", err.json())
            await self.__handle_error(
                get_invalid_params_error(err.errors),
                token,
                request  # type: ignore
            )
        except Error as e:
            await self.__handle_error(
                e.get_error(),
                token,
                request  # type: ignore
            )
        except asyncio.CancelledError:
            print(f"{self.get_addr()} Task for request: {data} cancelled")
        except Exception as e:
            print("Internal Error", e)
            print(traceback.format_exc())
            error = {}
            error["args"] = e.args
            error["traceback"] = traceback.format_exc()
            await self.__handle_error(
                get_internal_error(error),
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
                error = {}
                error["args"] = e.args
                error["traceback"] = traceback.format_exc()
                await self.__handle_error(get_internal_error(error), token, request)

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
