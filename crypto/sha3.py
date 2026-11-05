"""Keccak-f[1600], SHA3 ve SHAKE (FIPS 202) – sıfırdan yazılmıştır.

Kullanılan fikir "sünger" (sponge) yapısıdır:
  1. Emme (absorb): girdi rate boyutunda bloklara bölünür, duruma XOR'lanır,
     her blokta Keccak-f[1600] permütasyonu çalışır.
  2. Sıkma (squeeze): durumun ilk rate baytı çıktı olarak okunur; daha fazla
     çıktı gerekirse permütasyon tekrar çalıştırılır.

Durum 5x5'lik 25 "şeritten" (lane) oluşur; her şerit 64 bittir. Şerit (x, y)
dizide x + 5*y indisindedir. Baytlar şeritlere little-endian sırayla yerleşir.
"""

MASK64 = (1 << 64) - 1
ROUNDS = 24


def _make_round_constants():
    """Iota adımının 24 sabiti; FIPS 202'deki LFSR (x^8 + x^6 + x^5 + x^4 + 1) ile üretilir."""
    def lfsr_bit(t):
        if t % 255 == 0:
            return 1
        r = 1
        for _ in range(t % 255):
            r <<= 1
            if r & 0x100:
                r ^= 0x171
        return r & 1

    constants = []
    for ir in range(ROUNDS):
        rc = 0
        for j in range(7):
            if lfsr_bit(j + 7 * ir):
                rc |= 1 << ((1 << j) - 1)
        constants.append(rc)
    return constants


def _make_rotation_offsets():
    """Rho adımının dönme miktarları; (x, y) = (1, 0) noktasından başlayan yörüngeden bulunur."""
    offsets = [[0] * 5 for _ in range(5)]
    x, y = 1, 0
    for t in range(ROUNDS):
        offsets[x][y] = ((t + 1) * (t + 2) // 2) % 64
        x, y = y, (2 * x + 3 * y) % 5
    return offsets


RC = _make_round_constants()
ROT = _make_rotation_offsets()


def _rol(value, shift):
    shift %= 64
    if shift == 0:
        return value
    return ((value << shift) | (value >> (64 - shift))) & MASK64


def keccak_f1600(state):
    """25 şeritlik (64 bit) durumu yerinde değiştirerek 24 turluk permütasyonu uygular."""
    for rnd in range(ROUNDS):
        # theta: her sütunun eşliğini komşu sütunlara dağıt
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]

        # rho ve pi: şeritleri döndür ve yerlerini değiştir
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(state[x + 5 * y], ROT[x][y])

        # chi: satır içinde doğrusal olmayan karıştırma
        for y in range(5):
            row = b[5 * y:5 * y + 5]
            for x in range(5):
                state[x + 5 * y] = row[x] ^ ((~row[(x + 1) % 5] & MASK64) & row[(x + 2) % 5])

        # iota: tura özel sabiti ekle
        state[0] ^= RC[rnd]


class _Sponge:
    """Artımlı (update/squeeze) sünger. SHA3 ve SHAKE bunun üstüne kuruludur."""

    def __init__(self, rate, suffix):
        self.rate = rate          # bayt cinsinden blok boyutu
        self.suffix = suffix      # alan ayırıcı: SHA3 için 0x06, SHAKE için 0x1F
        self.state = [0] * 25
        self.buf = bytearray()
        self.squeezing = False
        self.block = b""
        self.pos = 0

    def _absorb_block(self, block):
        for i in range(self.rate // 8):
            self.state[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        keccak_f1600(self.state)

    def _load_block(self):
        self.block = b"".join(lane.to_bytes(8, "little") for lane in self.state[:self.rate // 8])
        self.pos = 0

    def update(self, data):
        if self.squeezing:
            raise ValueError("çıktı okunmaya başlandıktan sonra veri eklenemez")
        self.buf += data
        while len(self.buf) >= self.rate:
            self._absorb_block(bytes(self.buf[:self.rate]))
            del self.buf[:self.rate]
        return self

    def _finalize(self):
        # pad10*1: alan ayırıcı baytı, sıfırlar, son baytın en üst biti
        pad = bytearray(self.buf)
        pad.append(self.suffix)
        pad.extend(b"\x00" * (self.rate - len(pad)))
        pad[-1] |= 0x80
        self._absorb_block(bytes(pad))
        self.buf = bytearray()
        self.squeezing = True
        self._load_block()

    def squeeze(self, n):
        if not self.squeezing:
            self._finalize()
        out = bytearray()
        while len(out) < n:
            if self.pos == self.rate:
                keccak_f1600(self.state)
                self._load_block()
            take = min(self.rate - self.pos, n - len(out))
            out += self.block[self.pos:self.pos + take]
            self.pos += take
        return bytes(out)


class Shake128(_Sponge):
    """SHAKE128: update() ile veri ekle, squeeze(n) ile istediğin kadar çıktı al."""
    def __init__(self, data=b""):
        super().__init__(rate=168, suffix=0x1F)
        self.update(data)


class Shake256(_Sponge):
    def __init__(self, data=b""):
        super().__init__(rate=136, suffix=0x1F)
        self.update(data)


class Sha3_256(_Sponge):
    def __init__(self, data=b""):
        super().__init__(rate=136, suffix=0x06)
        self.update(data)

    def digest(self):
        return self._digest(32)

    def _digest(self, n):
        # digest() birden çok kez çağrılabilsin diye süngerin kopyası üzerinde çalış
        copy = _Sponge(self.rate, self.suffix)
        copy.state, copy.buf = list(self.state), bytearray(self.buf)
        return copy.squeeze(n)


class Sha3_512(Sha3_256):
    def __init__(self, data=b""):
        _Sponge.__init__(self, rate=72, suffix=0x06)
        self.update(data)

    def digest(self):
        return self._digest(64)


def sha3_256(data):
    return Sha3_256(data).digest()


def sha3_512(data):
    return Sha3_512(data).digest()


def shake128(data, length):
    return Shake128(data).squeeze(length)


def shake256(data, length):
    return Shake256(data).squeeze(length)
