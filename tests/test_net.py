"""Tests for the TCP/UDP transports over localhost (no external hardware)."""

import time

from fae_toolkit.core.net import TcpClientTransport, TcpServerTransport, UdpTransport
from fae_toolkit.core.transport import read_exact


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_tcp_client_server_roundtrip():
    port = _free_port()
    server = TcpServerTransport(port, host="127.0.0.1")
    server.open()
    client = TcpClientTransport("127.0.0.1", port)
    # wait for the server's accept thread to register the connection
    for _ in range(50):
        client_open = False
        try:
            client.open()
            client_open = True
            break
        except OSError:
            time.sleep(0.05)
    assert client_open
    for _ in range(50):
        if server.has_client:
            break
        time.sleep(0.02)
    assert server.has_client

    try:
        client.write(b"hello")
        assert read_exact(server, 5, timeout=1.0) == b"hello"
        server.write(b"world!")
        assert read_exact(client, 6, timeout=1.0) == b"world!"
    finally:
        client.close()
        server.close()


def test_udp_roundtrip():
    a = UdpTransport("127.0.0.1", 0, local_port=0)
    a.open()
    b = UdpTransport("127.0.0.1", a.bound_port, local_port=0)
    b.open()
    # point a back at b's bound port
    a.remote_port = b.bound_port
    try:
        b.write(b"\x01\x02\x03")
        assert read_exact(a, 3, timeout=1.0) == b"\x01\x02\x03"
    finally:
        a.close()
        b.close()
