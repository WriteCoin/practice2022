import asyncio
from contextlib import asynccontextmanager
from functools import partial
import threading
from typing import AsyncGenerator, Awaitable, Callable, Optional
from json_rpc.socket_base.send_recv import DisconnectException, RecvType, SendType


DISCONNECT_COMMAND = "disconnect"
DEFAULT_ENCODING = "UTF-8"
NOTIFY_COMMAND = "notify"

async def send(message: bytes, writer: asyncio.StreamWriter) -> None:
    writer.write(message + b"\n\n")
    await writer.drain()

async def notify(writer: asyncio.StreamWriter) -> None:
    writer.write(NOTIFY_COMMAND.encode(DEFAULT_ENCODING))
    await writer.drain()

async def recv(reader: asyncio.StreamReader) -> bytes:
    # data = await reader.readline()
    # return data[: len(data) - 1]
    while True:
        data = await reader.readline()
        if data.decode(DEFAULT_ENCODING) == DISCONNECT_COMMAND:
            raise DisconnectException
        data = data[: len(data) - 1]
        if data:
            return data

async def disconnect(writer: asyncio.StreamWriter):
    print("Close the connection")
    writer.write(DISCONNECT_COMMAND.encode(DEFAULT_ENCODING))
    await writer.drain()
    writer.close()
    await writer.wait_closed()
            

@asynccontextmanager
async def client_sr(
    addr: str, port: int
) -> AsyncGenerator[tuple[SendType, RecvType], None]:
    reader, writer = await asyncio.open_connection(addr, port)
    try:
        yield (partial(send, writer=writer), partial(recv, reader=reader))
    finally:
        await disconnect(writer)

async def client_connected(
    reader: asyncio.StreamReader, 
    writer: asyncio.StreamWriter,
    wrapper: Callable[[SendType, RecvType, Optional[str]], Awaitable[None]]
):
    addr = writer.get_extra_info("peername")
    print(f"Connected: {addr}")
    try:
        await wrapper(
            partial(send, writer=writer), partial(recv, reader=reader), addr
        )
    except Exception as ex:
        print(f"Error: {ex}")
    finally:
        await recv(reader)
        await disconnect(writer)

async def new_server(addr: str, port: int, wrapper: Callable[[SendType, RecvType, Optional[str]], Awaitable[None]]):
    server = await asyncio.start_server(partial(client_connected, wrapper=wrapper), addr, port)
    print("Server launched")
    async with server:
        await server.serve_forever()

def server_sr(addr: str, port: int):
    def actual_decorator(func):
        async def wrapper(send: SendType, recv: RecvType, addr: Optional[str]):
            await func(send, recv)

        asyncio.run(new_server(addr, port, wrapper))

        # def thread_callback():
        #     asyncio.run(new_server(addr, port, wrapper))

        # thread = threading.Thread(target=thread_callback, args=())
        # thread.start()

        # async def client_connected(
        #     reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        # ):
        #     addr = writer.get_extra_info("peername")
        #     print(f"Connected: {addr}")
        #     try:
        #         await wrapper(
        #             partial(send, writer=writer), partial(recv, reader=reader), addr
        #         )
        #     except Exception as ex:
        #         print(f"Error: {ex}")
        #     finally:
        #         print(f"Close the connection: {addr}")
        #         writer.close()
        #         await writer.wait_closed()

        # async def new_server():
        #     server = await asyncio.start_server(client_connected, addr, port)
        #     print("Server launched")
        #     async with server:
        #         await server.serve_forever()

        # asyncio.run(new_server())
        return wrapper

    return actual_decorator
