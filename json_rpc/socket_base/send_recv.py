import threading
from typing import Awaitable, Callable, Optional, TypeAlias


Token: TypeAlias = str

SendType: TypeAlias = Callable[[bytes, Token], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[tuple[Token, bytes]]]
ClientSendType: TypeAlias = Callable[[bytes], Awaitable[None]]
ClientRecvType: TypeAlias = Callable[[], Awaitable[bytes]]
Peername: TypeAlias = tuple[str, int]
# ServerCallback: TypeAlias = Callable[[SendType, RecvType, Optional[str]], Awaitable[None]]
ServerCallback: TypeAlias = Callable[[SendType, RecvType], Awaitable[None]]


def key_with_value(dict, value, default=None):
    for k, v in dict.iteritems():
        if v == value:
            return v
    return default


class DisconnectException(Exception):
    def __str__(self) -> str:
        return "Disconnect"
