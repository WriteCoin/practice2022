from functools import partial
from time import sleep
from json_rpc.json_rpc import JsonRPC, notification
import asyncio
from json_rpc.socket_base.send_recv import (
    ClientRecvType,
    ClientSendType,
    RecvType,
    SendType,
)
from json_rpc.socket_base.socket_fabric import client_sr


async def simple_test(send: ClientSendType, recv: ClientRecvType):
    # await send(b'{"jsonrpc": "2.0", "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}')

    await send(
        b'{"jsonrpc": "2.0", "id": 1, "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}'
    )

    # await (partial(send, b'{"jsonrpc": "2.0", "id": 1, "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}'))()

    data = await recv()
    print(data.decode("UTF-8"))


async def json_rpc_test(send: ClientSendType, recv: ClientRecvType):
    client = JsonRPC(send, recv)
    print("Client JSON RPC 2.0")

    # results = await asyncio.gather(
    #     client.call("foo", ["1", "2"]),
    #     client.notify("sleep", 10.0),
    #     client.notify("sleep", 5.0),
    #     client.notify("sleep", 1.0),
    #     client.call("foo", ["3", "4"]),
    # )
    # print(results)

    # for f in asyncio.as_completed(
    #     [
    #         client.call("foo", ["1", "2"]),
    #         client.call("sleep", 10.0),
    #         client.call("sleep", 5.0),
    #         client.call("sleep", 1.0),
    #         client.call("foo", ["3", "4"]),
    #     ]
    # ):
    #     result = await f
    #     print(f"result: {result}")

    # await client.call("sleep", 10.0)
    # await client.call("foo", ["1", "2"])
    # await client.call("sleep", 5.0)
    # await client.call("foo", ["3", "4"])
    # await client.call("sleep", 1.0)

    # await client.send('{"jsonrpc": "2.0", "method": "foo", "params": ["fizz", "buzz"], "id": 1}')

    # assert None == await client.call("sleep", 10.0)

    # assert None == await client.notify("sleep", [2.0])
    # assert "fizzbuzz" == await client.call("foo", args.split(','))
    res = await client.call("foo", {"bar": "fizz", "baz": "buzz"})
    # print(res)
    assert "fizzbuzz" == res

    # res1 = await client.call("foo", ["fizz", "buzz"])
    # sleep(1)
    # res2 = await client.call("foo", {"bar": "fizz", "baz": "buzz"})
    # print(res1)
    # print(res2)
    print("Test success")


async def batch_test(send: ClientSendType, recv: ClientRecvType):
    client = JsonRPC(send, recv)
    print("Client JSON RPC 2.0 Batch Test")

    assert ["ab", "cd"] == await client.batch(
        ("foo", ["a", "b"]),
        notification("sleep", [10.0]),
        ("foo", {"bar": "c", "baz": "d"}),
        notification("sleep", {"interval": 10.0}),
    )

    print(await client.call("schema", []))

    print("Test success")


async def ui_test(send: ClientSendType, recv: ClientRecvType):
    client = await JsonRPC(send, recv)  # type: ignore
    print("Client JSON RPC 2.0 UI Test")

    assert "fizzbuzz" == await client.foo("fizz", "buzz")  # type: ignore
    # type: ignore
    assert "fizzbuzz" == await client.foo(bar="fizz", baz="buzz")
    assert None == await client.notify("sleep", 10)

    print("Test success")


async def run():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            # await simple_test(send, recv)
            # await json_rpc_test(send, recv)
            # await batch_test(send, recv)
            await ui_test(send, recv)
        except Exception as ex:
            print(f"Error: {ex}")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
