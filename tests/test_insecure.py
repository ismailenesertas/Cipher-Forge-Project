"""Güvensiz mod uçtan uca testi: sunucu + 2 istemci, metin ve PDF."""

import asyncio
import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
for sub in ("", "Server", "Client"):
    sys.path.insert(0, os.path.join(ROOT, sub))

from client_core import Client, ClientError  # noqa: E402
from common import protocol as P  # noqa: E402
from server import Server  # noqa: E402


class ProtocolTests(unittest.TestCase):
    def test_frame_roundtrip(self):
        frame = P.encode_frame({"type": P.TEXT, "id": "1"}, b"merhaba")
        header, payload = P.decode_body(frame[4:])
        self.assertEqual(header, {"type": P.TEXT, "id": "1"})
        self.assertEqual(payload, b"merhaba")

    def test_bad_frame(self):
        with self.assertRaises(P.ProtocolError):
            P.decode_body(b"\x00")


class InsecureModeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = Server(out_dir=os.path.join(self.tmp.name, "srv"), log=lambda *_: None)
        await self.server.start("127.0.0.1", 0)
        self.texts, self.files = [], []
        out = os.path.join(self.tmp.name, "dl")
        self.a = Client("ali", out_dir=out)
        self.b = Client("veli", on_text=lambda s, t: self.texts.append((s, t)),
                        on_file=lambda s, p: self.files.append((s, p)), out_dir=out)
        await self.a.connect("127.0.0.1", self.server.port)
        await self.b.connect("127.0.0.1", self.server.port)

    async def asyncTearDown(self):
        await self.a.close()
        await self.b.close()
        await self.server.close()
        self.tmp.cleanup()

    async def test_text_is_forwarded(self):
        self.assertTrue(await self.a.send_text("selam çğış"))
        await asyncio.sleep(0.1)
        self.assertEqual(self.texts, [("ali", "selam çğış")])

    async def test_pdf_arrives_intact(self):
        data = b"%PDF-1.4\n" + os.urandom(P.CHUNK_SIZE * 2 + 123)  # birden çok parça
        path = os.path.join(self.tmp.name, "rapor.pdf")
        with open(path, "wb") as f:
            f.write(data)
        self.assertTrue(await self.a.send_file(path))
        await asyncio.sleep(0.1)
        self.assertEqual(len(self.files), 1)
        with open(self.files[0][1], "rb") as f:
            self.assertEqual(f.read(), data)
        saved = os.path.join(self.tmp.name, "srv", "ali_rapor.pdf")  # sunucu da kaydetti
        with open(saved, "rb") as f:
            self.assertEqual(f.read(), data)

    async def test_duplicate_name_rejected(self):
        extra = Client("ali")
        with self.assertRaises(ClientError):
            await extra.connect("127.0.0.1", self.server.port)

    async def test_no_peer_not_delivered(self):
        await self.b.close()
        await asyncio.sleep(0.1)
        self.assertFalse(await self.a.send_text("kimse yok"))


if __name__ == "__main__":
    unittest.main()
