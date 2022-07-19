import threading
from typing import Awaitable, Callable, Optional, Tuple, Union


Token = str

SendType = Union[
    Callable[[bytes, Token], Awaitable[None]], Callable[[bytes], Awaitable[None]]
]
RecvType = Callable[[], Awaitable[Tuple[Token, bytes]]]
ClientSendType = Callable[[bytes], Awaitable[None]]
ClientRecvType = Callable[[], Awaitable[bytes]]
Peername = Tuple[str, int]
