import asyncio
import contextlib
import os


LISTEN_HOST = os.environ.get("HELIX_STABLE_PROXY_BIND_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("HELIX_STABLE_PROXY_BIND_PORT", "8899"))


async def pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        with contextlib.suppress(Exception):
            writer.close()
            await writer.wait_closed()


async def respond_healthcheck(writer: asyncio.StreamWriter) -> None:
    writer.write(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\n"
        b"ok"
    )
    await writer.drain()


async def reject_request(writer: asyncio.StreamWriter, status: bytes, body: bytes) -> None:
    writer.write(
        b"HTTP/1.1 "
        + status
        + b"\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: "
        + str(len(body)).encode("ascii")
        + b"\r\nConnection: close\r\n\r\n"
        + body
    )
    await writer.drain()


async def handle_client(
    client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
) -> None:
    upstream_writer = None
    try:
        request_line = await client_reader.readline()
        if not request_line:
            return

        while True:
            header_line = await client_reader.readline()
            if not header_line or header_line in (b"\r\n", b"\n"):
                break

        parts = request_line.decode("utf-8", "replace").strip().split()
        if len(parts) < 3:
            await reject_request(client_writer, b"400 Bad Request", b"Malformed request")
            return

        method, target, _http_version = parts[0], parts[1], parts[2]
        if method == "GET" and target == "/healthz":
            await respond_healthcheck(client_writer)
            return

        if method != "CONNECT":
            await reject_request(
                client_writer,
                b"405 Method Not Allowed",
                b"Only CONNECT and GET /healthz are supported",
            )
            return

        if ":" not in target:
            await reject_request(client_writer, b"400 Bad Request", b"CONNECT target missing port")
            return

        host, port_text = target.rsplit(":", 1)
        try:
            port = int(port_text)
        except ValueError:
            await reject_request(client_writer, b"400 Bad Request", b"Invalid CONNECT target port")
            return

        upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
        client_writer.write(
            b"HTTP/1.1 200 Connection Established\r\n"
            b"Proxy-Agent: HelixStableProxy/1.0\r\n\r\n"
        )
        await client_writer.drain()

        await asyncio.gather(
            pipe_stream(client_reader, upstream_writer),
            pipe_stream(upstream_reader, client_writer),
        )
    except Exception:
        with contextlib.suppress(Exception):
            await reject_request(client_writer, b"502 Bad Gateway", b"Proxy upstream failure")
    finally:
        if upstream_writer is not None:
            with contextlib.suppress(Exception):
                upstream_writer.close()
                await upstream_writer.wait_closed()
        with contextlib.suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
