import socket
from threading import Thread
from abc import ABC, abstractmethod
import select

class TcpServer(ABC):
    def __init__(self, PORT) -> None:
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('localhost', PORT))
        self.server_sock.listen(12)

    @abstractmethod
    def run(self, on_handle):
        pass

    
class SingleThreadedTcpServer(TcpServer):
    def __init__(self, PORT) -> None:
        super().__init__(PORT)

    def run(self, on_handle):
        while True:
            client, _ = self.server_sock.accept()
            on_handle(client)


class MultithreadedTcpServer(TcpServer):
    def __init__(self, PORT) -> None:
        super().__init__(PORT)

    def run(self, on_handle) -> None:
        while True:
            client, _ = self.server_sock.accept()
            Thread(target=on_handle, args=(client,)).start()


class AsyncronousTcpServer(TcpServer):
    def __init__(self, PORT) -> None:
        super().__init__(PORT)
        self.server_sock.setblocking(False)
        self._readers = [self.server_sock]  
        self._writers = []
        self._message_queue = {}

    def remove_client(self, client_sock):
        """Remove a client socket from the readers, writers, and close it."""
        # print(f"Client {self.clients[client_sock]} disconnected.")
        if client_sock in self.readers:
            self.readers.remove(client_sock)
        if client_sock in self.writers:
            self.writers.remove(client_sock)
        client_sock.close()
        if client_sock in self.message_queues:
            del self.message_queues[client_sock]

    def run(self,on_read,on_write):
        while True:
            can_read,can_write, [] = select.select(self._readers,self._writers,[])

            for r in can_read:
                if r is self.server_sock:
                    client, _ = r.accept()
                    client.setblocking(False)
                    self._readers.append(client)
                    self._message_queue[client] = []
                else:
                    try:
                            flg, response = on_read(r)
                            if flg:
                                self._message_queue[r].append(response)
                            
                                if r not in self._writers:
                                    self._writers.append(r)


                    except ConnectionResetError:
                        self.remove_client(r)
            
            for w in can_write:
                if self._message_queue[w]:
                    message = self._message_queue[w].pop(0)
                    try:
                        on_write(w,message)
                    except BrokenPipeError:
                        self.remove_client(w)

                if not self._message_queue[w]:
                    self._writers.remove(w)



def on_read_handle(cli):
    data = cli.recv(1024)
    flg = True
    response = ""
    if data:
        message = data.decode('utf-8')
        response = f"ECHO: {message}"
    else:
        flg = False
    return flg, response

def on_write_handle(cli,message):
    cli.sendall(message.encode())

# Example usage with MultithreadedTcpServer
m = AsyncronousTcpServer(1234)
m.run(on_read_handle,on_write_handle)