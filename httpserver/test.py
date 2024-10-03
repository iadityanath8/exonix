import socket

HOST = '127.0.0.1'
PORT = 8080

def parse_request(request_data):
    """Parse the HTTP request into method, path, and headers."""
    # Split request into lines
    lines = request_data.split('\r\n')
    
    # Parse the request line (first line)
    if len(lines[0].split(' ')) == 3:
        method, path, http_version = lines[0].split(' ')
    else:
        raise ValueError("Malformed request line")
    
    # Parse headers (lines after the request line)
    headers = {}
    for line in lines[1:]:
        if line == '':  # Empty line indicates end of headers
            break
        header_name, header_value = line.split(': ', 1)
        headers[header_name] = header_value
    
    return method, path, http_version, headers

# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    while True:
        client_socket, client_address = server_socket.accept()
        with client_socket:
            try:
                # Receive and decode request data
                request_data = client_socket.recv(1024).decode()
                # print(f"Raw Request Data:\n{request_data}")

                # Parse the request
                method, path, http_version, headers = parse_request(request_data)
                
                # Print parsed data
                print(f"Method: {method}")
                print(f"Path: {path}")
                print(f"HTTP Version: {http_version}")
                print("Headers:")
                for header, value in headers.items():
                    print(f"{header}: {value}")

                # Send a basic response
                response = "HTTP/1.1 200 OK\r\n"
                response += "Content-Type: text/html\r\n"
                response += "Connection: close\r\n"
                response += "\r\n"
                response += "<html><body><h1>Basic HTTP Server</h1></body></html>"
                
                client_socket.sendall(response.encode())
            
            except ValueError as e:
                print(f"Error parsing request: {e}")
                client_socket.close()
