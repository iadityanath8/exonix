import asyncio
import time

# Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8080
TOTAL_CLIENTS = 25000
CONCURRENT_CLIENTS = 1000
REQUESTS_PER_CLIENT = 1

# Function to simulate a TCP client sending data to the server and receiving an echo
async def send_echo_request(client_id):
    try:
        reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)
        message = f"Hello from client {client_id}".encode()
        writer.write(message)
        await writer.drain()  # Ensure the data is sent

        # Wait for the echo response from the server
        data = await reader.read(100)  # Read up to 100 bytes of echoed data
        writer.close()
        await writer.wait_closed()

    except Exception as e:
        print(f"Client {client_id} encountered an error: {e}")

# Run the clients
async def run_clients(total_clients, concurrent_clients):
    start_time = time.time()
    tasks = []

    for i in range(total_clients):
        tasks.append(send_echo_request(i))

        # If enough tasks have been added, run the batch
        if len(tasks) >= concurrent_clients or i == total_clients - 1:
            await asyncio.gather(*tasks)  # Run the batch of tasks
            tasks = []  # Reset task list for the next batch

    end_time = time.time()

    # Calculate and display performance metrics
    total_time = end_time - start_time
    req_per_sec = total_clients / total_time
    print(f"Total time taken: {total_time:.2f} seconds")
    print(f"Requests per second: {req_per_sec:.2f}")

# Main entry point
def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_clients(TOTAL_CLIENTS, CONCURRENT_CLIENTS))

if __name__ == "__main__":
    main()

