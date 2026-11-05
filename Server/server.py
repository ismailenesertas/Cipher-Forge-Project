"""Cipher Forge sunucusu (asyncio).

İstemciler birbirine bağlanmaz; her mesaj önce buraya gelir, sunucu ekrana yazar
(dosyaysa kaydeder) ve diğer istemciye iletir. Şu an yalnızca güvensiz mod vardır.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from common import protocol as P  # noqa: E402

MAX_CLIENTS = 2


class Server:
    def __init__(self, out_dir="received", log=print):
        self.out_dir = out_dir
        self.log = log
        self.clients = {}    # ad -> writer
        self.transfers = {}  # (gönderen, aktarım id) -> {"name", "chunks": {index: bayt}, "total"}
        self._server = None

    async def start(self, host="0.0.0.0", port=P.DEFAULT_PORT):
        self._server = await asyncio.start_server(self.handle, host, port)
        return self._server

    @property
    def port(self):
        return self._server.sockets[0].getsockname()[1]

    async def close(self):
        self._server.close()
        await self._server.wait_closed()

    # ---- bağlantı yönetimi -------------------------------------------------
    async def handle(self, reader, writer):
        name = None
        try:
            name = await self._handshake(reader, writer)
            if name is None:
                return
            while True:
                header, payload = await P.read_frame(reader)
                await self._dispatch(name, header, payload, writer)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        except P.ProtocolError as exc:
            self.log(f"[!] protokol hatası ({name}): {exc}")
            await self._send_quiet(writer, {"type": P.ERROR, "reason": str(exc)})
        finally:
            if name is not None and self.clients.get(name) is writer:
                del self.clients[name]
                self.log(f"[-] {name} ayrıldı")
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    async def _handshake(self, reader, writer):
        header, _ = await P.read_frame(reader)
        name = header.get("name")
        if header["type"] != P.HELLO or not isinstance(name, str) or not name:
            await self._send_quiet(writer, {"type": P.ERROR, "reason": "ilk mesaj HELLO olmalı"})
            return None
        if header.get("mode") != P.MODE_INSECURE:
            await self._send_quiet(writer, {"type": P.ERROR, "reason": "bu sürüm yalnızca güvensiz modu destekler"})
            return None
        if name in self.clients or len(self.clients) >= MAX_CLIENTS:
            await self._send_quiet(writer, {"type": P.ERROR, "reason": "ad kullanımda ya da sunucu dolu"})
            return None
        self.clients[name] = writer
        self.log(f"[+] {name} bağlandı ({P.MODE_INSECURE} mod)")
        await P.write_frame(writer, {"type": P.ACK, "ref": "hello", "delivered": True})
        return name

    @staticmethod
    async def _send_quiet(writer, header):
        try:
            await P.write_frame(writer, header)
        except ConnectionError:
            pass

    # ---- mesaj işleme --------------------------------------------------------
    async def _dispatch(self, sender, header, payload, writer):
        kind = header["type"]
        msg_id = header.get("id")
        if kind == P.TEXT:
            self.log(f"[{sender}] {payload.decode('utf-8', errors='replace')}")
            delivered = await self._forward(sender, header, payload)
        elif kind == P.FILE_CHUNK:
            self._store_chunk(sender, header, payload)
            delivered = await self._forward(sender, header, payload)
        else:
            raise P.ProtocolError(f"bilinmeyen mesaj tipi: {kind}")
        await P.write_frame(writer, {"type": P.ACK, "ref": msg_id, "delivered": delivered})

    async def _forward(self, sender, header, payload):
        for name, peer in self.clients.items():
            if name != sender:
                out = dict(header)
                out["from"] = sender
                try:
                    await P.write_frame(peer, out, payload)
                    return True
                except ConnectionError:
                    return False
        return False

    def _store_chunk(self, sender, header, payload):
        try:
            transfer_id, index, total = header["id"], int(header["index"]), int(header["total"])
            filename = os.path.basename(str(header["name"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise P.ProtocolError("FILE_CHUNK başlığı eksik") from exc
        if not filename or total < 1 or not 0 <= index < total:
            raise P.ProtocolError("FILE_CHUNK başlığı geçersiz")
        entry = self.transfers.setdefault((sender, transfer_id), {"name": filename, "chunks": {}, "total": total})
        entry["chunks"][index] = payload
        if len(entry["chunks"]) == entry["total"]:
            del self.transfers[(sender, transfer_id)]
            os.makedirs(self.out_dir, exist_ok=True)
            path = os.path.join(self.out_dir, f"{sender}_{entry['name']}")
            with open(path, "wb") as f:
                for i in range(entry["total"]):
                    f.write(entry["chunks"][i])
            self.log(f"[{sender}] dosya kaydedildi: {path}")


async def main():
    parser = argparse.ArgumentParser(description="Cipher Forge sunucusu")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=P.DEFAULT_PORT)
    parser.add_argument("--out", default="received", help="gelen dosyaların kaydedileceği klasör")
    args = parser.parse_args()
    server = Server(out_dir=args.out)
    await server.start(args.host, args.port)
    print(f"Sunucu dinliyor: {args.host}:{server.port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
