from collections import deque
from enum import Enum, auto
from .kernel import kernel_switch


'''
    Promise Object helps to retain the result of any asyncronous operation 
    which tends to run in a eventloop of the executor 

    ********     NOT THREAD SAFE   ********

'''
class Promise:
    class State(Enum):
        CANCELLED = auto()
        PENDING   = auto()
        FINISHED  = auto()

    def __init__(self) -> None:
        from . import executor
        self.__value      =  None
        self.__callbacks  =  deque()
        self.__state      =  self.State.PENDING
        self.__done       =  False
        self.__executor   =  executor.getloop()

    def __await__(self):
        
        ''' This functions like a get_value in a only awiting
          the promise will yield in a result of the folowing promise '''

        if self.__state == self.State.PENDING or self.__done == False:
            self.__callbacks.append(self.__executor.get_current())
            self.__executor.set_current(None)
            yield

        return self.__value
    
    def __repr__(self) -> str:

        if self.__state == self.State.PENDING or self.__state == self.State.CANCELLED:
            return f"<Promise {self.__state}>"
        else:
            return f"<Promise {self.__state} value={self.__value}>"

    async def get_value(self):

        ''' 
                Get the value of a promise and if another task is not running in a main eventloop which
                sets the result then it immediately returns and stops the execution 
                and if another task is available in a eventloop then it kind of waits and polls that task 

                which can possibly set the value of promise 

                which implies it does not pause and does not wait for another thread which means this t
                thing is not thread safe 

        '''

        if self.__done == False:
            self.__state = self.State.PENDING
            self.__callbacks.append(self.__executor.get_current())
            self.__executor.set_current(None)
            await kernel_switch()

        return self.__value
    
    def set_value(self,value):

        ''' 
            Sets the value of a promise running in a coroutine evented evironment whenever it sets the 
            value then it noties the getters to get the following values resulting in a 
            smooth syncotrnization 
        '''

        self.__value = value
        self.__done  = True
        self.__state = self.State.FINISHED

        '''Wake up all the functions sleeping in the waitqueue'''
        while self.__callbacks:
            self.__executor.new_task(self.__callbacks.popleft())


__all__ = ['Promise']
# import executor