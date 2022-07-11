from time import sleep
from json_rpc.json_rpc import JsonRPC
import asyncio
from json_rpc.socket_base.send_recv import RecvType, SendType
from json_rpc.socket_base.socket_fabric import client_sr


async def simple_test(send: SendType, recv: RecvType):
    await send(
        b'{"jsonrpc": "2.0", "method": "foo", "params": {"bar": "fizz", "baz": "buzz"}}'
    )
    data = await recv()
    print(data.decode("UTF-8"))


async def json_rpc_test(send: SendType, recv: RecvType):
    client = JsonRPC(send, recv)
    print("Client JSON RPC 2.0")
    assert None == await client.notify("sleep", 10.0)
    # assert None == await client.notify("sleep", [10.0])
    assert "fizzbuzz" == await client.call("foo", ["fizz", "buzz"])
    # assert "fizzbuzz" == await client.call("foo", {"bar": "fizz", "baz": "buzz"})
    # res1 = await client.call("foo", ["fizz", "buzz"])
    # sleep(1)
    # res2 = await client.call("foo", {"bar": "fizz", "baz": "buzz"})
    # print(res1)
    # print(res2)
    print("Test success")


async def run():
    async with client_sr("127.0.0.1", 9999) as (send, recv):
        try:
            # await simple_test(send, recv)
            await json_rpc_test(send, recv)
        except Exception as ex:
            print(f"Error: {ex}")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()