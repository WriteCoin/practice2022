import asyncio
from contextlib import asynccontextmanager
from functools import partial
import traceback
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional
from json_rpc.socket_base.send_recv import (
    DisconnectException,
    Peername,
    RecvType,
    SendType,
    ServerCallback,
    Token,
)


DISCONNECT_COMMAND = "disconnect"
DEFAULT_ENCODING = "UTF-8"
NOTIFY_COMMAND = "notify"

writers: dict[Token, asyncio.StreamWriter] = {}
read_queue: asyncio.Queue = asyncio.Queue()


def get_data_to_read(line: bytes) -> bytes:
    return line[: len(line) - 1]


def get_data_to_send(message: bytes) -> bytes:
    return message + b"\n\n"


def is_data_empty(data: bytes) -> bool:
    return data == b"\n"


def new_token() -> Token:
    return object()


async def read(reader: asyncio.StreamReader, token: Token):
    async for line in reader:
        # await read_queue.put((token, get_data_to_read(line)))
        await read_queue.put((token, line))

async def server_recv() -> tuple[Token, bytes]:
    return await read_queue.get()

async def server_send(message: bytes, token: Token) -> None:
    writer = writers[token]
    # writer.write(get_data_to_send(message))
    writer.write(message)
    # writer.writelines([message])
    await writer.drain()


async def client_recv(reader: asyncio.StreamReader) -> bytes:
    # return get_data_to_read(await reader.readline())
    # return await reader.readline()
    return await reader.read()

    # while True:
    #     line = await reader.readline()
    #     line = get_data_to_read(line)
    #     if line:
    #         return line

async def client_send(message: bytes, writer: asyncio.StreamWriter) -> None:
    # writer.write(get_data_to_send(message))
    writer.write(message)
    # writer.writelines([message])
    await writer.drain()


async def notify(writer: asyncio.StreamWriter) -> None:
    writer.write(NOTIFY_COMMAND.encode(DEFAULT_ENCODING))
    await writer.drain()


async def disconnect(writer: asyncio.StreamWriter, addr: Optional[Peername] = None):
    if addr is None:
        print("Close the connection")
        writer.write(DISCONNECT_COMMAND.encode(DEFAULT_ENCODING))
        await writer.drain()
    else:
        print(f"Close the connection: {addr}")
    writer.close()
    await writer.wait_closed()


@asynccontextmanager
async def client_sr(
    addr: str, port: int
) -> AsyncGenerator[tuple[SendType, RecvType], None]:
    reader, writer = await asyncio.open_connection(addr, port)
    # try:
    #     yield (partial(client_send, writer=writer), partial(client_recv, reader=reader))
    # finally:
    #     await disconnect(writer)
    yield (partial(client_send, writer=writer), partial(client_recv, reader=reader))


async def client_connected(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    addr = writer.get_extra_info("peername")
    print(f"Connected: {addr}")
    token = new_token()
    print(f"Token: {token}")
    writers[token] = writer
    asyncio.create_task(read(reader, token))

@asynccontextmanager
async def server_sr(addr: str, port: int):
    socket_server = await asyncio.start_server(client_connected, addr, port)
    print(f"Socket server has been started on port {port}")
    server_task = asyncio.create_task(socket_server.serve_forever())
    yield server_send, server_recv
    await server_task
