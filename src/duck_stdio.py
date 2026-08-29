"""
duck_stdio.py — Python wrapper for the duck-stdio universal I/O library.
Provides file, memory, SQLite, and generic stream I/O with thread-safe operations.
Since the C library may not compile on Windows without gcc, this is a pure-Python
reimplementation of the duck-stdio API using ctypes-compatible semantics.
"""
import os
import io
import sqlite3
import threading
import time
from enum import IntEnum
from typing import Optional, Any

# ─── Stream types ───
class StreamType(IntEnum):
    DUCK_FILE = 0
    DUCK_MEMORY = 1
    DUCK_SQLITE = 2
    DUCK_PIPE = 3
    DUCK_SOCKET = 4

# ─── Flags ───
class Flags(IntEnum):
    DUCK_READ = 0x01
    DUCK_WRITE = 0x02
    DUCK_APPEND = 0x04
    DUCK_BINARY = 0x08
    DUCK_NONBLOCK = 0x10
    DUCK_COMPRESSED = 0x20
    DUCK_ENCRYPTED = 0x40
    DUCK_BUFFERED = 0x80

class DuckStream:
    """Universal I/O stream — mirrors the C duck_stream_t struct."""

    def __init__(self, stream_type: StreamType = StreamType.DUCK_FILE):
        self.type = stream_type
        self.flags = Flags.DUCK_BUFFERED
        self.fd: Optional[int] = -1
        self._file: Optional[io.FileIO] = None
        self._membuf: Optional[bytearray] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._table: Optional[str] = None
        self._key_col: Optional[str] = None
        self._data_col: Optional[str] = None
        self._offset: int = 0
        self._buf: bytearray = bytearray(8192)
        self._bufpos: int = 0
        self._buflen: int = 0
        self.error: int = 0
        self.errmsg: str = ""
        self._lock = threading.Lock()
        self.created: float = time.time()
        self.bytes_read: int = 0
        self.bytes_written: int = 0
        self._closed: bool = False

    # ─── Core I/O ───
    def fread(self, size: int, nmemb: int) -> bytes:
        if self._closed:
            raise IOError("Stream closed")
        if not (self.flags & Flags.DUCK_READ):
            self.error = 9  # EBADF
            return b""
        with self._lock:
            total = size * nmemb
            data = bytearray()
            if self._membuf is not None:
                remaining = len(self._membuf) - self._offset
                to_read = min(total, remaining)
                if to_read > 0:
                    data = self._membuf[self._offset:self._offset + to_read]
                    self._offset += to_read
                    self.bytes_read += to_read
            elif self._file is not None:
                data = self._file.read(total)
                self._offset += len(data)
                self.bytes_read += len(data)
            elif self._conn is not None:
                # SQLite read
                cursor = self._conn.execute(
                    f"SELECT {self._data_col} FROM {self._table} WHERE {self._key_col} > ? LIMIT 1",
                    (self._offset,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    data = row[0][:total]
                    self._offset += len(data)
                    self.bytes_read += len(data)
            return bytes(data)

    def fwrite(self, data: bytes) -> int:
        if self._closed:
            raise IOError("Stream closed")
        if not (self.flags & (Flags.DUCK_WRITE | Flags.DUCK_APPEND)):
            self.error = 9
            return 0
        with self._lock:
            if self._membuf is not None:
                self._membuf.extend(data)
                self._offset += len(data)
                self.bytes_written += len(data)
            elif self._file is not None:
                self._file.write(data)
                self._offset += len(data)
                self.bytes_written += len(data)
            elif self._conn is not None:
                # SQLite write
                self._conn.execute(
                    f"INSERT OR REPLACE INTO {self._table} ({self._key_col}, {self._data_col}) VALUES (?, ?)",
                    (self._offset, data)
                )
                self._conn.commit()
                self._offset += len(data)
                self.bytes_written += len(data)
            return len(data)

    def fseek(self, offset: int, whence: int = 0) -> int:
        with self._lock:
            if whence == 0:  # SEEK_SET
                self._offset = offset
            elif whence == 1:  # SEEK_CUR
                self._offset += offset
            elif whence == 2:  # SEEK_END
                if self._membuf is not None:
                    self._offset = len(self._membuf) + offset
                elif self._file is not None:
                    self._file.seek(0, 2)
                    self._offset = self._file.tell()
                    self._file.seek(self._offset)
            return self._offset

    def ftell(self) -> int:
        return self._offset

    def fflush(self) -> int:
        if self._file is not None:
            self._file.flush()
        if self._conn is not None:
            self._conn.commit()
        return 0

    def feof(self) -> bool:
        if self._membuf is not None:
            return self._offset >= len(self._membuf)
        if self._file is not None:
            pos = self._file.tell()
            self._file.seek(0, 2)
            end = self._file.tell()
            self._file.seek(pos)
            return pos >= end
        return True

    def ferror(self) -> int:
        return self.error

    def clearerr(self):
        self.error = 0
        self.errmsg = ""

    def fileno(self) -> int:
        return self.fd if self.fd >= 0 else -1

    def close(self):
        if self._closed:
            return
        self._closed = True
        with self._lock:
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._membuf = None

    # ─── Convenience ───
    def write_text(self, text: str) -> int:
        return self.fwrite(text.encode('utf-8'))

    def read_text(self, size: int = 65536) -> str:
        data = self.fread(1, size)
        return data.decode('utf-8', errors='replace')

    def write_line(self, text: str) -> int:
        return self.fwrite((text + '\n').encode('utf-8'))

    def read_lines(self) -> list:
        lines = []
        while not self.feof():
            data = self.fread(1, 4096)
            if not data:
                break
            text = data.decode('utf-8', errors='replace')
            lines.extend(text.splitlines())
        return lines


# ─── Factory functions (mirror C API) ───

def duck_fopen(path: str, mode: str = "r") -> DuckStream:
    s = DuckStream(StreamType.DUCK_FILE)
    if 'r' in mode:
        s.flags = Flags.DUCK_READ | Flags.DUCK_BUFFERED
    elif 'w' in mode:
        s.flags = Flags.DUCK_WRITE | Flags.DUCK_BUFFERED
    elif 'a' in mode:
        s.flags = Flags.DUCK_APPEND | Flags.DUCK_WRITE | Flags.DUCK_BUFFERED
    if 'b' in mode:
        s.flags |= Flags.DUCK_BINARY
    if '+' in mode:
        s.flags |= Flags.DUCK_READ | Flags.DUCK_WRITE
    # Always use binary mode internally — fwrite sends bytes
    py_mode = mode.replace('DUCK_', '')
    if 'b' not in py_mode:
        py_mode += 'b'
    s._file = open(path, py_mode)
    s.fd = s._file.fileno() if hasattr(s._file, 'fileno') else -1
    return s

def duck_fmemopen(size: int = 4096, data: bytes = None) -> DuckStream:
    s = DuckStream(StreamType.DUCK_MEMORY)
    s.flags = Flags.DUCK_READ | Flags.DUCK_WRITE | Flags.DUCK_BUFFERED
    if data:
        s._membuf = bytearray(data)
    else:
        s._membuf = bytearray(size)
    return s

def duck_fdb_open(db_path: str, table: str = "duck_data") -> DuckStream:
    s = DuckStream(StreamType.DUCK_SQLITE)
    s.flags = Flags.DUCK_READ | Flags.DUCK_WRITE | Flags.DUCK_BUFFERED
    s._conn = sqlite3.connect(db_path)
    s._table = table
    s._key_col = "id"
    s._data_col = "data"
    s._conn.execute(
        f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY, data BLOB)"
    )
    s._conn.commit()
    return s

def duck_stdin() -> DuckStream:
    s = DuckStream(StreamType.DUCK_PIPE)
    s._file = sys_stdin if (sys_stdin := __import__('sys').stdin) else None
    s.flags = Flags.DUCK_READ
    return s

def duck_stdout() -> DuckStream:
    s = DuckStream(StreamType.DUCK_PIPE)
    s._file = __import__('sys').stdout
    s.flags = Flags.DUCK_WRITE
    return s

def duck_stderr() -> DuckStream:
    s = DuckStream(StreamType.DUCK_PIPE)
    s._file = __import__('sys').stderr
    s.flags = Flags.DUCK_WRITE
    return s

def duck_fclose(s: DuckStream):
    if s:
        s.close()
