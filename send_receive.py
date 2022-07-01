from abc import ABC, abstractmethod

class Communication(ABC):
  @abstractmethod
  async def send(self, message: bytes) -> None:
    pass

  @abstractmethod
  async def recv(self) -> bytes:
    pass