import asyncio
from encodings.utf_8 import decode
from socket_fabric import client_sr


async def main():
  send, recv, writer = await client_sr("127.0.0.1", 9999)
  try:
    print("Send request")
    await send(b"hello")
    print("Wait response")
    data = await recv()
    assert b"world" == data
    print("Response received")
  except Exception as ex:
    print(f"Error: {ex}")
  finally:
    print("Close the connection")
    writer.close()
    await writer.wait_closed()

if __name__ == '__main__':
  asyncio.run(main())