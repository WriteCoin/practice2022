import pickle
from time import sleep
from send_receive import Communication

class FileCommunication(Communication):
  def __init__(self, filepath: str) -> None:
    self.__filepath = filepath

  async def send(self, message: bytes) -> None:
    with open(self.__filepath, "wb") as file:
      pickle.dump(message, file)

  async def recv(self) -> bytes:
    with open(self.__filepath, "rb") as file:
      return pickle.load(file)