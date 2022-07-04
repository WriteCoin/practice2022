import asyncio
from socket_fabric import client_sr


async def main():
  send, recv = client_sr("127.0.0.1", 9999)
  text = input()
  # await send(b"hello")
  await send(text.encode("UTF-8"))
  assert b"world" == await recv()
  print("Сообщение world получено")

if __name__ == '__main__':
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(main())
  finally:
    pass