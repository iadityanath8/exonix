class Kernel_Pause:    
    def __await__(self):
        yield


def kernel_switch():
    return Kernel_Pause()
