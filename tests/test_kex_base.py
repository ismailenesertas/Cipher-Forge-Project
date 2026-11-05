"""Arayüz sözleşmesi testi: sahte bir yöntemle server_start -> client_respond -> server_finish akışı."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from crypto.kex import base  # noqa: E402


@base.register
class _Dummy(base.KeyExchange):
    name = "DUMMY"

    def server_start(self):
        return b"sunucu-acik-deger"

    def client_respond(self, server_msg):
        return b"istemci-mesaji", b"\x01" * base.AES_KEY_LEN

    def server_finish(self, client_msg):
        return b"\x01" * base.AES_KEY_LEN


class KexBaseTests(unittest.TestCase):
    def test_flow_and_registry(self):
        server, client = base.create("DUMMY"), base.create("DUMMY")
        server_msg = server.server_start()
        client_msg, client_key = client.client_respond(server_msg)
        server_key = server.server_finish(client_msg)
        self.assertEqual(client_key, server_key)
        self.assertEqual(len(server_key), base.AES_KEY_LEN)

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            base.create("YOK")

    def test_abstract(self):
        with self.assertRaises(TypeError):
            base.KeyExchange()


if __name__ == "__main__":
    unittest.main()
