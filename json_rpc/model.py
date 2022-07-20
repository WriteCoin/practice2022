from inspect import FullArgSpec
from lib2to3.pgen2.parse import ParseError
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


class ErrorData(TypedDict):
    loc: Optional[list]
    msg: Optional[str]
    type: str
    ctx: Optional[dict]


class Error(TypedDict):
    code: int
    message: str
    data: Optional[ErrorData]


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


def get_invalid_request_error(data: ErrorData):
    return Error(
        code=INVALID_REQUEST_ERROR_CODE,
        message=INVALID_REQUEST_ERROR_MESSAGE,
        data=data
    )


def get_method_not_found_error(data: ErrorData):
    return Error(
        code=METHOD_NOT_FOUND_ERROR_CODE,
        message=METHOD_NOT_FOUND_ERROR_MESSAGE,
        data=data
    )


def get_invalid_params_error(data: ErrorData):
    return Error(
        code=INVALID_PARAMS_ERROR_CODE,
        message=INVALID_PARAMS_ERROR_MESSAGE,
        data=data
    )


def get_internal_error(data: ErrorData):
    return Error(
        code=INTERNAL_ERROR_CODE,
        message=INTERNAL_ERROR_MESSAGE,
        data=data
    )


def get_parse_error(data: ErrorData):
    return Error(
        code=PARSE_ERROR_CODE,
        message=PARSE_ERROR_MESSAGE,
        data=data
    )


DefaultInvalidRequestErrorData = ErrorData(
    loc=None,
    msg=None,
    type=INVALID_REQUEST_ERROR_TYPE,
    ctx=None
)

DefaultInvalidRequestError = get_invalid_request_error(
    DefaultInvalidRequestErrorData)

DefaultMethodNotFoundErrorData = ErrorData(
    loc=None,
    msg=None,
    type=METHOD_NOT_FOUND_ERROR_TYPE,
    ctx=None
)

DefaultMethodNotFoundError = get_method_not_found_error(
    DefaultMethodNotFoundErrorData)

DefaultInvalidParamsErrorData = ErrorData(
    loc=None,
    msg=None,
    type=INVALID_PARAMS_ERROR_TYPE,
    ctx=None
)

DefaultInvalidParamsError = get_invalid_params_error(
    DefaultInvalidParamsErrorData)

DefaultInternalErrorData = ErrorData(
    loc=None,
    msg=None,
    type=INTERNAL_ERROR_TYPE,
    ctx=None
)

DefaultInternalError = get_internal_error(DefaultInternalErrorData)

DefaultParseErrorData = ErrorData(
    loc=None,
    msg=None,
    type=PARSE_ERROR_TYPE,
    ctx=None
)

DefaultParseError = get_parse_error(DefaultParseErrorData)


class ResponseError(JsonRpcModel):
    error: Error


class ResponseResult(JsonRpcModel):
    result: Any


class InvalidRequestException(Exception):
    def __str__(self) -> str:
        return DefaultInvalidRequestError["message"]


class MethodNotFoundException(Exception):
    def __str__(self) -> str:
        return DefaultMethodNotFoundError["message"]


class InternalErrorException(Exception):
    def __str__(self) -> str:
        return DefaultInternalError["message"]


class FuncSchema(BaseModel):
    func_name: str = Field(alias="funcName")
    parameters: dict


class JsonRpcSchema(BaseModel):
    title: str = "JSON-RPC 2.0"


exceptions = {
    INVALID_REQUEST_ERROR_TYPE: InvalidRequestException,
    METHOD_NOT_FOUND_ERROR_TYPE: MethodNotFoundException,
    INVALID_PARAMS_ERROR_TYPE: TypeError,
    INTERNAL_ERROR_TYPE: InternalErrorException,
    PARSE_ERROR_TYPE: ParseError
}
