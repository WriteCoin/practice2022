from time import sleep
from file_send_receive import FileCommunication
from json_rpc import JsonRPC


comm = FileCommunication("file")

server = JsonRPC(comm.send, comm.recv)

@server.register(None)
def foo(bar: str, baz: str) -> str:
  return bar + baz

@server.register(name="sleep")
async def new_sleep(interval: float) -> None:
  print(f"Received {interval!r}")
  sleep(interval)
  print("Finished")

try:
  server.run()
except Exception as e:
  print(e)
else:
  print("Server has been started...")