import socket
from send_receive import Communication

sock = socket.socket()
conn, addr = sock.accept()

class SocketCommunication(Communication):
  pass