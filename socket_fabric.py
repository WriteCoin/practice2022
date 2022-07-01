import socket
from json_rpc import RecvType, SendType
import socket

BUFF_SIZE = 1024

def client_sr(addr: str, port: int) -> tuple[SendType, RecvType]:
  try:
    sock = socket.socket()
    sock.connect((addr, port))
    async def send(message: bytes):
      return sock.send(message)
    async def recv() -> bytes:
      return sock.recv(BUFF_SIZE)
  except Exception as err:
    print(err)
    sock.close()
  return (send, recv)

def server_sr(addr: str, port: int, listen_count: int = 1):
  sock = socket.socket()
  sock.bind((addr, port))
  sock.listen(listen_count)
  def actual_decorator(func):
    async def wrapper(send: SendType, recv: RecvType):
      conn, addr = sock.accept()
      print(f"Connected: {addr}")
      async def on_send(message: bytes):
        return conn.send(message)
      async def on_recv() -> bytes:
        return conn.recv(BUFF_SIZE)
      try:
        while True:
          # data = await on_recv()
          # if not data:
          #   continue
          await func(on_send, on_recv)
      except Exception as ex:
        print(ex)
        print(f"Закрытие соединения: {addr}")
        conn.close()
    return wrapper
  return actual_decorator