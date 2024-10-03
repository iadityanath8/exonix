'''

    Make Reactor powerfull and production ready compatible with non-blocking sockets 

'''

from abc import ABC,abstractmethod
import select

class ReactorBase(ABC):
    def __init__(self,_loop) -> None:
        self._read_waiters  = {}
        self._write_waiters = {}
        self._loop         = _loop

    @abstractmethod
    def register_reader(self,fd,task):
        pass

    @abstractmethod
    def reactor_ready(self):
        if self._read_waiters or self._write_waiters:
            return True
        return False
    
    @abstractmethod
    def register_writter(self,fd,task):
        pass
    
    @abstractmethod
    def remove_waiters(self,fd):
        pass

    @abstractmethod
    def poll(self,timeout):
        pass
'''
    A reactor class for interacting with io polling or completion api like 
    epoll poll, select and io_uring type polling api
'''

class SelectReactor(ReactorBase):
    def __init__(self,_loop) -> None:
        super().__init__(_loop)
    
    def register_reader(self,fd,task):
        self._read_waiters[fd] = task
    
    def register_writter(self, fd, task):
        self._write_waiters[fd] = task
    
    def remove_waiters(self, fd):
        if fd in self._read_waiters:
            del self._read_waiters[fd]
        
        elif fd in self._write_waiters:
            del self._write_waiters[fd]
        else:
            raise Exception("File descriptor not available")

    def reactor_ready(self):
        return super().reactor_ready()

    def poll(self, timeout):
        can_read,can_write,_ = select.select(self._read_waiters,self._write_waiters,[],timeout)

        for rfd in can_read:
            self._loop.new_task(self._read_waiters.pop(rfd))

        for wfd in can_write:
            self._loop.new_task(self._write_waiters.pop(wfd))


## TODO : -> improve speed 
class EpollReactor(ReactorBase):
    def __init__(self, _loop) -> None:
        super().__init__(_loop)
        self._epoll = select.epoll()
    

    def register_reader(self, fd, task):
        self._read_waiters[fd.fileno()] = task;
        try:
            self._epoll.register(fd.fileno(),select.EPOLLIN)
        except FileExistsError:
            self._epoll.modify(fd.fileno(),select.EPOLLIN)

    def register_writter(self, fd, task):
        self._write_waiters[fd.fileno()] = task

        try:
            self._epoll.register(fd.fileno(),select.EPOLLOUT)
        except FileExistsError:
            self._epoll.modify(fd.fileno(),select.EPOLLOUT)


    def remove_waiters(self, fd):
        if fd.fileno() in self._read_waiters:
            del self._read_waiters[fd.fileno()]
            self._epoll.unregister(fd.fileno())
        elif fd.fileno() in self._write_waiters:
            del self._write_waiters[fd.fileno()]
            self._epoll.unregister(fd.fileno())
        else:
            raise Exception("File descriptor not available")

    def reactor_ready(self):
        return super().reactor_ready()


    def poll(self, timeout):
        events = self._epoll.poll(timeout)

        for fd, event in events:
            if event & select.EPOLLIN:
                task = self._read_waiters[fd]
                if task:
                    self._loop.new_task(task)

            elif event & select.EPOLLOUT:
                task = self._write_waiters[fd]
                if task:
                    self._loop.new_task(task)

