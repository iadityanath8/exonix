from collections import deque
import heapq
from abc import ABC,abstractmethod
from select import select 
from enum import Enum, auto
import time
import socket


'''
    Async Queue I build a simple async queue 
'''

class AsyncQueue:
    def __init__(self,sched) -> None:
        self.__items   = deque()
        self.__getters = deque()
        self.__sched   = sched
    
    async def get(self):
        if not self.__items:   # if empty 
            self.__getters.append(self.__sched.current)
            self.__sched.current = None
            await kernel_switch()

        return self.__items.popleft()


    async def put(self,val):
        self.__items.append(val)

        if self.__getters:
            self.__sched.new_task(self.__getters.popleft())


'''
    Utilities used in this files
'''
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class State(Enum):
    READY    = auto()
    PENING   = auto()
    FINISHED = auto()


'''
    Basic switching Kernel used in the scheduler for fast context switching context
'''
class KernelSwitcher:
    def __await__(self):
        yield

def kernel_switch():
    return KernelSwitcher()

'''
    Simple Task Wrapper for wrapping coroutine and making scheduler adaptive with callback functions
'''
class _Task:
    
    def __init__(self,coro,sched) -> None:
        self.__coro       =  coro
        self.__sched      =  sched
        self.__return    =  None
        self.__state     =  State.READY
        self.__finished  =  False   
    
    def __call__(self):
        try:
            self.__sched.current = self
            self.__coro.send(None)

            if self.__sched.current:
                self.__sched.new_task(self)
            
        except StopIteration as e:
            self.__finished = True
            self.__state    = State.FINISHED
            self.__return   = e.value


'''
Promise class that will help in recovering the return value from the scheduler 
'''
class Promise:
    def __init__(self,sched):
        self.__val   = None 
        self.__done  = False
        self.__state = State.READY
        self.__sched = sched
        self.__callback = deque()

    def set_value(self,val):
        self.__val  = val
        self.__done = False
        if self.__callback:
            self.__sched.new_task(self.__callback.popleft())

    async def value(self):
        if not self.__done:
            # awaiting the result or say waiting for the result to happen in here 
            self.__callback.append(self.__sched.current)
            self.__sched.current = None
            await kernel_switch()

        return self.__val

'''
    In future we are going to implement the Base class for scheduler so that we can have multiple scheduler and 
    event loop
'''
class Scheduler:
    def __init__(self) -> None:
        self.__ready    = deque()
        self.__sleeping = []      # Min Heap 
        self.__id       = 0
        self.current    = None

        # IO 
        self.__read_waiters  = { }  # waiting area for reading file descriptor TODO  
        self.__write_waiters = { }  # waiting area for writting file descriptors  TODO 

    async def sleep(self,delay):
        self.__id += 1
        deadline = delay + time.time()
        heapq.heappush(self.__sleeping,(deadline,self.__id,self.current))
        self.current = None
        await kernel_switch()

    def new_task(self,_task):
        if isinstance(_task,_Task):
            self.__ready.append(_task)
        else:
            self.__ready.append(_Task(_task,self))
    
    def spawn(self,_task):
        self.new_task(_task)
        self.run_loop()

    def read_wait(self,fileno,_task):
        self.__read_waiters[fileno] = _task

    def write_wait(self,fileno,_task):
        self.__write_waiters[fileno] = _task

    def gather(self,*args):
        for t in args:
            self.new_task(t)
        self.run_loop()

    def run_loop(self):

        '''
            
            Not for production 

            Deprecated
    
        '''
        while (self.__ready or self.__sleeping or self.__read_waiters or self.__write_waiters):
            if not self.__ready:
                if self.__sleeping:
                    deadline,_, func = self.__sleeping[0]
                    timeout = deadline - time.time()
                    if timeout < 0:
                        timeout = 0
                else:
                    timeout = None
                
                can_read,can_write,[] = select(self.__read_waiters,self.__write_waiters,[],timeout)
                for rfd in can_read:    self.new_task(self.__read_waiters.pop(rfd))
                for wfd in can_write:   self.new_task(self.__write_waiters.pop(wfd))

                now = time.time()
                while self.__sleeping:
                    if now > self.__sleeping[0][0]:
                        self.new_task(heapq.heappop(self.__sleeping)[2])
                    else:
                        break

            self.current = self.__ready.popleft()
            self.current()


'''

    Never Use Deprecated(())

'''
class EventLoop(metaclass=SingletonMeta):
    pass


class _RawSocket:
    def __init__(self,sock,addr,sched:Scheduler) -> None:
        self.__sock  = sock
        self.__addr  = addr
        self.__sched = sched

    async def send(self,data):
        self.__sched.write_wait(self.__sock,self.__sched.current)
        self.__sched.current = None
        await kernel_switch()
        return self.__sock.send(data)

    async def recv(self,max_bytes):
        self.__sched.read_wait(self.__sock,self.__sched.current)
        self.__sched.current = None
        await kernel_switch()
        return self.__sock.recv(max_bytes)

    def close(self):
        self.__sock.close()



class TcpSocket:
    def __init__(self,PORT,sched:Scheduler) -> None:
        self.__raw_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__raw_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.__raw_sock.bind(('localhost',PORT))
        self.__raw_sock.listen(12)
        self.__sched = sched

    async def accept(self):
        self.__sched.read_wait(self.__raw_sock,self.__sched.current)
        self.__sched.current = None 
        await kernel_switch() 
        client,addr = self.__raw_sock.accept()
        return _RawSocket(client,addr,self.__sched)

    def close(self):
        self.__raw_sock.close()


sched = Scheduler()

async def main():
    sock = TcpSocket(1234,sched)
    while True:
        client = await sock.accept()
        sched.new_task(echo_handler(client))

async def echo_handler(cli:_RawSocket):
    while True:
        data = await cli.recv(1024)
        if not data:
            cli.close()
            print("Connection closed")
            break
        await cli.send(data)

q = AsyncQueue(sched)
async def producer():
    for i in range(10):
        await q.put(i)
        print("Produced: ",i)
        await sched.sleep(1)

async def consumer():
    for _ in range(10):
        item = await q.get()
        await sched.sleep(2)
        print("Got: ",item)

'''
Tests
'''
fut = Promise(sched)
#   Hail Nemesis

async def ff():
    print('running in here')
    await kernel_switch()

    return 12

async def f():
    c = await ff()
    print(c)
    return 1


sched.new_task(f())
sched.run_loop()
