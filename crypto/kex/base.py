"""Anahtar dağıtım yöntemlerinin ortak arayüzü.

RSA-2048, DH-2048, ECDH (P-256) ve ML-KEM-768 aynı üç adımlı akışa uyar:

    SUNUCU                                   İSTEMCİ
    server_start()          -- sunucu mesajı -->
                            <-- istemci mesajı --   client_respond(sunucu_mesajı)
    server_finish(istemci_mesajı)                   (her iki taraf aynı AES anahtarına sahip)

Her yöntem bu akışta farklı baytlar taşır:

    Yöntem   sunucu mesajı        istemci mesajı
    -------  -------------------  ---------------------------------------------
    RSA      açık anahtar (n, e)  AES anahtarının RSA-OAEP ile şifrelenmiş hali
    DH       sunucu açık değeri   istemci açık değeri (ortak sır HKDF'ten geçer)
    ECDH     sunucu açık noktası  istemci açık noktası (ortak sır HKDF'ten geçer)
    Kyber    kapsülleme anahtarı  şifreli metin (ciphertext)

Ölçüm tablosu için:
    anahtar üretme süresi  -> server_start() süresi
    anahtar değişim süresi -> client_respond() + server_finish() süresi
    paket boyutu           -> len(sunucu mesajı) + len(istemci mesajı)
"""

from abc import ABC, abstractmethod

AES_KEY_LEN = 16  # AES-128 anahtarı, bayt


class KeyExchange(ABC):
    """Bir bağlantı için tek kullanımlık nesne: her yeni istemci için yenisi oluşturulur."""

    name = ""  # protokolde ve arayüzde görünen ad: "RSA", "DH", "ECC", "KYBER"

    @abstractmethod
    def server_start(self) -> bytes:
        """Sunucu tarafı: anahtar çiftini üretir, istemciye gidecek ilk mesajı döner."""

    @abstractmethod
    def client_respond(self, server_msg: bytes) -> tuple[bytes, bytes]:
        """İstemci tarafı: (sunucuya gidecek mesaj, AES_KEY_LEN baytlık AES anahtarı) döner."""

    @abstractmethod
    def server_finish(self, client_msg: bytes) -> bytes:
        """Sunucu tarafı: istemci mesajından AES_KEY_LEN baytlık AES anahtarını çıkarır."""


# Yöntem adı -> sınıf. Her yöntem dosyası kendini buraya kaydeder (@register).
REGISTRY: dict[str, type] = {}


def register(cls):
    REGISTRY[cls.name] = cls
    return cls


def create(name: str) -> KeyExchange:
    """Arayüzde seçilen ada göre yeni bir yöntem nesnesi üretir."""
    try:
        return REGISTRY[name]()
    except KeyError:
        raise ValueError(f"bilinmeyen anahtar yöntemi: {name}") from None
