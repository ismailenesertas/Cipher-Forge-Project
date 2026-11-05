"""Cipher Forge ağ protokolü.

Çerçeve (frame) biçimi:

    | 4 bayt: toplam uzunluk | 2 bayt: başlık uzunluğu | başlık (JSON, UTF-8) | yük (ham bayt) |

Uzunluklar big-endian. Yük, metin ya da dosya parçasının baytlarıdır.
Güvensiz modda yük açık gider; güvenli modda AES ile şifrelenmiş olarak gidecek.
"""

import json
import struct

# Mesaj tipleri
HELLO = "HELLO"            # istemci -> sunucu: {"name": ..., "mode": "insecure"|"secure"}
ACK = "ACK"                # sunucu -> istemci: {"ref": <mesaj id>, "delivered": bool}
TEXT = "TEXT"              # metin mesajı, yük = UTF-8 metin
FILE_CHUNK = "FILE_CHUNK"  # dosya parçası: {"id", "name", "index", "total"}, yük = parça baytları
ERROR = "ERROR"            # {"reason": ...}

MODE_INSECURE = "insecure"
MODE_SECURE = "secure"

MAX_FRAME = 64 * 1024 * 1024   # tek çerçeve üst sınırı
CHUNK_SIZE = 64 * 1024         # dosya parça boyutu
DEFAULT_PORT = 5000


class ProtocolError(Exception):
    """Bozuk ya da geçersiz çerçeve."""


def encode_frame(header: dict, payload: bytes = b"") -> bytes:
    head = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(head) > 0xFFFF:
        raise ProtocolError("başlık çok büyük")
    body = struct.pack(">H", len(head)) + head + payload
    if len(body) > MAX_FRAME:
        raise ProtocolError("çerçeve çok büyük")
    return struct.pack(">I", len(body)) + body


def decode_body(body: bytes):
    if len(body) < 2:
        raise ProtocolError("çerçeve çok kısa")
    (head_len,) = struct.unpack(">H", body[:2])
    if 2 + head_len > len(body):
        raise ProtocolError("başlık uzunluğu geçersiz")
    try:
        header = json.loads(body[2:2 + head_len].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("başlık okunamadı") from exc
    if not isinstance(header, dict) or "type" not in header:
        raise ProtocolError("başlıkta 'type' yok")
    return header, body[2 + head_len:]


async def read_frame(reader):
    """Bir çerçeve okur ve (başlık, yük) döner. Bağlantı kapanırsa IncompleteReadError fırlatır."""
    raw = await reader.readexactly(4)
    (length,) = struct.unpack(">I", raw)
    if length < 2 or length > MAX_FRAME:
        raise ProtocolError("geçersiz çerçeve uzunluğu")
    body = await reader.readexactly(length)
    return decode_body(body)


async def write_frame(writer, header: dict, payload: bytes = b""):
    writer.write(encode_frame(header, payload))
    await writer.drain()
