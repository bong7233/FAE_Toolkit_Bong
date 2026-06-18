"""TCP and UDP transports for the communication tester.

All three conform to :class:`fae_toolkit.core.transport.Transport`, so the GUI
treats serial / TCP / UDP uniformly. Connections are *real*: opening fails if
the port/host is unavailable (no fabricated data), and reads return ``b""`` on
timeout, mirroring the serial transport.
"""

from __future__ import annotations

import socket
import threading
import time

from fae_toolkit.core.transport import Transport


class TcpClientTransport(Transport):
    """Outgoing TCP connection to ``host:port``."""

    def __init__(self, host: str, port: int, connect_timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self._sock: socket.socket | None = None

    def open(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        sock.setblocking(True)
        self._sock = sock

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def write(self, data: bytes) -> int:
        if self._sock is None:
            raise RuntimeError("not connected")
        self._sock.sendall(bytes(data))
        return len(data)

    def read(self, size: int, timeout: float | None = None) -> bytes:
        if self._sock is None:
            raise RuntimeError("not connected")
        import select

        ready, _, _ = select.select([self._sock], [], [], timeout)
        if not ready:
            return b""
        data = self._sock.recv(size)
        if data == b"":
            raise ConnectionError("connection closed by peer")
        return data


class TcpServerTransport(Transport):
    """Listening TCP socket that accepts one client at a time.

    Lets two instances of the tester talk over localhost (honest loopback) with
    no external hardware. Reads return ``b""`` until a client is connected.
    """

    def __init__(self, port: int, host: str = "0.0.0.0") -> None:
        self.port = port
        self.host = host
        self._srv: socket.socket | None = None
        self._conn: socket.socket | None = None
        self._peer: tuple[str, int] | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None

    def open(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(1)
        srv.settimeout(0.3)
        self._srv = srv
        self._stop.clear()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self) -> None:
        while not self._stop.is_set() and self._srv is not None:
            try:
                conn, addr = self._srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            conn.setblocking(True)
            with self._lock:
                if self._conn is not None:
                    self._conn.close()
                self._conn = conn
                self._peer = addr

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
        if self._srv is not None:
            self._srv.close()
            self._srv = None
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1.0)
            self._accept_thread = None

    @property
    def is_open(self) -> bool:
        return self._srv is not None

    @property
    def has_client(self) -> bool:
        return self._conn is not None

    def write(self, data: bytes) -> int:
        with self._lock:
            conn = self._conn
        if conn is None:
            return 0
        conn.sendall(bytes(data))
        return len(data)

    def read(self, size: int, timeout: float | None = None) -> bytes:
        import select

        with self._lock:
            conn = self._conn
        if conn is None:
            if timeout:
                time.sleep(min(timeout, 0.05))
            return b""
        ready, _, _ = select.select([conn], [], [], timeout)
        if not ready:
            return b""
        try:
            data = conn.recv(size)
        except OSError:
            data = b""
        if data == b"":  # client went away; keep listening for a new one
            with self._lock:
                if self._conn is conn:
                    self._conn.close()
                    self._conn = None
            return b""
        return data


class UdpTransport(Transport):
    """UDP socket: sends to ``remote_host:remote_port``, receives on a local port."""

    def __init__(
        self,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,
        bind_host: str = "0.0.0.0",
    ) -> None:
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port
        self.bind_host = bind_host
        self._sock: socket.socket | None = None
        self.bound_port: int | None = None
        self.last_peer: tuple[str, int] | None = None

    def open(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.bind_host, self.local_port))
        self._sock = sock
        self.bound_port = sock.getsockname()[1]

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def write(self, data: bytes) -> int:
        if self._sock is None:
            raise RuntimeError("socket not open")
        return self._sock.sendto(bytes(data), (self.remote_host, self.remote_port))

    def read(self, size: int, timeout: float | None = None) -> bytes:
        if self._sock is None:
            raise RuntimeError("socket not open")
        import select

        ready, _, _ = select.select([self._sock], [], [], timeout)
        if not ready:
            return b""
        data, addr = self._sock.recvfrom(size)
        self.last_peer = addr
        return data
