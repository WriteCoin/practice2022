from socket_fabric import server_sr


@server_sr("127.0.0.1", 9999)
async def on_connection(send, recv):
  print("Wait request")
  assert b"hello" == await recv()
  print("Send response")
  await send(b"world")