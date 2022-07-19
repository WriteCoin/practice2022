import asyncio
from time import sleep
from json_rpc.server import ServerJsonRPC
from json_rpc.socket_base.socket_fabric import server_sr


async def run():
    addr = "127.0.0.1"
    port = 9999

    async with server_sr(addr, port) as (send, recv):
        server = ServerJsonRPC(send, recv, addr)

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


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
