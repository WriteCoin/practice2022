import queue
import socket
from json_rpc import RecvType, SendType
import select

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

def server_sr(addr: str, port: int, listen_count: int = 5):
  server = socket.socket()
  server.setblocking(False)
  server.bind((addr, port))
  server.listen(listen_count)

  print("Server launched")

  inputs = [server]
  outputs: list[socket.socket] = []
  message_queues: dict[socket.socket, queue.Queue] = {}

  def actual_decorator(func):

    def read_server_socket(s: socket.socket) -> tuple[SendType, RecvType]:
      connection, client_address = s.accept()
      connection.setblocking(False)
      inputs.append(connection)
      message_queues[connection] = queue.Queue()
      print(f"Connected: {addr}")
      async def on_send(message: bytes):
        return connection.send(message)
      async def on_recv() -> bytes:
        return connection.recv(BUFF_SIZE)
      return (on_send, on_recv)

    def read_client_socket(s: socket.socket):
      data = s.recv(BUFF_SIZE)
      if data:
        message_queues[s].put(data)
        if s not in outputs:
          outputs.append(s)
      else:
        if s in outputs:
          outputs.remove(s)
        inputs.remove(s)
        s.close()
        del message_queues[s]
        print(f"Закрытие соединения: {addr}")

    
    def write_socket(s: socket.socket):
      try:
        next_msg = message_queues[s].get_nowait()
      except queue.Empty:
        outputs.remove(s)
      else:
        s.send(next_msg)

    def except_socket(s: socket.socket):
      inputs.remove(s)
      if s in outputs:
        outputs.remove(s)
      s.close()
      del message_queues[s]
      print(f"Закрытие соединения: {addr}")


    # async def wrapper(send: SendType, recv: RecvType):
    async def wrapper():

      async def on_send(message: bytes):
        pass

      async def on_recv() -> bytes:
        pass

      while inputs:
        readable, writeable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
          if s is server:
            read_server_socket(s)
          else:
            read_client_socket(s)
        for s in writeable:
          write_socket(s)
        for s in exceptional:
          except_socket(s)

      return

      conn, addr = sock.accept()
      async def on_connect():
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
      await on_connect()
      # await on_connect()
      # type:ignore
      # PID = os.fork()
      # if PID:
      #   await on_connect()
      # else:
      #   await wrapper(send, recv)
    return wrapper
  return actual_decorator