import asyncio
from time import sleep
from json_rpc.json_rpc import JsonRPC
from json_rpc.socket_base.socket_fabric import server_sr


def main():
    @server_sr("127.0.0.1", 9999)
    async def on_connection(send, recv):
        server = JsonRPC(send, recv)

        @server.register
        def foo(bar: str, baz: str) -> str:
            return bar + baz

        @server.register(name="sleep")
        async def new_sleep(interval: float) -> None:
            print(f"Received {interval!r}")
            await asyncio.sleep(interval)
            print("Finished")

        @server.register
        def schema() -> dict:
            return server.schema()

        @server.register
        def sample_func():
            pass

        await server.run()


if __name__ == "__main__":
    main()
