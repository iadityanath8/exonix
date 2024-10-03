import exonix
from concurrent.futures import ThreadPoolExecutor as pool
import time

def fib(n):
    if n <= 1:
        return 1
    return fib(n-1) + fib(n-2)


async def run():
    while True:
        print("Hail Nemesis to the ultimate time of 2016 and 2017")
        _loop = exonix.getloop()
        _loop.new_task(run1())


async def run1():   
    time.sleep(3)
    print("Meow world")

loop = exonix.getloop()

loop.new_task(run())
p = pool(2)

p.submit(loop.run_default_policy)
p.submit(loop.run_default_policy)

p.shutdown(wait=True)