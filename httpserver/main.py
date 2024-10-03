import socket
import os
import mimetypes
import urllib.parse
import json
from threading import Thread

HOST = '127.0.0.1'
PORT = 8080

def get_file_content(file_path):
    """Read the content of the file."""
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            return file.read()
    else:
        return None

def get_content_type(file_path):
    """Determine the MIME type of the file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def parse_form_data(request_data):
    """Parse form data from the POST request."""
    headers, body = request_data.split('\r\n\r\n', 1)
    content_type = [line for line in headers.split('\r\n') if line.startswith('Content-Type:')][0]
    if 'application/x-www-form-urlencoded' in content_type:
        form_data = urllib.parse.parse_qs(body)
        return {key: value[0] for key, value in form_data.items()}
    return {}


def handle_request(request_data):
    """Parse the request and generate the appropriate response with CORS headers."""
    lines = request_data.split('\r\n')
    if not lines or len(lines) < 1:
        return b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<html><body><h1>400 Bad Request</h1></body></html>"

    request_line = lines[0]
    try:
        method, path, _ = request_line.split(' ')
    except ValueError:
        return b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<html><body><h1>400 Bad Request</h1></body></html>"

    cors_headers = "Access-Control-Allow-Origin: *\r\n"
    response = b""

    if method == 'GET':
        response = handle_get(path)
    elif method == 'POST':
        response = handle_post(request_data)
    elif method == 'PUT':
        response = handle_put(request_data)
    elif method == 'DELETE':
        response = handle_delete(path)
    else:
        response = handle_not_supported()

    # Ensure the CORS headers are added correctly
    if isinstance(response, bytes):
        if b"HTTP/1.1 200 OK\r\n" in response:
            response = response.replace(b"HTTP/1.1 200 OK\r\n", b"HTTP/1.1 200 OK\r\n" + cors_headers.encode())
        else:
            response = response.replace(b"HTTP/1.1", b"HTTP/1.1" + cors_headers.encode())
    else:
        response = response.replace("HTTP/1.1 200 OK\r\n", f"HTTP/1.1 200 OK\r\n{cors_headers}")

    return response


def handle_get(path):
    """Handle GET requests."""
    if path == '/':
        path = 'index.html'
    file_content = get_file_content(path)
    content_type = get_content_type(path)

    if file_content:
        response = "HTTP/1.1 200 OK\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(file_content)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response = response.encode() + file_content
    else:
        response = "HTTP/1.1 404 Not Found\r\n"
        response += "Content-Type: text/html\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += "<html><body><h1>404 Not Found</h1></body></html>"
        response = response.encode()

    return response

def handle_post(request_data):
    """Handle POST requests with JSON and display data on an HTML page."""
    headers, body = request_data.split('\r\n\r\n', 1)
    
    try:
        # Try to parse the body as JSON
        json_data = json.loads(body)
        name = json_data.get('name', 'No name received')
        email = json_data.get('email', 'No email received')
    except json.JSONDecodeError:
        name = 'Invalid JSON data'
        email = ''

    # Generate an HTML response to display the data
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: text/html\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    response += f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Submission Result</title>
    </head>
    <body>
        <h1>POST Data Received</h1>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
    </body>
    </html>
    """

    print(response)
    return response.encode()


def handle_put(request_data):
    """Handle PUT requests."""
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: text/html\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    response += "<html><body><h1>PUT Request Received</h1></body></html>"
    return response.encode()

def handle_delete(path):
    """Handle DELETE requests."""
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: text/html\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    response += f"<html><body><h1>DELETE Request for {path} Received</h1></body></html>"
    return response.encode()

def handle_not_supported():
    """Handle unsupported HTTP methods."""
    response = "HTTP/1.1 405 Method Not Allowed\r\n"
    response += "Content-Type: text/html\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    response += "<html><body><h1>405 Method Not Allowed</h1></body></html>"
    return response.encode()

def handle_client(client_socket):
    """Handle client connections in a separate thread."""
    try:
        while True:
            request_data = client_socket.recv(1024).decode()
            if not request_data:
                break
            print(f"Request data: {request_data}")

            response = handle_request(request_data)
            print(f"response is {response}")

            client_socket.sendall(response)
            # Ensure the response is fully sent
            client_socket.shutdown(socket.SHUT_WR)
    finally:
        client_socket.close()


# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Serving HTTP on port {PORT}...")

    while True:
        client_socket, client_address = server_socket.accept()
        Thread(target=handle_client, args=(client_socket,)).start()
