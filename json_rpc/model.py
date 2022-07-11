from typing import Any, Awaitable, Callable, TypeAlias, TypedDict
from pydantic import BaseModel, Field


FuncType: TypeAlias = Callable[(...), Awaitable[None]] | Callable

ParamType: TypeAlias = list[Any] | dict[str, Any]


class JsonRpcModel(BaseModel):
    json_rpc: str = Field(alias="jsonrpc")
    id: int | None


class ProcRequest(JsonRpcModel):
    method: str
    params: ParamType


class Error(TypedDict):
    code: int
    message: str


InvalidRequestError = Error(code=-32600, message="Invalid request")
MethodNotFoundError = Error(code=-32601, message="Method not found")
InvalidParamsError = Error(code=-32602, message="Invalid params")
InternalError = Error(code=-32603, message="Internal error")
ParseError = Error(code=-32700, message="Parse error")


class ResponseError(JsonRpcModel):
    error: Error


class ResponseResult(JsonRpcModel):
    result: Any


class InternalErrorException(Exception):
    def __str__(self) -> str:
        return InternalError["message"]
