"""Komut satırı istemcisi (güvensiz mod).

Kullanım:
    python client.py --host 192.168.1.20 --name ali
Yazdığın satır metin olarak gider; PDF göndermek için:  /file yol/dosya.pdf
Çıkış: /quit
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client_core import Client, ClientError  # noqa: E402
from common import protocol as P  # noqa: E402


async def main():
    parser = argparse.ArgumentParser(description="Cipher Forge istemcisi")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=P.DEFAULT_PORT)
    parser.add_argument("--name", required=True, help="istemci adı (iki istemcide farklı olmalı)")
    parser.add_argument("--out", default="downloads", help="gelen dosyaların klasörü")
    args = parser.parse_args()

    client = Client(
        args.name,
        on_text=lambda sender, text: print(f"\n[{sender}] {text}"),
        on_file=lambda sender, path: print(f"\n[{sender}] dosya alındı: {path}"),
        out_dir=args.out,
    )
    try:
        await client.connect(args.host, args.port)
    except (ClientError, OSError) as exc:
        print(f"Bağlanılamadı: {exc}")
        return
    print("Bağlandı (güvensiz mod). Metin yaz, /file <yol> ile PDF gönder, /quit ile çık.")

    loop = asyncio.get_running_loop()
    while True:
        line = (await loop.run_in_executor(None, sys.stdin.readline)).strip()
        if not line or line == "/quit":
            break
        try:
            if line.startswith("/file "):
                ok = await client.send_file(line[6:].strip())
            else:
                ok = await client.send_text(line)
            print("iletildi" if ok else "sunucuya ulaştı, karşı istemci bağlı değil")
        except (ClientError, OSError, asyncio.TimeoutError) as exc:
            print(f"Hata: {exc}")
    await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
