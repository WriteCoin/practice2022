import asyncio
from json_rpc.socket_base.send_recv import RecvType, SendType
from json_rpc.socket_base.socket_fabric import server_sr


async def run():
    async with server_sr("127.0.0.1", 9999) as (send, recv):
        for i in range(2):
            print("Wait request")
            token, recv_data = await recv()
            data = recv_data.decode("UTF-8")
            print(f"data: {data}")
            print(len(data))
            print(b"hello" == recv_data)
            assert b"hello" == recv_data
            print("Send response")
            await send(b"world", token)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
