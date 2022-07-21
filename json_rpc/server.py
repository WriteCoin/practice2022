import asyncio
import inspect
import json
import traceback
from functools import partial
from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import ValidationError, validate_arguments
from pydantic.typing import AnyCallable

from json_rpc.model import (DefaultInternalError, DefaultInternalErrorDict, DefaultInvalidParamsError, DefaultInvalidRequestErrorDict, DefaultMethodNotFoundErrorDict, DefaultParseErrorDict, ErrorDataType,
                            InvalidRequestError,
                            DefaultMethodNotFoundError, DefaultParseError,
                            Error, ErrorDict, FuncSchema, FuncType, ParamType,
                            ProcRequest, ResponseError, ResponseResult, get_invalid_params_error_dict)
from json_rpc.socket_base.send_recv import RecvType, SendType, Token


class ServerJsonRPC():
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
        self.__functions: Dict[str, tuple[AnyCallable, FuncType]] = {}

    def get_addr(self):
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

    # @staticmethod
    # def __validate_func_args(func: FuncType, args: ParamType):
    #     func_spec = inspect.getfullargspec(func)
    #     anno_types = func_spec.annotations
    #     arg_types = {k: v for k, v in anno_types.items() if k != "return"}
    #     for i, (key, anno) in enumerate(arg_types.items()):
    #         value = args[i] if isinstance(args, list) else args[key]
    #         if not issubclass(type(value), anno):
    #             raise TypeError

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
        self, err: ErrorDict, token: Token, request: ProcRequest = default_request
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
                print("ValidationError", e.json())
                await self.__handle_error(DefaultInvalidRequestErrorDict, token)
                return
            except Exception:
                await self.__handle_error(DefaultParseErrorDict, token)
                return
            try:
                pydantic_func, func = self.__functions[request.method]
            except KeyError:
                await self.__handle_error(DefaultMethodNotFoundErrorDict, token, request)
                return
            # try:
            #     self.__validate_func_args(func, request.params)
            # except:
            #     await self.__handle_error(DefaultInvalidParamsError, token, request)
            #     return

            # if isinstance(request.params, list):
            #     pydantic_func.validate(*request.params)
            # else:
            #     pydantic_func.validate(**request.params)

            if isinstance(request.params, list):
                pydantic_func = partial(pydantic_func, *request.params)
            else:
                pydantic_func = partial(pydantic_func, **request.params)

            if inspect.iscoroutinefunction(func):
                result = await pydantic_func()
            else:
                result = pydantic_func()

            # if isinstance(request.params, list):
            #     func = partial(func, *request.params)
            # else:
            #     func = partial(func, **request.params)

            # if inspect.iscoroutinefunction(func):
            #     result = await func()
            # else:
            #     result = func()

            # if issubclass(type(result), type(Error)):
            #     await self.__handle_error(
            #         result_err,  # type: ignore
            #         token,
            #         request
            #     )
        except ValidationError as err:
            print("ValidationError", err.json())
            error_data = json.loads(err.json())[0]
            try:
                error_data["ctx"]
            except KeyError:
                error_data["ctx"] = None
            await self.__handle_error(
                get_invalid_params_error_dict([error_data]),
                token,
                request  # type: ignore
            )
        except asyncio.CancelledError:
            print(f"{self.get_addr()} Task for request: {data} cancelled")
        except Exception as e:
            print("Internal Error", e)
            print(traceback.format_exc())
            await self.__handle_error(
                DefaultInternalErrorDict,
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
                await self.__handle_error(DefaultInternalErrorDict, token, request)

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
