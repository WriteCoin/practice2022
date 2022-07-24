import asyncio
import secrets
import string
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, AsyncGenerator, Dict, Optional, Tuple, Union

from json_rpc.socket_base.send_recv import (ClientRecvType, ClientSendType,
                                            Peername, Token)

writers: Dict[Token, Optional[asyncio.StreamWriter]] = {}
read_queue: asyncio.Queue = asyncio.Queue()


def get_data_to_read(line: bytes) -> bytes:
    """
        Returns a whole message in bytes from a string of bytes.
    :param line: data in bytes
    :return bytes
    """
    return line[: len(line) - 1]


def get_data_to_send(message: bytes) -> bytes:
    """
        Sends a byte message as a full string.
    :param message: message in bytes
    :return bytes
    """
    return message + b"\n\n"


def is_data_empty(data: bytes) -> bool:
    """
        Checks the emptiness of the incoming message.
    :param data: message in bytes
    :return bool
    """
    return data == b"\n" or data == b"" or len(data) == 0


def new_token() -> Token:
    """
        Generates a new token to differentiate the connected clients by the server.
    :return Token
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(20))


async def read(reader: asyncio.StreamReader, token: Optional[Token] = None):
    """
        The function of registering all incoming messages on the server side.
        Registers non-empty incoming messages and writes them together with the token to the asynchronous queue.
    :param reader: the thread responsible for reading
    :param token: string ID of the client
    :return
    """
    async for line in reader:
        if not is_data_empty(line):
            await read_queue.put((token, get_data_to_read(line)))


async def server_recv() -> Tuple[Token, bytes]:
    """
        receiving a message on the server side.
    :return Token and bytes
    """
    return await read_queue.get()


async def client_recv() -> bytes:
    """
        receiving a message on the client side.
    :return bytes
    """
    _, data = await read_queue.get()
    return data


async def server_send(
    message: bytes, token: Union[Token, asyncio.StreamWriter]
) -> None:
    """
        Sending a message on the server side.
    :param message: message in bytes
    :param token: Token or writer stream when connecting a new client
    :return
    """
    if isinstance(token, Token):
        writer = writers[token]
    else:
        writer = token
    if not writer is None:
        writer.write(get_data_to_send(message))
        await writer.drain()


async def disconnect(writer: asyncio.StreamWriter, addr: Optional[Peername] = None):
    """
        Disconnection from the connected party.
    :param writer: stream writer required for this
    :param addr: a tuple with an address and a port. Optional parameter
    :return
    """
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
    """
        Creating a new client. Opens a socket connection.
        Used as an asynchronous context manager.
        It is used as an asynchronous context manager that works with the server_send and client_recv functions
        Upon completion of the function, the connection is closed.
        When creating a client, a task is created to read all incoming messages
    :param addr: IP address of client
    :param port: port
    :return asynchronous context manager with (send, recv)
    """
    reader, writer = await asyncio.open_connection(addr, port)
    try:
        asyncio.create_task(read(reader))
        yield (partial(server_send, token=writer), client_recv)
    finally:
        await disconnect(writer)


async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
        Connecting a new client to a single socket server.
        Standard callback function for asyncio.start_server operation
        When creating a client, a task is created to read all incoming messages
        When the client connects, a task is created and put on hold to read all incoming messages.
    :param reader: read stream for socket
    :param writer: writer stream for socket
    :return
    """
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
    """
        Creating a socket server.
        It is used as an asynchronous context manager that works with the server_send and server_recv functions
    :param addr: IP address of the server
    :param port: port
    :return asynchronous context manager with (send, recv)
    """
    socket_server = await asyncio.start_server(client_connected, addr, port)
    print(f"Socket server has been started on port {port}")
    server_task = asyncio.create_task(socket_server.serve_forever())
    yield server_send, server_recv
    await server_task
