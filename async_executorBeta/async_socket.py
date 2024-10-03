from scheduler import AsyncScheduler,kernel_switch
import socket

class _RawSocket:
    def __init__(self,sock,addr,sched:AsyncScheduler) -> None:
        self.__sock  = sock
        self.__addr  = addr
        self.__sched = sched 

    async def send(self,data):
        self.__sched.write_wait(self.__sock,self.__sched.curr_exe_coro)
        self.__sched.curr_exe_coro = None
        await kernel_switch()
        return self.__sock.send(data)

    async def recv(self,max_bytes):
        self.__sched.read_wait(self.__sock,self.__sched.curr_exe_coro)
        self.__sched.curr_exe_coro = None
        await kernel_switch()                 # kernel switch to another retrieve control back to event loop 
        return self.__sock.recv(max_bytes)
      

    def close(self):
        self.__sock.close()


class AsyncronousTcpSocket: 
    def __init__(self,PORT,sched:AsyncScheduler) -> None:
        self.__socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
        self.__sched = sched
        self.__socket.bind(('localhost',PORT))
        self.__socket.listen(12)

        
    async def accept(self):
        self.__sched.read_wait(self.__socket,self.__sched.curr_exe_coro)
        self.__sched.curr_exe_coro = None
        await kernel_switch()
        client, addr = self.__socket.accept()    # blocking operation 
        return _RawSocket(client,addr,sched)
    

    def close(self):
        self.__socket.close()


sched = AsyncScheduler()

async def main():
    sock = AsyncronousTcpSocket(1234,sched)
    while True:
        rclient = await sock.accept()
        sched.new_task(echo_handler(rclient))

async def echo_handler(cli:_RawSocket):
    while True:
        data = await cli.recv(1024)
        resp = data.decode('utf-8')
        if data:
            await cli.send(data)
        else:
            break
    
    cli.close()
    print("Connection closed")


async def method():
    while True:
        print("Hello owlr")
        await sched.sleep(2)

async def call_me():
    while True:
        print("Non empty")
        await kernel_switch()

sched.gather(main())