import asyncio
from contextlib import asynccontextmanager
from functools import partial
import secrets
import string
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional
from json_rpc.socket_base.send_recv import (
    ClientRecvType,
    ClientSendType,
    DisconnectException,
    Peername,
    RecvType,
    SendType,
    ServerCallback,
    Token,
    key_with_value,
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
    return data == b"\n" or data == b"" or len(data) == 0


def new_token() -> Token:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(20))


def is_data_disconnect(data: bytes) -> bool:
    return data.decode(DEFAULT_ENCODING) == DISCONNECT_COMMAND


async def read(reader: asyncio.StreamReader, token: Token = None):
    async for line in reader:
        if not is_data_empty(line):
            if not is_data_disconnect(line):
                line = get_data_to_read(line)
            # else:
            #     raise DisconnectException
            await read_queue.put((token, line))
            # await read_queue.put((token, line))


async def server_recv() -> tuple[Token, bytes]:
    token, data = await read_queue.get()
    if is_data_disconnect(data):
        raise DisconnectException
    return (token, data)

    while True:
        token, data = await read_queue.get()
        if data.decode(DEFAULT_ENCODING) == DISCONNECT_COMMAND:
            raise DisconnectException
        if not is_data_empty(data):
            return (token, get_data_to_read(data))


async def server_send(message: bytes, token: Token | asyncio.StreamWriter) -> None:
    if isinstance(token, Token):
        writer = writers[token]
    else:
        writer = token
    writer.write(get_data_to_send(message))
    # writer.write(message)
    # writer.writelines([message])
    await writer.drain()


async def client_recv(reader: asyncio.StreamReader):
    # return get_data_to_read(await reader.readline())
    # return await reader.readline()
    # return await reader.read()

    while True:
        line = await reader.readline()
        line = get_data_to_read(line)
        if line:
            return line


async def client_send(message: bytes, writer: asyncio.StreamWriter) -> None:
    writer.write(get_data_to_send(message))
    # writer.write(message)
    # writer.writelines([message])
    await writer.drain()


async def client_part_send(send: SendType, message: bytes):
    return partial(send, message=message)


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
    # token: Token = key_with_value(writers, writer)
    # token_b = await client_recv(reader)
    # token = token_b.decode(DEFAULT_ENCODING)
    try:
        client_task = asyncio.create_task(read(reader))
        client_task
        yield (partial(server_send, token=writer), server_recv)
    finally:
        await disconnect(writer)
    # yield (partial(client_send, writer=writer), partial(client_recv, reader=reader))


async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    print(f"Connected: {addr}")
    token = new_token()
    print(f"Token: {token}")
    writers[token] = writer
    # await server_send(str(token).encode(DEFAULT_ENCODING), token)
    task = asyncio.create_task(read(reader, token))
    await task
    await disconnect(writer, addr)


@asynccontextmanager
async def server_sr(addr: str, port: int):
    socket_server = await asyncio.start_server(client_connected, addr, port)
    print(f"Socket server has been started on port {port}")
    server_task = asyncio.create_task(socket_server.serve_forever())
    yield server_send, server_recv
    await server_task
