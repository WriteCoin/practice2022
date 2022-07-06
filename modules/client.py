from modules.json_rpc import JsonRPC
import asyncio
from modules.socket_base.socket_fabric import client_sr


async def main():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            await send(b'{ "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}')
            data = await recv()
            print(data.decode("UTF-8"))
        except Exception as ex:
            print(f"Error: {ex}")


if __name__ == "__main__":
    asyncio.run(main())
