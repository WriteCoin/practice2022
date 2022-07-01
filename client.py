from file_send_receive import FileCommunication
from json_rpc import JsonRPC
import asyncio


async def main():
  comm = FileCommunication("file")
  client = JsonRPC(comm.send, comm.recv)
  await client.send(b'hello, world!')
  data = await client.recv()
  print(str(data, 'UTF-8'))

if __name__ == '__main__':
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(main())
  finally:
    pass