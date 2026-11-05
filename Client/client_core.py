"""İstemci çekirdeği: arayüzden bağımsız, hem CLI hem tkinter tarafından kullanılır."""

import asyncio
import math
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common import protocol as P  # noqa: E402


class ClientError(Exception):
    pass


class Client:
    def __init__(self, name, on_text=None, on_file=None, out_dir="downloads"):
        self.name = name
        self.on_text = on_text or (lambda sender, text: None)
        self.on_file = on_file or (lambda sender, path: None)
        self.out_dir = out_dir
        self.mode = P.MODE_INSECURE
        self._reader = None
        self._writer = None
        self._acks = {}
        self._incoming = {}
        self._task = None

    async def connect(self, host, port=P.DEFAULT_PORT, mode=P.MODE_INSECURE):
        self.mode = mode
        self._reader, self._writer = await asyncio.open_connection(host, port)
        await P.write_frame(self._writer, {"type": P.HELLO, "name": self.name, "mode": mode})
        header, _ = await P.read_frame(self._reader)
        if header["type"] == P.ERROR:
            await self.close()
            raise ClientError(header.get("reason", "bağlantı reddedildi"))
        self._task = asyncio.create_task(self._listen())

    async def close(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    async def send_text(self, text, timeout=10):
        msg_id = uuid.uuid4().hex
        return await self._send({"type": P.TEXT, "id": msg_id}, text.encode("utf-8"), msg_id, timeout)

    async def send_file(self, path, timeout=30):
        name = os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
        transfer_id = uuid.uuid4().hex
        total = max(1, math.ceil(len(data) / P.CHUNK_SIZE))
        delivered = True
        for i in range(total):
            chunk = data[i * P.CHUNK_SIZE:(i + 1) * P.CHUNK_SIZE]
            header = {"type": P.FILE_CHUNK, "id": transfer_id, "name": name, "index": i, "total": total}
            delivered = await self._send(header, chunk, transfer_id, timeout)
        return delivered

    async def _send(self, header, payload, ack_key, timeout):
        fut = asyncio.get_running_loop().create_future()
        self._acks[ack_key] = fut
        await P.write_frame(self._writer, header, payload)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._acks.pop(ack_key, None)

    async def _listen(self):
        try:
            while True:
                header, payload = await P.read_frame(self._reader)
                kind = header["type"]
                if kind == P.ACK:
                    fut = self._acks.get(header.get("ref"))
                    if fut and not fut.done():
                        fut.set_result(bool(header.get("delivered")))
                elif kind == P.TEXT:
                    self.on_text(header.get("from"), payload.decode("utf-8", errors="replace"))
                elif kind == P.FILE_CHUNK:
                    self._receive_chunk(header, payload)
                elif kind == P.ERROR:
                    raise ClientError(header.get("reason", "sunucu hatası"))
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
            pass
        finally:
            for fut in self._acks.values():
                if not fut.done():
                    fut.set_exception(ClientError("bağlantı koptu"))

    def _receive_chunk(self, header, payload):
        key = (header["from"], header["id"])
        entry = self._incoming.setdefault(key, {"name": os.path.basename(header["name"]), "chunks": {}})
        entry["chunks"][header["index"]] = payload
        if len(entry["chunks"]) == header["total"]:
            del self._incoming[key]
            os.makedirs(self.out_dir, exist_ok=True)
            path = os.path.join(self.out_dir, f"{header['from']}_{entry['name']}")
            with open(path, "wb") as f:
                for i in range(header["total"]):
                    f.write(entry["chunks"][i])
            self.on_file(header["from"], path)
