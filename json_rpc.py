from copy import copy
from re import A
from typing import Awaitable, Callable
from unicodedata import decimal


class JsonRPC:
  # def __init__(self, send: Awaitable[Callable[[bytes], None]], receive: Awaitable[Callable[[], bytes]]):
  def __init__(self, 
    send: Callable[[bytes], Awaitable[None]],
    recv: Callable[[], Awaitable[bytes]]
  ):
    self.__send = send
    self.__recv = recv
    self.__functions: dict[str, Callable] = {}
    # self.__is_run = False

  def register(self, name: str | None = None):
    # if not self.__is_run:
    #   return
    def decorator(func: Awaitable[Callable] | Callable):
      async def wrapper(*args, **kwargs):
        if not name:
          key = str(func).split(' ')[1]
          self.__functions[key] = func
        else:
          self.__functions[name] = func
        if isinstance(func, Awaitable):
          return await func(*args, **kwargs)
        else:
          return func(*args, **kwargs)
      return wrapper
    return decorator

  def call(self, name: str):
    # if not self.__is_run:
    #   return
    pass

  # def call(self, request: Request):
  #   def decorator(func):
  #     response = JSONRPCResponseManager.handle(
  #       request.data, self.__dispatcher)
  #     return Response(response.json, mimetype='application/json')
  #   return decorator

  async def run(self):
    # self.__is_run = True
    while True:
      yield await self.__recv()
      # await self.__send()
