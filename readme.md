# Exonix

**Exonix** is a powerful asynchronous coroutine executor library for Python, designed to handle asynchronous I/O operations and coroutine scheduling effortlessly. It simplifies concurrent programming, allowing developers to build scalable and responsive applications with ease.

## Features

- 📈 **Efficient Asynchronous I/O Handling**: Exonix provides simple APIs for managing non-blocking I/O operations using coroutines, making it easy to write asynchronous code.
- ⚡ **Flexible Coroutine Scheduling**: With a robust coroutine scheduler, Exonix enables smooth interleaving and management of concurrent tasks, optimizing performance.
- 🔄 **Non-blocking Event Loop**: Exonix employs a non-blocking event loop, ensuring that your applications remain responsive by efficiently handling I/O without blocking execution.
- 🔧 **Easy Integration**: The library integrates seamlessly with existing Python socket operations, making it suitable for network programming and real-time applications.

## Getting Started

### Prerequisites

- Python 3.7 or later

### Installation

You can install Exonix using pip:

```bash
pip install exonix
```


```python 
from exonix import getloop, start, kernel_switch
import socket

async def accept(sock: socket.socket):
    _loop = getloop()
    _loop.read_wait(sock, _loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.accept()

async def send(sock: socket.socket, data):
    _loop = getloop()
    _loop.write_wait(sock, _loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.send(data)

async def recv(sock: socket.socket, max_bytes=1024):
    _loop = getloop()
    _loop.read_wait(sock, _loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.recv(max_bytes)

async def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_sock.bind(('localhost', 8080))
    server_sock.listen(socket.SOMAXCONN)
    
    print("Server Started at 8080")
    while True:
        client, _ = await accept(server_sock)
        _loop = getloop()
        _loop.new_task(handleClient(client))

async def handleClient(client: socket.socket):
    while True:
        data = await recv(client)
        if not data:
            break
        
        await send(client, data)

start(main())
```




## Feel free to modify any sections, such as adding installation instructions or usage examples specific to your library. Let me know if you need any additional changes!