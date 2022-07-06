import asyncio
from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncGenerator, Optional
from socket_base.send_recv import RecvType, SendType


async def send(message: bytes, writer: asyncio.StreamWriter) -> None:
    writer.write(message + b"\n\n")
    await writer.drain()


async def recv(reader: asyncio.StreamReader) -> bytes:
    data = await reader.readline()
    return data[: len(data) - 1]


@asynccontextmanager
async def client_sr(
    addr: str, port: int
) -> AsyncGenerator[tuple[SendType, RecvType], None]:
    reader, writer = await asyncio.open_connection(addr, port)
    try:
        yield (partial(send, writer=writer), partial(recv, reader=reader))
    finally:
        print("Close the connection")
        writer.close()
        await writer.wait_closed()


def server_sr(addr: str, port: int):
    def actual_decorator(func):
        async def wrapper(send: SendType, recv: RecvType):
            await func(send, recv)

        async def client_connected(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ):
            addr = writer.get_extra_info("peername")
            print(f"Connected: {addr}")
            try:
                await wrapper(
                    partial(send, writer=writer), partial(recv, reader=reader)
                )
            except Exception as ex:
                print(f"Error: {ex}")
            finally:
                print(f"Close the connection: {addr}")
                writer.close()
                await writer.wait_closed()

        async def new_server():
            server = await asyncio.start_server(client_connected, addr, port)
            print("Server launched")
            async with server:
                await server.serve_forever()

        asyncio.run(new_server())
        return wrapper

    return actual_decorator
