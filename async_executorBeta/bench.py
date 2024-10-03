import socket
import time

def benchmark_echo_client(host, port, message, repetitions):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        
        # Record start time
        start_time = time.time()
        
        for _ in range(1000):
            sock.sendall(message.encode())
            data = sock.recv(len(message))
            print(data)
        
        # Record end time
        end_time = time.time()
    
    duration = end_time - start_time
    requests_per_second = repetitions / duration
    
    print(f"Time taken for {repetitions} repetitions: {duration:.2f} seconds")
    print(f"Average time per round-trip: {duration / repetitions:.6f} seconds")
    print(f"Requests per second: {requests_per_second:.2f} req/sec")

def main():
    host = '127.0.0.1'
    port = 8888
    message = "Hello, World!"
    repetitions = 1000  # Number of messages to send
    
    benchmark_echo_client(host, port, message, repetitions)

if __name__ == '__main__':
    main()
