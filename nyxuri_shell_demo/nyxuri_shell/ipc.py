import json
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

MAX_MESSAGE = 65536
SOCKET_TIMEOUT = 5.0
DEFAULT_SOCKET_NAME = "shell.sock"


def runtime_dir() -> Path:
    raw = os.environ.get("XDG_RUNTIME_DIR")
    if raw and Path(raw).is_dir():
        return Path(raw)
    return Path("/tmp")


def socket_path(name: str = DEFAULT_SOCKET_NAME) -> Path:
    return runtime_dir() / f"nyxuri-{os.getuid()}" / name


@dataclass
class Response:
    ok: bool
    data: Any = None
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {"ok": self.ok, "data": self.data, "error": self.error},
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, raw: str) -> "Response":
        try:
            payload = json.loads(raw)
        except ValueError:
            return cls(False, None, "malformed response")
        if not isinstance(payload, dict):
            return cls(False, None, "malformed response")
        return cls(
            bool(payload.get("ok")),
            payload.get("data"),
            str(payload.get("error") or ""),
        )


def send(command: str, args: Optional[Dict[str, Any]] = None,
         timeout: float = SOCKET_TIMEOUT, name: str = DEFAULT_SOCKET_NAME) -> Response:
    path = socket_path(name)
    if not path.exists():
        return Response(False, None, "daemon not running")
    payload = json.dumps({"command": command, "args": args or {}}, ensure_ascii=False)
    if len(payload) > MAX_MESSAGE:
        return Response(False, None, "message too large")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(str(path))
        client.sendall(payload.encode("utf-8"))
        client.shutdown(socket.SHUT_WR)
        chunks: List[bytes] = []
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(len(c) for c in chunks) > MAX_MESSAGE:
                return Response(False, None, "response too large")
        raw = b"".join(chunks).decode("utf-8", "replace")
        if not raw:
            return Response(False, None, "empty response")
        return Response.from_json(raw)
    except socket.timeout:
        return Response(False, None, "timeout")
    except OSError as exc:
        return Response(False, None, f"socket error: {exc}")
    finally:
        client.close()


def is_running(name: str = DEFAULT_SOCKET_NAME) -> bool:
    return send("ping", timeout=1.0, name=name).ok


Handler = Callable[[Dict[str, Any]], Response]


class Server:
    def __init__(self, name: str = DEFAULT_SOCKET_NAME):
        self.name = name
        self.path = socket_path(name)
        self.handlers: Dict[str, Handler] = {}
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def register(self, command: str, handler: Handler) -> None:
        self.handlers[command] = handler

    def start(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() or self.path.is_symlink():
                self.path.unlink(missing_ok=True)
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.bind(str(self.path))
            os.chmod(self.path, 0o600)
            self._sock.listen(8)
            self._sock.settimeout(0.5)
        except OSError:
            return False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return True

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(SOCKET_TIMEOUT)
            chunks: List[bytes] = []
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(len(c) for c in chunks) > MAX_MESSAGE:
                    conn.sendall(Response(False, None, "message too large").to_json().encode())
                    return
            raw = b"".join(chunks).decode("utf-8", "replace")
            if not raw:
                return
            try:
                payload = json.loads(raw)
            except ValueError:
                conn.sendall(Response(False, None, "malformed request").to_json().encode())
                return
            command = str(payload.get("command") or "")
            args = payload.get("args")
            if not isinstance(args, dict):
                args = {}
            response = self.dispatch(command, args)
            conn.sendall(response.to_json().encode("utf-8"))
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def dispatch(self, command: str, args: Dict[str, Any]) -> Response:
        if command == "ping":
            return Response(True, {"pong": True, "pid": os.getpid()})
        handler = self.handlers.get(command)
        if handler is None:
            return Response(False, None, f"unknown command: {command}")
        try:
            return handler(args)
        except Exception as exc:
            return Response(False, None, f"{type(exc).__name__}: {exc}")

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass


def _self_check() -> List[str]:
    problems: List[str] = []
    name = f"test-{os.getpid()}.sock"
    server = Server(name)
    if not server.start():
        return ["server failed to start"]

    server.register("echo", lambda a: Response(True, a))
    server.register("boom", lambda a: (_ for _ in ()).throw(RuntimeError("kaboom")))

    try:
        pong = send("ping", name=name)
        if not pong.ok or not pong.data.get("pong"):
            problems.append("ping failed")

        echo = send("echo", {"value": 42, "text": "hi"}, name=name)
        if not echo.ok or echo.data.get("value") != 42:
            problems.append("echo failed")

        unknown = send("nope", name=name)
        if unknown.ok or "unknown" not in unknown.error:
            problems.append("unknown command not rejected")

        boom = send("boom", name=name)
        if boom.ok or "kaboom" not in boom.error:
            problems.append("exception not contained")

        big = send("echo", {"blob": "x" * (MAX_MESSAGE + 10)}, name=name)
        if big.ok:
            problems.append("oversized message not rejected")
    finally:
        server.stop()

    if server.path.exists():
        problems.append("socket not cleaned up")

    dead = send("ping", name=name)
    if dead.ok:
        problems.append("stale socket reported alive")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print("ok")
