import asyncio
from socket_fabric import server_sr

@server_sr("127.0.0.1", 9999)
async def on_connection(send, recv):
  assert b"hello" == await recv()
  await send(b"world")

if __name__ == '__main__':
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(on_connection(None, None))
  finally:
    pass