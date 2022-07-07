from practice2022.json_rpc.json_rpc import JsonRPC
import asyncio
from practice2022.json_rpc.socket_base.socket_fabric import client_sr

async def run():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            await send(b'{ "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}')
            data = await recv()
            print(data.decode("UTF-8"))
        except Exception as ex:
            print(f"Error: {ex}")

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
