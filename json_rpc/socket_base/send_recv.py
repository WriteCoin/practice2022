import threading
from typing import Awaitable, Callable, Optional, TypeAlias


SendType: TypeAlias = Callable[[bytes], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[bytes]]
Peername: TypeAlias = tuple[str, int]
# ServerCallback: TypeAlias = Callable[[SendType, RecvType, Optional[str]], Awaitable[None]]
ServerCallback: TypeAlias = Callable[[SendType, RecvType], Awaitable[None]]


Token: TypeAlias = object


class DisconnectException(Exception):
    def __str__(self) -> str:
        return "Disconnect"
