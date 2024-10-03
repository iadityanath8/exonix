from .kernel import kernel_switch
from collections import deque
import heapq
import time
from .job import Job
from enum import Enum,auto
from abc import ABC,abstractmethod
from .reactor import *

class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls,*args,**kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args,**kwargs)

        return cls._instances[cls]

class ExecutorBase(ABC):
    
    def __init__(self) -> None:
        pass
    
    @abstractmethod
    def register_read(self,fd,task):
        """Register the file descriptor of a resource such as socket and 
            a file waiting to read 
        """
        pass

    @abstractmethod
    def register_write(self,fd,task):
        """Register the file descriptor of a resource such as socket and 
            a file waiting to write to a network resource such as socket 
            or a file 
        """
        pass

    @abstractmethod
    def new_task(self,task):
        """ Register a coroutine to the scheduler's task queue from where it is polled by 
            scheduling policy
        """
        pass

    @abstractmethod
    def delay_task(self,task,delay):
        """
            Register a task which need to be called after a given time 
        """
        pass
    
    @abstractmethod
    def run():
        """
            Start the eventLoop to process the given tasks for polling and running 
        """
        pass

class TaskExecutor(metaclass=SingletonMeta):
    def __init__(self) -> None:
        if not hasattr(self,'_initialized'):
            self._initialized     = True
            self.__readyTask     = deque()
            self.__sleepingTask  = []
            self.__current       = None 
            self.__id            = 0
                    
            
            '''
                 IO Reactor will be used in here to 
                 Interacto with low level api like 
                 system like api such as EPOLL SELECT POLL a
                 and the completion api's like IO_URING 
            '''

            self.__reactor = SelectReactor(self)
            # self.__reactor = EpollReactor(self)

    def get_current(self):
        return self.__current
    
    def set_current(self,current):
        self.__current = current


    '''Ensures the pushed value is a _Task'''
    def __create_task(self,_task):
        if not isinstance(_task,Job):
            raise Exception("Argument Passed is not a acceptable type")
            
        self.__readyTask.append(_task)

    def new_task(self,_task):
        prom = None
        if isinstance(_task,Job):
            self.__create_task(_task)
            prom = _task
        else:
            prom = Job(_task)
            self.__create_task(prom)
        return prom
    
    def read_wait(self,fileno,task):
        self.__reactor.register_reader(fileno,task)
    
    def write_wait(self,fileno,task):
        self.__reactor.register_writter(fileno,task)

    async def sleep(self,delay):
        self.call_later(self.__current,delay)
        self.__current = None 
        await kernel_switch()
    
    def close_epoll(self,fd):
        self.__reactor.remove_waiters(fd)

    ''' experimental right now '''
    def call_later(self,task,delay):
        self.__id += 1
        deadline = delay + time.time()

        if isinstance(task,Job):
            heapq.heappush(self.__sleepingTask,(deadline,self.__id,task))
        else:
            heapq.heappush(self.__sleepingTask,(deadline,self.__id,Job(task)))   

    
    ''' Experimental kind of now we can use another loop in here we should have build in system for different loops

        TODO --> Try to use a epoll or iouring api for fast event notification 
                 so that we can process more request 

                 suggestion try to use another event policy for running 
                 multiple tasks a policy which should be much faster 
                 for monitoring tasks  
    '''
    
    def run_default_policy(self):

        while (self.__readyTask or self.__sleepingTask or self.__reactor.reactor_ready()):

            if not self.__readyTask:

                if self.__sleepingTask:
                    deadline,_ ,func = self.__sleepingTask[0]
                    timeout = deadline - time.time()

                    if timeout < 0:
                        timeout = 0
                else:
                    timeout = None 
                
                # Sleeping done in here OK Method select has a timeout which actually helps giving illusion that
                # particular task is sleeping 

                '''
                    Polling from the Reactor api 
                    
                '''
                # print(timeout)
                self.__reactor.poll(timeout)
                
                time_now = time.time()
                while self.__sleepingTask:
                    if time_now > self.__sleepingTask[0][0]:
                        self.__create_task(heapq.heappop(self.__sleepingTask)[2])
                    else:
                        break

            self.__current = self.__readyTask.popleft()
            self.__current()


''' 
        Base Policy Locks soon we will make it more fast and powerful 
'''

class Lock:
    class LockState(Enum):
        ACQUIRED = auto()
        RELEASED = auto()

    def __init__(self,exe) -> None:
        self.__lock      =  self.LockState.RELEASED
        self.__waiters   =  deque()            
        self.__executor  =  exe

    def __repr__(self) -> str:
        if self.__lock == self.LockState.ACQUIRED:
            return f"<Lock on {self.__executor.get_current()} {self.__lock}>"
        else:
            return f"<Lock finished {self.__lock}>"

    async def acquire(self):
        if self.__lock == self.LockState.ACQUIRED:
            # wait 
            self.__waiters.append(self.__executor.get_current())
            self.__executor.set_current(None)
            await kernel_switch()
        else:        
            self.__lock = self.LockState.ACQUIRED

    def release(self):
        self.__lock = self.LockState.RELEASED
        
        if self.__waiters:
            self.__executor.new_task(self.__waiters.popleft())


class Barrier:
    class BarrierState(Enum):
        WAITING  = auto()
        FINISHED = auto()

    def __init__(self,count,exe) -> None:
        self.__idx      =  0
        self.__count    =  count
        self.__waiters  =  deque()
        self.__state    =  self.BarrierState.WAITING
        self.__executor =  exe

    async def wait(self):
        self.__idx += 1
        
        if self.__idx < self.__count:
            self.__waiters.append(self.__executor.get_current())
            self.__executor.set_current(None)
            await kernel_switch()

        else:
            for i in self.__waiters:
                self.__executors.new_task(self.__waiters.popleft())



def getloop():
    return TaskExecutor()

async def sleep(delay):
    loop = getloop()
    loop.call_later(loop.get_current(),delay)
    loop.set_current(None)
    await kernel_switch()

def start(task):
    _loop = getloop()
    res = _loop.new_task(task)
    _loop.run_default_policy()
    return res.inner_val_unsafe()

def converge(*args):
    _loop = getloop()
    res = []

    for i in args:
        res.append(_loop.new_task(i))

    return res


__all__ = ['getloop','sleep','start','converge']