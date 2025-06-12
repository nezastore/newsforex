# CryptoCraft News Bot with Gemini AI

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-8E77F0?style=for-the-badge&logo=google-gemini&logoColor=white)

Bot Telegram ini secara otomatis mengambil berita ekonomi terbaru dari situs [CryptoCraft.com](https://www.cryptocraft.com/calendar), menganalisis dampaknya ke pasar crypto menggunakan Google Gemini, dan mengirimkan notifikasi ke pengguna yang telah berlangganan melalui pesan pribadi.

## ✨ Fitur Utama

-   **Otomatis Penuh**: Memeriksa berita baru setiap 30 menit (dapat diubah).
-   **Analisis AI**: Memberikan analisis potensi dampak pasar dari Google Gemini untuk setiap berita.
-   **Langganan Mudah**: Pengguna cukup mengirim perintah `/start` untuk mulai menerima notifikasi secara otomatis.
-   **Berjalan di Latar Belakang**: Didesain untuk berjalan 24/7 di server menggunakan utilitas `screen`.

## 📋 Prasyarat

Sebelum memulai, pastikan Anda memiliki:
1.  Server/VPS yang menjalankan sistem operasi Linux (misalnya Ubuntu).
2.  Python 3.8 atau yang lebih baru.
3.  Token Bot Telegram dari [@BotFather](https://t.me/BotFather).
4.  API Key dari [Google AI Studio (Gemini)](https://aistudio.google.com/app/apikey).

## 🚀 Instalasi & Konfigurasi

Berikut adalah panduan langkah demi langkah untuk menjalankan bot ini di server Anda.

### 1. Unggah File Proyek
Hubungkan ke server Anda melalui SSH. Buat sebuah folder baru (misal `my-crypto-bot`), lalu unggah `bot_script.py` dan `requirements.txt` ke dalamnya.

```bash
# Contoh membuat folder
mkdir my-crypto-bot
cd my-crypto-bot
```
*Gunakan SCP, FTP, atau metode lain untuk mengunggah file Anda ke folder ini.*

### 2. Isi Kredensial
Buka file `bot_script.py` menggunakan editor teks di server (seperti `nano` atau `vim`) dan isi informasi Anda pada bagian konfigurasi.
```bash
nano bot_script.py
```
```python
# --- ⚙️ KONFIGURASI WAJIB (Isi bagian ini) ⚙️ ---
TELEGRAM_BOT_TOKEN = "ISI_DENGAN_TOKEN_BOT_ANDA" 
GEMINI_API_KEY = "ISI_DENGAN_GEMINI_API_KEY_ANDA" 
```
*Simpan file setelah mengedit (di `nano`, tekan `Ctrl+X`, lalu `Y`, lalu `Enter`).*

### 3. Siapkan Lingkungan Virtual & Install Library
Sangat disarankan untuk menggunakan *virtual environment* agar tidak mengganggu paket Python sistem Anda.

```bash
# Pastikan Anda berada di dalam folder proyek
# Buat virtual environment bernama 'venv'
python3 -m venv venv

# Aktifkan virtual environment
source venv/bin/activate

# Install semua library yang dibutuhkan dengan satu perintah
pip install -r requirements.txt
```
*Tunggu hingga proses instalasi semua library selesai.*

### 4. Jalankan Bot Menggunakan `screen`
`screen` akan memastikan bot tetap berjalan meskipun Anda menutup terminal SSH.

```bash
# Jika screen belum terinstall (biasanya sudah ada)
# sudo apt-get update && sudo apt-get install screen

# 1. Buat sesi screen baru dengan nama 'bot_crypto'
screen -S bot_crypto

# 2. Setelah layar terminal bersih, jalankan skrip Python di dalamnya
python bot_script.py

# 3. Bot sekarang berjalan. Untuk keluar dari screen tanpa mematikan bot:
#    Tekan Ctrl+A, lalu lepas, lalu tekan D
```
Sekarang bot Anda sudah berjalan di latar belakang. Anda bisa menutup koneksi SSH dengan aman.

## ⚙️ Cara Penggunaan Bot (Untuk Pengguna)
Interaksi dengan bot ini sangat sederhana.
1.  Temukan bot Anda di Telegram.
2.  Tekan tombol **Start** atau kirim perintah `/start`.
3.  Selesai! Pengguna akan otomatis terdaftar untuk menerima notifikasi.

Untuk berhenti menerima notifikasi, pengguna cukup memblokir bot dari sisi aplikasi Telegram mereka.

## 🛠️ Manajemen Bot di Server

Berikut adalah perintah `screen` yang berguna untuk mengelola bot Anda.

-   **Melihat daftar sesi yang sedang berjalan:**
    ```bash
    screen -ls
    ```

-   **Menyambung kembali ke sesi bot (untuk melihat log):**
    ```bash
    screen -r bot_crypto
    ```

-   **Mematikan bot secara permanen:**
    1.  Sambung kembali ke sesi `screen -r bot_crypto`.
    2.  Hentikan skrip dengan menekan `Ctrl+C`.
    3.  Ketik `exit` dan tekan Enter untuk menutup sesi `screen`.

## ⚠️ Disclaimer
Bot ini bergantung pada struktur HTML dari `cryptocraft.com`. Jika situs tersebut mengubah desainnya, fungsi _scraping_ mungkin perlu disesuaikan.
