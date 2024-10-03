from .promise import Promise

''' Represents a wrapped coroutine with the helps of future retains the result of a function 
    that returns the value in a asyncronouse envirnonment when scheduled in a executors 
    eventLoop
'''
class Job(Promise):
    
    def __init__(self,coro) -> None:
        super().__init__()
        self.__coro = coro  

    def inner_val_unsafe(self):
        return self._Promise__value
    
    def __repr__(self):
        if self._Promise__state == self.State.PENDING or self._Promise__state == self.State.CANCELLED:
            return f"<Job {self._Promise__state}>"
        else:
            return f"<Job {self._Promise__state}> value={self._Promise__value}"

    def __call__(self):
        try:
            self._Promise__executor.set_current(self)
            self.__coro.send(None)

            if self._Promise__executor.get_current():
                self._Promise__executor.new_task(self)
        
        except StopIteration as e:
            self._Promise__state = self.State.FINISHED
            self._Promise__done  = True
            self.set_value(e.value)
        

__all__ = ['Job']