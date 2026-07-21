import json
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, QStandardPaths, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


SERVER_NAME = "MediaCraft.SingleInstance.v1"
LOCK_FILE_NAME = "MediaCraft.SingleInstance.lock"


def command_line_paths(arguments: list[str]) -> list[str]:
    """Return existing file paths passed by the shell or command line."""
    paths: list[str] = []
    for value in arguments:
        path = Path(value).expanduser()
        if path.is_file():
            paths.append(str(path.resolve()))
    return paths


class SingleInstance(QObject):
    paths_received = Signal(list)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        server_name: str = SERVER_NAME,
        lock_path: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name
        if lock_path is None:
            temp_directory = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.TempLocation
            )
            lock_path = str(Path(temp_directory) / LOCK_FILE_NAME)
        self._lock = QLockFile(lock_path)
        self._server = QLocalServer(self)
        self._server.setSocketOptions(
            QLocalServer.SocketOption.UserAccessOption
        )
        self._server.newConnection.connect(self._accept_connections)
        self._buffers: dict[QLocalSocket, bytearray] = {}

    def acquire_or_notify(self, paths: list[str]) -> bool:
        """Become the primary instance, or notify it and return False."""
        if self._lock.tryLock(0):
            QLocalServer.removeServer(self._server_name)
            if self._server.listen(self._server_name):
                return True
            self._lock.unlock()
            return False

        socket = QLocalSocket()
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(1000):
            return False
        payload = json.dumps(
            {"paths": paths}, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        socket.write(payload)
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            socket.waitForDisconnected(1000)
        return False

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
            QLocalServer.removeServer(self._server_name)
        if self._lock.isLocked():
            self._lock.unlock()

    def _accept_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            self._buffers[socket] = bytearray()
            socket.readyRead.connect(lambda current=socket: self._read(current))
            socket.disconnected.connect(
                lambda current=socket: self._discard(current)
            )
            self._read(socket)

    def _read(self, socket: QLocalSocket) -> None:
        buffer = self._buffers.get(socket)
        if buffer is None:
            return
        buffer.extend(bytes(socket.readAll()))
        while b"\n" in buffer:
            raw_message, _, remainder = buffer.partition(b"\n")
            buffer[:] = remainder
            try:
                message = json.loads(raw_message.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            values = message.get("paths") if isinstance(message, dict) else None
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                continue
            self.paths_received.emit(values)

    def _discard(self, socket: QLocalSocket) -> None:
        self._buffers.pop(socket, None)
        socket.deleteLater()
