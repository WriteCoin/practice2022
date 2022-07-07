from practice2022.json_rpc.socket_base.socket_fabric import server_sr


def main():
    @server_sr("127.0.0.1", 9999)
    async def on_connection(send, recv):
        print("Wait request")
        assert b"hello" == await recv()
        print("Send response")
        await send(b"world")

if __name__ == '__main__':
    main()
