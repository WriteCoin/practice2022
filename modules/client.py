from json_rpc import JsonRPC
import asyncio
from socket_base.socket_fabric import client_sr


async def main():
  send, recv, writer = await client_sr("127.0.0.1", 9999)
  try:
    await send(b'{ "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}')
    data = await recv()
    print(data.decode("UTF-8"))
  except Exception as ex:
    print(f"Error: {ex}")
  finally:
    print("Close the connection")
    writer.close()
    await writer.wait_closed()

if __name__ == '__main__':
  asyncio.run(main())