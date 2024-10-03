import socket
import select
import errno

# Configuration
HOST = '127.0.0.1'  # Server address
PORT = 3000          # Server port

def main():
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    # Set the server socket to non-blocking mode
    server_socket.setblocking(False)

    # Create an epoll object
    epoll = select.epoll()
    
    # Register the server socket with epoll
    epoll.register(server_socket.fileno(), select.EPOLLIN)

    # A dictionary to store client sockets
    clients = {}

    try:
        while True:
            # Wait for events
            events = epoll.poll()  # Block until there are events

            for fileno, event in events:
                if fileno == server_socket.fileno():
                    # Accept a new client connection
                    client_socket, addr = server_socket.accept()
                    
                    # Set the client socket to non-blocking mode
                    client_socket.setblocking(False)

                    # Register the client socket with epoll
                    epoll.register(client_socket.fileno(), select.EPOLLIN)
                    
                    # Store the client socket in the dictionary
                    clients[client_socket.fileno()] = client_socket

                elif event & select.EPOLLIN:
                    # Read data from a client socket
                    client_socket = clients[fileno]
                    try:
                        data = client_socket.recv(1024)
                        if data:
                            # Echo the data back to the client
                            client_socket.sendall(data)
                        else:
                            # Client has closed the connection

                            epoll.unregister(fileno)
                            client_socket.close()
                            del clients[fileno]
                    except OSError as e:
                        # Handle errors (like client disconnect)
                        if e.errno != errno.ECONNRESET:
                            raise
                        epoll.unregister(fileno)
                        client_socket.close()
                        del clients[fileno]

    finally:
        # Clean up
        epoll.unregister(server_socket.fileno())
        epoll.close()
        server_socket.close()

if __name__ == "__main__":
    main()

