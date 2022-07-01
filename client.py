from file_send_receive import FileCommunication
from json_rpc import JsonRPC

comm = FileCommunication("file")

client = JsonRPC(comm.send, comm.recv)