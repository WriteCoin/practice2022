from typing import Awaitable, Callable, Tuple, Union

Token = str

SendType = Callable[[bytes, Token], Awaitable[None]]
RecvType = Callable[[], Awaitable[Tuple[Token, bytes]]]
ClientSendType = Callable[[bytes], Awaitable[None]]
ClientRecvType = Callable[[], Awaitable[bytes]]
Peername = Tuple[str, int]
