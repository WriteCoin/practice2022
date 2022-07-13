import threading
from typing import Awaitable, Callable, Optional, TypeAlias


Token: TypeAlias = str

SendType: TypeAlias = Callable[[bytes, Token | None], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[tuple[Token, bytes]]]
Peername: TypeAlias = tuple[str, int]
