from typing import Awaitable, Callable, TypeAlias


SendType: TypeAlias = Callable[[bytes], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[bytes]]