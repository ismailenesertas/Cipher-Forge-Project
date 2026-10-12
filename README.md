# Cipher-Forge-Project
# Güvenli Haberleşme Projesi (RSA, DH, ECC, Kyber)

Bu proje, Karadeniz Teknik Üniversitesi Kriptoloji dersi kapsamında geliştirilmiş bir güvenli haberleşme sistemidir. Sistem bir merkezi sunucu ve iki istemciden oluşmaktadır. İstemciler arası veri (metin ve PDF) transferi AES-128 ile şifrelenmekte, AES anahtarının güvenli dağıtımı ise RSA, Diffie-Hellman, ECC veya Kyber algoritmaları ile sağlanmaktadır.

## 👥 Grup Üyeleri
*   **İsmail Enes Ertaş**(Master)
*   **Nehir Buket Polat**
*   **Reyyan Gezici** 

## 🛠️ Kullanılan Teknolojiler ve Platformlar
*   **İstemci (Client):**
*   **Sunucu (Server):** Python 
*   **Ağ Analizi:** Wireshark

## 🚀 Kurulum ve Çalıştırma Adımları

### Sistem Gereksinimleri
*   Sistem en az 2 farklı bilgisayarda veya sanal makine ağında çalıştırılmalıdır.
*   Python 3.x ve .NET SDK yüklü olmalıdır.

### 1. Sunucuyu Çalıştırma (Bilgisayar A)
1. `Server` klasörüne gidin.
2. Gerekli kütüphaneleri kurun: `pip install -r requirements.txt`
3. Sunucuyu başlatın: `python server.py`
4. Sunucunun dinlediği IP adresini not alın.

### 2. İstemcileri Çalıştırma (Bilgisayar B ve C)
1. `Client` klasörüne gidin ve C# projesini derleyin.
2. Oluşan `.exe` dosyasını çalıştırın.
3. Arayüzden "Sunucu IP" alanına Bilgisayar A'nın IP adresini girin ve bağlanın.
4. Anahtar dağıtım yöntemini (RSA, DH, ECC, Kyber) seçerek haberleşmeyi başlatın.

## 📁 Manuel AES Modülü
Kütüphane kullanılmadan yazılan AES-128 implementasyonu ve standart kütüphane ile yapılan karşılaştırma testleri `Manual_AES` klasörü altında bulunmaktadır.
