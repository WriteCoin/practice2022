import asyncio
from json_rpc.socket_base.socket_fabric import client_sr


async def run():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            print("Send request")
            await send(b"hello")
            print("Wait response")
            data = await recv()
            assert b"world" == data
            print("Response received")
        except Exception as ex:
            print(f"Error: {ex}")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
