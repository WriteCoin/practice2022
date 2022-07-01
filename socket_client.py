import asyncio
from socket_fabric import client_sr


async def main():
  send, recv = client_sr("127.0.0.1", 9999)
  await send(b"hello")
  assert b"world" == await recv()
  print("Сообщение world получено")

if __name__ == '__main__':
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(main())
  finally:
    pass