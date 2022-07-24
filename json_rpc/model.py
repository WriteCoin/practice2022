from inspect import FullArgSpec
import json
from types import MemberDescriptorType
from typing import (Any, Awaitable, Callable, Dict, List, Mapping, Optional,
                    Union)

from pydantic import BaseModel, Field, ValidationError
from typing_extensions import TypedDict

FuncType = Union[Callable[(...), Awaitable[None]], Callable]

ParamType = Union[List[Any], Dict[str, Any]]

ArgsType = Union[ParamType, Any]


class BatchParam(TypedDict):
    func_name: str
    args: Union[ParamType, Any]


class JsonRpcModel(BaseModel):
    json_rpc: str = Field(alias="jsonrpc")
    id: Optional[int]


class ProcRequest(JsonRpcModel):
    method: str
    params: ParamType


class RequestResult(TypedDict):
    request: ProcRequest
    request_id: Optional[int]


class BatchRequest(BaseModel):
    params: List[ProcRequest]


ErrorDataType = Any


class JsonRpcError(TypedDict):
    code: int
    message: str
    data: ErrorDataType


def _all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in _all_subclasses(c)]
    )


class Error(Exception):
    code: int
    message: str
    data: ErrorDataType

    def __init__(self, code: Optional[int] = None, message: Optional[str] = None, data: ErrorDataType = None) -> None:
        self.code = code or self.__class__.code
        self.message = message or self.__class__.message
        self.data = data

    def __str__(self):
        if self.data is None:
            return f"{self.message}"
        else:
            return f"{self.message}\n{json.dumps(self.data)}"

    def get_error(self, include_data: bool = True):
        return JsonRpcError(
            code=self.code,
            message=self.message,
            data=self.message if include_data else None
        )

    def json(self):
        try:
            return json.dumps(self.get_error())
        except:
            return json.dumps(self.get_error(False))

    @classmethod
    def from_error(cls, error: JsonRpcError):
        for error_class in _all_subclasses(cls):
            if error_class.code == error["code"]:
                return error_class(error["code"], error["message"], error["data"])
        return cls(error["code"], error["message"], error["data"])


INVALID_REQUEST_ERROR_CODE = -32600
INVALID_REQUEST_ERROR_MESSAGE = "Invalid request"
INVALID_REQUEST_ERROR_TYPE = "invalid_request"
METHOD_NOT_FOUND_ERROR_CODE = -32601
METHOD_NOT_FOUND_ERROR_MESSAGE = "Method not found"
METHOD_NOT_FOUND_ERROR_TYPE = "method_not_found"
INVALID_PARAMS_ERROR_CODE = -32602
INVALID_PARAMS_ERROR_MESSAGE = "Invalid params"
INVALID_PARAMS_ERROR_TYPE = "type_error"
INTERNAL_ERROR_CODE = -32603
INTERNAL_ERROR_MESSAGE = "Internal error"
INTERNAL_ERROR_TYPE = "internal_error"
PARSE_ERROR_CODE = -32700
PARSE_ERROR_MESSAGE = "Parse error"
PARSE_ERROR_TYPE = "parse_error"

VALUE_ERROR_TYPE = "value_error"


class InvalidRequestError(Error):
    code: int = INVALID_REQUEST_ERROR_CODE
    message: str = INVALID_REQUEST_ERROR_MESSAGE


class MethodNotFoundError(Error):
    code: int = METHOD_NOT_FOUND_ERROR_CODE
    message: str = METHOD_NOT_FOUND_ERROR_MESSAGE


class InvalidParamsError(Error):
    code: int = INVALID_PARAMS_ERROR_CODE
    message: str = INVALID_PARAMS_ERROR_MESSAGE


class InternalError(Error):
    code: int = INTERNAL_ERROR_CODE
    message: str = INTERNAL_ERROR_MESSAGE


class ParseError(Error):
    code: int = PARSE_ERROR_CODE
    message: str = PARSE_ERROR_MESSAGE


def get_invalid_request_error(data: ErrorDataType = None):
    return JsonRpcError(
        code=INVALID_REQUEST_ERROR_CODE,
        message=INVALID_REQUEST_ERROR_MESSAGE,
        data=data
    )


def get_method_not_found_error(data: ErrorDataType = None):
    return JsonRpcError(
        code=METHOD_NOT_FOUND_ERROR_CODE,
        message=METHOD_NOT_FOUND_ERROR_MESSAGE,
        data=data
    )


def get_invalid_params_error(data: ErrorDataType = None):
    return JsonRpcError(
        code=INVALID_PARAMS_ERROR_CODE,
        message=INVALID_PARAMS_ERROR_MESSAGE,
        data=data
    )


def get_internal_error(data: ErrorDataType = None):
    return JsonRpcError(
        code=INTERNAL_ERROR_CODE,
        message=INTERNAL_ERROR_MESSAGE,
        data=data
    )


def get_parse_error(data: ErrorDataType = None):
    return JsonRpcError(
        code=PARSE_ERROR_CODE,
        message=PARSE_ERROR_MESSAGE,
        data=data
    )


class ResponseError(JsonRpcModel):
    error: JsonRpcError


class ResponseResult(JsonRpcModel):
    result: Any


class FuncSchema(BaseModel):
    func_name: str = Field(alias="funcName")
    parameters: dict


class JsonRpcSchema(BaseModel):
    title: str = "JSON-RPC 2.0"
