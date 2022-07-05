from copy import copy
from encodings.utf_8 import encode
import inspect
from re import A
from typing import Any, Awaitable, Callable, Literal, TypeAlias
from unicodedata import decimal
from pydantic import BaseModel
from socket_base.send_recv import RecvType, SendType


  
FuncType: TypeAlias = Awaitable[Callable] | Callable

ParamType: TypeAlias = list[Any] | dict[str, Any]

class ProcRequest(BaseModel):
  method: str
  params: ParamType

class ResponseWithError(BaseModel):
  error: dict[Literal["message"], str]

class Response(BaseModel):
  result: Any

def get_func_name(func: FuncType) -> str:
  func_full_path = str(func).split(' ')[1]
  if func_full_path.find('.<locals>.') != -1:
    paths_to_func = func_full_path.split('.<locals>.')
    path_to_func = paths_to_func[len(paths_to_func) - 1]
  else:
    path_to_func = func_full_path
  func_parts = path_to_func.split('.')
  name_func = func_parts[len(func_parts) - 1]
  return name_func

def validate_func_args(func: FuncType, args: ParamType):
  func_spec = inspect.getfullargspec(func)
  anno_types = func_spec.annotations
  i = 0
  for key in anno_types:
    if key != 'return':
      # print(f"arg name: {key}, arg type: {anno_types[key]}")
      value = args[i] if isinstance(args, list) else args[key]
      # print(f"type value: {type(value)}")
      if type(value) != anno_types[key]:
        raise ValueError
      i += 1
    else:
      i -= 1

class JsonRPC:
  def __init__(self, 
    send: SendType,
    recv: RecvType
  ):
    self.__send = send
    self.__recv = recv
    self.__functions: dict[str, FuncType] = {}
    # self.__is_run = False

  def register(self, name: str | None = None):
    # if not self.__is_run:
    #   return
    def decorator(func: FuncType):
      # print(f"register func: {func}")
      if name is None:
        key = get_func_name(func)
      else:
        key = name
      # print(f"func name: {key}")
      self.__functions[key] = func
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

  def schema(self) -> dict:
    return {}

  async def run(self):
    # self.__is_run = True
    # print(f"functions: {self.__functions}")
    response = None
    try:
      bytes = await self.__recv()
      data = bytes.decode("UTF-8")
      request = ProcRequest.parse_raw(data)
      func = self.__functions[request.method]
      # print("Validation data")
      # validate_func_args(func, request.params)
      print("result...")
      result = func(*request.params) if isinstance(request.params, list) else func(**request.params)
    except Exception as err:
      # print(f"Error: {err}")
      error_data = {"error": {"message": str(err)}}
      response = ResponseWithError(**error_data)
      # print(response)
    else:
      # print("Block no error")
      result_data = {"result": result}
      response = Response(**result_data)
    await self.__send(response.json().encode("UTF-8"))
    # await self.__send()
    # args_data = inspect.getfullargspec(self.__functions[request.method])
    # print(args_data)
    # await self.__send(request)