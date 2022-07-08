import threading
from typing import Awaitable, Callable, TypeAlias


SendType: TypeAlias = Callable[[bytes], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[bytes]]

class DisconnectException(Exception):
    def __str__(self) -> str:
        return "Disconnect"

class NotifyExcept(Exception):
    def __str__(self) -> str:
        return "Notify"

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper