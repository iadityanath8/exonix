import asyncio

async def handle_echo(reader, writer):
    addr = writer.get_extra_info('peername')

    while True:
        data = await reader.read(100)
        if not data:
            break

        message = data.decode()
        #print(f"Received {message} from {addr}")

        writer.write(data)
        await writer.drain()

    #print(f"Closing connection to {addr}")
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_echo, '127.0.0.1', 8080)

    addr = server.sockets[0].getsockname()
   # print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())

