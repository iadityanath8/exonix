import heapq
from collections import deque
from select import select
import time
from enum import Enum, auto

class KernelPause:
    def __await__(self):
        yield

def kernel_switch():
    return KernelPause()

class TaskState(Enum):
    READY = auto()
    PENDING = auto()
    FINISHED = auto()

class PromiseState(Enum):
    READY    = auto()
    PENDING  = auto()
    FINISHED = auto()


class Promise:
    def __init__(self,sched) -> None:
        self.__val        = None
        self.__finished   = False
        self.__callbacks  =  []
        self.__sched      = sched

    def set_result(self,val):
        self.__val = val
        self.__finished = True
        
        for tasks in self.__callbacks:
            self.__sched.new_task(tasks)

    async def result(self):
        if not self.__finished:
            self.__callbacks.append(self.__sched.curr_exe_coro)
            self.__sched.curr_exe_coro = None
            await kernel_switch()   # we have to look into the swithching 
        
        return self.__val
    
class Task:
    def __init__(self,coro,sched) -> None:
        self.__coro        = coro
        self.__sched       = sched
        self.__state       = TaskState.READY
        self.__finished    = False
        self.__return      = None

    def result(self):
        return self.__return
    

    def __call__(self):
        try:
            self.__state = TaskState.PENDING
            self.__sched.curr_exe_coro = self
            self.__coro.send(None)
            
            if self.__sched.curr_exe_coro:
                self.__sched.new_task(self)

        except StopIteration as e:
            self.__return = e.value
            self.__state  = TaskState.FINISHED

    def __repr__(self) -> str:
        return f"<Task state={self.__state}>"


class AsyncScheduler:
    def __init__(self) -> None:
        self.__ready = deque()
        self.__sleeping = []
        self.curr_exe_coro = None
        self.tid = 0
        self.return_values   = { }  # Not in a production right now 
        
        # IO
        self.__read_waiters  = { }
        self.__write_waiters = { }

    def new_task(self,task):
        if not isinstance(task,Task):
            t_task = Task(task,self)
            self.__ready.append(t_task)
            return t_task
        else:
            self.__ready.append(task)
            return task    

    def read_wait(self,fileno,task):
        if isinstance(task,Task):
            self.__read_waiters[fileno] = task
        else:
            self.__read_waiters[fileno] = Task(task,self)

    def write_wait(self,fileno,task):
        if isinstance(task,Task):
            self.__write_waiters[fileno] = task
        else:
            self.__write_waiters[fileno] = Task(task,self)
        
    async def sleep(self,delay):
        self.tid += 1
        deadline = time.time() + delay
        heapq.heappush(self.__sleeping,(deadline,self.tid,self.curr_exe_coro))
        self.curr_exe_coro = None
        await kernel_switch()

    def spawn(self,task):
        self.new_task(task)
        self.run_loop()
    
    async def awaiter_task(self):
        pass
    
    def print_task(self):
        print(self.__ready)
    
    def gather(self,*args):
        for i in args:
            self.new_task(i)
        self.run_loop()

    def run_loop(self):
        while (self.__ready or self.__sleeping or self.__read_waiters or self.__write_waiters):
            if not self.__ready:
            
                if self.__sleeping:
                    deadline,_ ,task = self.__sleeping[0]
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
                    if now > self.__sleeping[0][0]: # Direct breaking 
                        self.new_task(heapq.heappop(self.__sleeping)[2])
                    else:
                        break

            self.curr_exe_coro = self.__ready.popleft()
            self.curr_exe_coro()

                



# sched = AsyncScheduler()
# k = Promise(sched)
# async def re():
#     await sched.sleep(1)
#     k.set_result(121)
#     return "returned the value"
    
# async def noreturn():
#     # await sched.sleep(1)
#     return "no return "


# f = Promise(sched)

# async def runnner():
#     for _ in range(5):
#         print("I a runner in here")
#         await sched.sleep(1)

#     f.set_result(12)

# async def main():
#     sched.new_task(runnner())
#     sched.new_task(re())
#     l = await f.result()
#     r = await k.result()
#     print("Hail Nemsis",l,r)

# # sched.new_task(main())

# # sched.run_loop()
# print(r.result())
# print(l.result())