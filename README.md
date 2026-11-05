# Cipher Forge – Güvenli Haberleşme Projesi (RSA, DH, ECC, Kyber)

Karadeniz Teknik Üniversitesi, Yazılım Mühendisliği, Kriptoloji dersi dönem projesi. Sistem bir sunucu ve iki istemciden oluşur. İstemciler birbirine doğrudan bağlanmaz; metin ve PDF önce sunucuya gider, sunucu diğer istemciye iletir.

- **Güvensiz mod:** Veri şifresiz gider, Wireshark'ta okunur.
- **Güvenli mod:** Veri AES-128 ile şifrelenir. Sunucu çözer, ekrana yazar (dosyaysa kaydeder) ve diğer istemciye onun anahtarıyla yeniden şifreleyip iletir.
- **Anahtar dağıtımı:** RSA-2048, Diffie-Hellman-2048, ECDH (P-256) ve Kyber (ML-KEM-768) yalnızca AES anahtarını karşı tarafa güvenle ulaştırır; veriyi şifrelemez.

Kripto algoritmaları (AES, SHA-2/SHA-3, HMAC, HKDF, RSA, DH, ECC, Kyber) sıfırdan yazılmıştır. Hazır kripto kütüphanesi yalnızca `Manual_AES` karşılaştırma betiğinde kullanılır.

## Grup Üyeleri

| Üye | Sorumluluk |
| --- | --- |
| İsmail Enes Ertaş (Master) | Sunucu, protokol, entegrasyon, Keccak/SHA3, Kyber ML-KEM-768, Wireshark |
| Nehir Buket Polat | tkinter arayüz, büyük sayı aritmetiği, Miller-Rabin, RSA-2048, DH-2048 |
| Reyyan Gezici | Manuel AES, CBC + PKCS7, SHA-256 / HMAC / HKDF, ECC P-256, benchmark |

## Teknolojiler

- **Dil:** Python 3.10+ (sunucu ve istemci)
- **Arayüz:** tkinter
- **Ağ:** socket, asyncio (standart kütüphane)
- **Ağ analizi:** Wireshark

## Kurulum ve Çalıştırma

### Gereksinimler

- Sistem en az 2 farklı bilgisayarda çalıştırılır (ör. A'da sunucu, B'de istemciler).
- Python 3.10 veya üzeri. Aynı Wi-Fi ağı kullanılmalı, sunucu bilgisayarda güvenlik duvarında **5000** portu açılmalıdır.

```bash
git clone https://github.com/ismailenesertas/Cipher-Forge-Project.git
cd Cipher-Forge-Project
```

### 1. Sunucu (Bilgisayar A)

```bash
cd Server
python server.py --host 0.0.0.0 --port 5000
```

Sunucunun IP adresini not alın (`ipconfig` / `ip a`).

### 2. İstemciler (Bilgisayar B ve C)

```bash
cd Client
python client.py
```

Arayüzde sunucu IP ve portunu girin, modu (güvensiz / güvenli) ve güvenli modda anahtar yöntemini (RSA, DH, ECC, Kyber) seçip bağlanın. Metin kutusundan mesaj yazabilir ya da klasörden PDF seçip gönderebilirsiniz.

### Testler

```bash
python -m unittest discover -s tests
```

Her algoritma resmi test vektörleriyle (FIPS-197, FIPS 202, RFC, NIST) doğrulanır.

## Klasör Yapısı

> Klasör adları geliştikçe güncellenir.

```
Server/      Asyncio sunucu: çöz, yaz, yeniden şifrele, ilet
Client/      İstemci çekirdeği ve tkinter arayüzü
crypto/      Sıfırdan yazılmış algoritmalar (kex/base.py arayüzü)
Manual_AES/  Manuel AES ve kütüphaneli karşılaştırma betiği
tests/       Test vektörleri ve birim testleri
captures/    Wireshark .pcapng kayıtları (güvensiz, güvenli)
```

## Manuel AES Modülü

AES-128 kütüphanesiz kodlanır (S-box, SubBytes, ShiftRows, MixColumns, key expansion, CBC + PKCS7). Aynı girdi için kütüphaneli çıktıyla karşılaştırılır; farkların nedenleri (dolgu, çalışma modu, IV) raporda açıklanır. Betik `Manual_AES` klasöründedir.

## Çalışma Kuralları

- Her üye kendi GitHub hesabıyla, küçük ve sık commit'ler atar; kendi dalında çalışır (`aes`, `rsa-dh`, `kyber`), testler geçince `main`'e birleştirilir.
- Commit biçimi: `feat(aes): ShiftRows ekle`, `test(rsa): Miller-Rabin testleri`, `fix(server): ...`, `docs: ...`
- Ortak yazılan işte commit sonuna `Co-authored-by: Ad Soyad <eposta>` eklenir.
- Test geçmeden birleştirme yok.
