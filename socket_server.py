from json_rpc.socket_base.send_recv import RecvType, SendType
from json_rpc.socket_base.socket_fabric import server_sr


def main():
    @server_sr("127.0.0.1", 9999)
    async def on_connection(send: SendType, recv: RecvType):
        for i in range(2):
            print("Wait request")
            recv_data = await recv()
            data = recv_data.decode("UTF-8")
            print(f"data: {data}")
            assert b"hello" == recv_data
            print("Send response")
            await send(b"world")


if __name__ == "__main__":
    main()
