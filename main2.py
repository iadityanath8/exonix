from exonix import getloop,start,kernel_switch
import socket 


async def accept(sock:socket.socket):
    _loop = getloop()
    _loop.read_wait(sock,_loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.accept()

async def send(sock:socket.socket,data):
    _loop = getloop()
    _loop.write_wait(sock,_loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.send(data)

async def recv(sock:socket.socket,max_bytes=1024):
    _loop = getloop()
    _loop.read_wait(sock,_loop.get_current())
    _loop.set_current(None)
    await kernel_switch()
    
    return sock.recv(max_bytes)


async def main():
    server_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    
    server_sock.bind(('localhost',8080))
    server_sock.listen(socket.SOMAXCONN)
    
    print("Server Started at 8080")
    while True:
        client,_ = await accept(server_sock)
        _loop = getloop()
        _loop.new_task(handleClient(client))
        
        
async def handleClient(client:socket.socket):
    while True:
        data = await recv(client)
        if not data:
            break
        
        await send(client,data)

start(main())
