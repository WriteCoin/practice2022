import asyncio
import traceback
from json_rpc.socket_base.socket_fabric import client_sr


async def run():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            for i in range(2):
                print("Send request")
                await send(b"hello")
                print("Wait response")
                _, recv_data = await recv()
                data = recv_data.decode("UTF-8")
                print(f"data: {data}")
                assert b"world" == recv_data
                print("Response received")
        except Exception as ex:
            print(f"Error: {ex}")
            print(traceback.format_exc())


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
