import asyncio
from contextlib import asynccontextmanager
from functools import partial
import secrets
import string
from typing import Any, AsyncGenerator, Dict, Optional, Tuple, Union
from json_rpc.socket_base.send_recv import (
    ClientRecvType,
    ClientSendType,
    Peername,
    RecvType,
    SendType,
    Token,
)


DISCONNECT_COMMAND = "disconnect"
DEFAULT_ENCODING = "UTF-8"
NOTIFY_COMMAND = "notify"

writers: Dict[Token, Optional[asyncio.StreamWriter]] = {}
read_queue: asyncio.Queue = asyncio.Queue()


def get_data_to_read(line: bytes) -> bytes:
    return line[: len(line) - 1]


def get_data_to_send(message: bytes) -> bytes:
    return message + b"\n\n"


def is_data_empty(data: bytes) -> bool:
    return data == b"\n" or data == b"" or len(data) == 0


def new_token() -> Token:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(20))


def is_data_disconnect(data: bytes) -> bool:
    return data.decode(DEFAULT_ENCODING) == DISCONNECT_COMMAND


async def read(reader: asyncio.StreamReader, token: Optional[Token] = None):
    async for line in reader:
        if not is_data_empty(line):
            await read_queue.put((token, get_data_to_read(line)))


async def server_recv() -> Tuple[Token, bytes]:
    return await read_queue.get()


async def client_recv() -> bytes:
    _, data = await read_queue.get()
    return data


async def server_send(
    message: bytes, token: Union[Token, asyncio.StreamWriter]
) -> None:
    if isinstance(token, Token):
        writer = writers[token]
    else:
        writer = token
    if not writer is None:
        writer.write(get_data_to_send(message))
        await writer.drain()


async def disconnect(writer: asyncio.StreamWriter, addr: Optional[Peername] = None):
    if addr is None:
        print("Close the connection")
    else:
        print(f"Close the connection: {addr}")
    writer.close()
    await writer.wait_closed()


@asynccontextmanager
async def client_sr(
    addr: str, port: int
) -> AsyncGenerator[Tuple[ClientSendType, ClientRecvType], None]:
    reader, writer = await asyncio.open_connection(addr, port)
    try:
        asyncio.create_task(read(reader))
        yield (partial(server_send, token=writer), client_recv)
    finally:
        await disconnect(writer)


async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    print(f"Connected: {addr}")
    token = new_token()
    print(f"Token: {token}")
    writers[token] = writer
    task = asyncio.create_task(read(reader, token))
    await task
    await disconnect(writer, addr)
    writers[token] = None


@asynccontextmanager
async def server_sr(addr: str, port: int):
    socket_server = await asyncio.start_server(client_connected, addr, port)
    print(f"Socket server has been started on port {port}")
    server_task = asyncio.create_task(socket_server.serve_forever())
    yield server_send, server_recv
    await server_task
