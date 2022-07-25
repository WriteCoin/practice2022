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
        """
            Registering a new feature.
            It is recommended to use as a decorator.
            Pre-passes the type check using pedantic.
        :param func: if None, then a special name is required
        :param name: the alias of the registered function, the client will have to specify this name to call it
        :return func
        """
        if func is None:
            return partial(self.register, name=name)
        key = func.__name__ if name is None else name
        pydantic_func = validate_arguments(func)
        self.__functions[key] = (pydantic_func, func)
        return func

    async def send(self, message: str, token: Token):
        """
            Sending a message.
        :param message: message to send
        :param token: the client ID received by receiving the message
        :return
        """
        b_message = message.encode(self.default_encondig)
        await self.__send(b_message, token)

    async def recv(self) -> Tuple[Token, str]:
        """
            Receiving a message.
        :return Token and message string
        """
        token, data = await self.__recv()
        result = data.decode(self.default_encondig)
        return (token, result)

    async def __send_error(
        self, err: ResponseError, token: Token
    ):
        """
            Sending an error in JSON RPC format.
            in the error object, especially the data property, you need to put the correct data for JSON serialization
        :param err: error object
        :param token: Token
        :return
        """
        response = err.json(by_alias=True)
        print(f"{self.get_addr()} Response with error: {response}")
        await self.send(response, token)

    async def __handle_error(
        self, err: JsonRpcError, token: Token, request: ProcRequest = default_request
    ):
        """
            Generating and sending an error, if it occurred, in JSON RPC format.
            The link between Exception and Target sending.
            it is strongly recommended to specify valid data for the JsonRpcError object.
            Otherwise, sending is not possible.
            If there is no request ID, nothing is sent (notify call), and the message is output in string form.
        :param err: error object
        :param token: Token
        :param request: Generated (optional) request
        """
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
        """
            Sending the result in JSON RPC format.
            The function that worked correctly should return the correct JSON format for serialization.
        :param response: result model object
        :param token: Token
        """
        result = response.json(by_alias=True)
        print(f"{self.get_addr()} Response: {result}")
        await self.send(result, token)

    async def __handle_result(
        self, result: Any, token: Token, request: ProcRequest = default_request
    ):
        """
            Generating and sending the result in JSON RPC format.
            The link between Exception and Target sending.
            it is strongly recommended to specify a valid result data type for serialization.
            Otherwise, sending is not possible.
            If the request ID is missing, nothing is sent (notification call), and the result is JSON in string form.
        :param result: valid value for serialization
        :param token: Token
        :param request: Generated (optional) request
        :return
        """
        response = ResponseResult(
            jsonrpc=request.json_rpc, result=result, id=request.id
        )
        if request.id is not None:
            await self.__send_result(response, token)
        else:
            print(
                f"{self.get_addr()} Result for request: {response.json(by_alias=True)}")

    def schema(self) -> dict:
        """
            Getting the server schema.
            Getting information about the JSON RPC specification version and the functions used,
            in dictionary format: `alias_func_name`: (annotations object).
            Annotations are taken from the standard inspect module.
        :return dict
        """
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
        """
            Server-side request processing.
            Sends a result in the normal case or an error.
            Handles all errors provided by the JSON RPC specification.

            The first ValidationError is responsible for the error 
            of invalid data as not conforming to the specification (invalid format).

            The second JSONDecodeError error is a basic JSON parsing error.

            KeyError - the function was not registered.

            The second ValidationError error is an error
            related to incorrect data types sent to the function.

            Error - a custom error that you can implement yourself.

            Exception - general Internal error.

        :param data: data
        :param token: Token
        :return
        """
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
                get_invalid_params_error(err.json()),
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
        """
            The basis of the server operation.
            Constantly receives messages and creates tasks for new requests.
        :return
        """
        while True:
            try:
                req = await self.recv()
            except Exception as e:
                print(f"{self.get_addr()} Internal error: {e}")
                print(traceback.format_exc())
            else:
                token, data = req
                asyncio.create_task(self.__handle_request(data, token))
