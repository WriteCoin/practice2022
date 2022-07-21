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


class ErrorData(TypedDict):
    loc: Optional[list]
    msg: Optional[str]
    type: str
    ctx: Optional[dict]


ErrorDataType = Optional[list[ErrorData]]


class ErrorDict(TypedDict):
    code: int
    message: str
    data: ErrorDataType


class Error(Exception):
    code: int
    message: str
    data: ErrorDataType

    def __init__(self, code: int, message: str, data: ErrorDataType = None) -> None:
        self.code = code
        self.message = message
        self.data = data

    def __str__(self):
        if self.data is None:
            return f"{self.message}"
        else:
            return f"{self.message}\n{json.dumps(self.data)}"


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
    def __init__(self, data: ErrorDataType = None) -> None:
        super().__init__(INVALID_REQUEST_ERROR_CODE, INVALID_REQUEST_ERROR_MESSAGE, data)


class MethodNotFoundError(Error):
    def __init__(self, data: ErrorDataType = None) -> None:
        super().__init__(METHOD_NOT_FOUND_ERROR_CODE, METHOD_NOT_FOUND_ERROR_MESSAGE, data)


class InvalidParamsError(Error):
    def __init__(self, data: ErrorDataType = None) -> None:
        super().__init__(INVALID_PARAMS_ERROR_CODE, INVALID_PARAMS_ERROR_MESSAGE, data)


class InternalError(Error):
    def __init__(self, data: ErrorDataType = None) -> None:
        super().__init__(INTERNAL_ERROR_CODE, INTERNAL_ERROR_MESSAGE, data)


class ParseError(Error):
    def __init__(self, data: ErrorDataType = None) -> None:
        super().__init__(PARSE_ERROR_CODE, PARSE_ERROR_MESSAGE, data)


def get_invalid_request_error_dict(data: ErrorDataType = None):
    return ErrorDict(
        code=INVALID_REQUEST_ERROR_CODE,
        message=INVALID_REQUEST_ERROR_MESSAGE,
        data=data
    )


def get_method_not_found_error_dict(data: ErrorDataType = None):
    return ErrorDict(
        code=METHOD_NOT_FOUND_ERROR_CODE,
        message=METHOD_NOT_FOUND_ERROR_MESSAGE,
        data=data
    )


def get_invalid_params_error_dict(data: ErrorDataType = None):
    return ErrorDict(
        code=INVALID_PARAMS_ERROR_CODE,
        message=INVALID_PARAMS_ERROR_MESSAGE,
        data=data
    )


def get_internal_error_dict(data: ErrorDataType = None):
    return ErrorDict(
        code=INTERNAL_ERROR_CODE,
        message=INTERNAL_ERROR_MESSAGE,
        data=data
    )


def get_parse_error_dict(data: ErrorDataType = None):
    return ErrorDict(
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

DefaultInvalidRequestErrorDict = get_invalid_request_error_dict(
    [DefaultInvalidRequestErrorData])

DefaultInvalidRequestError = InvalidRequestError(
    [DefaultInvalidRequestErrorData])

DefaultMethodNotFoundErrorData = ErrorData(
    loc=None,
    msg=None,
    type=METHOD_NOT_FOUND_ERROR_TYPE,
    ctx=None
)

DefaultMethodNotFoundErrorDict = get_method_not_found_error_dict(
    [DefaultMethodNotFoundErrorData])

DefaultMethodNotFoundError = MethodNotFoundError(
    [DefaultMethodNotFoundErrorData])

DefaultInvalidParamsErrorData = ErrorData(
    loc=None,
    msg=None,
    type=INVALID_PARAMS_ERROR_TYPE,
    ctx=None
)

DefaultInvalidParamsErrorDict = get_invalid_params_error_dict(
    [DefaultInvalidParamsErrorData])

DefaultInvalidParamsError = InvalidParamsError(
    [DefaultInvalidParamsErrorData])

DefaultInternalErrorData = ErrorData(
    loc=None,
    msg=None,
    type=INTERNAL_ERROR_TYPE,
    ctx=None
)

DefaultInternalErrorDict = get_internal_error_dict([DefaultInternalErrorData])

DefaultInternalError = InternalError([DefaultInternalErrorData])

DefaultParseErrorData = ErrorData(
    loc=None,
    msg=None,
    type=PARSE_ERROR_TYPE,
    ctx=None
)

DefaultParseErrorDict = get_parse_error_dict([DefaultParseErrorData])

DefaultParseError = ParseError([DefaultParseErrorData])


class ResponseError(JsonRpcModel):
    error: ErrorDict


class ResponseResult(JsonRpcModel):
    result: Any


class FuncSchema(BaseModel):
    func_name: str = Field(alias="funcName")
    parameters: dict


class JsonRpcSchema(BaseModel):
    title: str = "JSON-RPC 2.0"


exceptions = {
    INVALID_REQUEST_ERROR_TYPE: InvalidRequestError,
    METHOD_NOT_FOUND_ERROR_TYPE: MethodNotFoundError,
    INVALID_PARAMS_ERROR_TYPE: TypeError,
    INTERNAL_ERROR_TYPE: InternalError,
    PARSE_ERROR_TYPE: ParseError,
    VALUE_ERROR_TYPE: ValueError
}
