# Python API для клиент-сервер приложений на основе JSON-RPC

## Этапы

### 1. Фабрики для send и recv, работа с сокетами в asyncio

* Исходный код: `json_rpc/socket_base/socket_fabric.py`, `json_rpc/socket_base/send_recv.py`.
* Демонстрационные примеры: `socket_server.py`, `socket_client.py`.

### 2. Передача JSON-RPC сообщений, вызов удаленной функции

* Исходный код: `json_rpc/server.py`, `json_rpc/client.py`.
* Демонстрационные примеры: `server.py`, `client.py`, функция `simple_test`.

### 3. Обертка в класс JsonRpc с методами register и call

* Исходный код: `json_rpc/server.py`, `json_rpc/client.py`.
* Демонстрационные примеры: `server.py`, `client.py`, функция `json_rpc_test`.

### 4. Поддержка notify

* Демонстрационные примеры: `client.py`, функция `json_rpc_test`.

### 5. Поддержка batch

* Демонстрационные примеры: `client.py`, функция `batch_test`.

### 6. Проверка типов

* Демонстрационные примеры: `client.py`, функция `valid_types_test`.

### 7. JSON Schema

* Исходный код: `json_rpc/server.py`
* Демонстрационные примеры: `server.py`, `client.py`, функция `batch_test`.

### 8. Вызов удаленных функций без call

* Исходный код: `json_rpc/client.py`, класс `CallNotifyGasket`
* Демонстрационные примеры: `server.py`, `client.py`, функция `item_attr_test`.

### 9. Более красивый интерфейс для notify

* Исходный код: `json_rpc/client.py`, класс `CallNotifyGasket`
* Демонстрационные примеры: `server.py`, `client.py`, функция `item_attr_test`.

### 10. Более красивый интерфейс для batch

* Исходный код: `json_rpc/client.py`, класс `BatchGasket`
* Демонстрационные примеры: `server.py`, `client.py`, функция `item_attr_test`.

### 11. Интеграция с ESB

Планируется в дальнейшем.