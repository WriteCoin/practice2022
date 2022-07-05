# Python API для клиент-сервер приложений на основе JSON-RPC

## Этапы

### 1. Фабрики для send и recv, работа с сокетами в asyncio

Исходный код: `modules/socket_base/socket_fabric.py`.
Демонстрационные примеры: `modules/socket_base/socket_server.py`, `modules/socket_base/socket_client.py`

### 2. Передача JSON-RPC сообщений, вызов удаленной функции

Исходный код: `modules/json_rpc.py`
Демонстрационные примеры: `modules/server.py`, `modules/client.py`

### 3. Обертка в класс JsonRpc с методами register и call

Исходный код: `modules/json_rpc.py`

### 4. Поддержка notify

### 5. Поддержка batch

### 6. Проверка типов

### 7. JSON Schema

### 8. Вызов удаленных функций без call

### 9. Более красивый интерфейс для notify

### 10. Более красивый интерфейс для batch

### 11. Интеграция с ESB
