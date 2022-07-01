from copy import copy
from re import A
from typing import Any, Awaitable, Callable, TypeAlias
from unicodedata import decimal
from pydantic import BaseModel


class ProcRequest(BaseModel):
  method: str
  params: list[Any] | dict[str, Any]

SendType: TypeAlias = Callable[[bytes], Awaitable[None]]
RecvType: TypeAlias = Callable[[], Awaitable[bytes]]
FuncType: TypeAlias = Awaitable[Callable] | Callable

class JsonRPC:
  # def __init__(self, send: Awaitable[Callable[[bytes], None]], receive: Awaitable[Callable[[], bytes]]):
  def __init__(self, 
    send: SendType,
    recv: RecvType
  ):
    self.__send = send
    self.__recv = recv
    self.send = send
    self.recv = recv
    self.__functions: dict[str, FuncType] = {}
    # self.__is_run = False

  def register(self, name: str | None = None):
    # if not self.__is_run:
    #   return
    def decorator(func: FuncType):
      if not name:
        key = str(func).split(' ')[1]
        self.__functions[key] = func
      else:
        self.__functions[name] = func
      async def wrapper(*args, **kwargs):
        if isinstance(func, Awaitable):
          return await func(*args, **kwargs)
        else:
          return func(*args, **kwargs)
      return wrapper
    return decorator

  def call(self, data: ProcRequest) -> Any:
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
      bytes = await self.__recv()
      if not bytes:
        continue
      await self.__send(bytes)
      # try:
      #   # request = str(bytes, 'UTF-8')
      #   data = ProcRequest.parse_raw(bytes)
      #   self.__functions[data.method]
        
      #   result = self.call(data)
      #   await self.__send(result)
      # except Exception as e:
      #   await self.__send()