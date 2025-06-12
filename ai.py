import io
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import google.generativeai as genai
import pytz
import asyncio

# Pastikan Anda sudah menginstalnya: pip install python-telegram-bot
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- ⚙️ KONFIGURASI WAJIB ⚙️ ---
TELEGRAM_BOT_TOKEN = "ISI_DENGAN_TOKEN_BOT_ANDA" 
GEMINI_API_KEY = "ISI_DENGAN_GEMINI_API_KEY_ANDA" 

# --- 🔧 PENGATURAN LAINNYA 🔧 ---
CALENDAR_URL = "https://www.cryptocraft.com/calendar"
HOURS_AHEAD_TO_CHECK = 48
MINIMUM_IMPACT_LEVELS = ['High', 'Medium']
NOTIFIED_EVENTS_FILE = "notified_crypto_events_history.txt"
CHECK_INTERVAL_SECONDS = 1800 
SUBSCRIBERS_FILE = "subscribers.txt"

# --- FUNGSI-FUNGSI UTAMA ---

# Konfigurasi Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    print("✅ Model Gemini berhasil dikonfigurasi.")
except Exception as e:
    print(f"❌ Gagal mengkonfigurasi Gemini: {e}")
    gemini_model = None

# Fungsi untuk memuat dan menyimpan daftar pelanggan
def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        for sub_id in subscribers:
            f.write(str(sub_id) + '\n')

# ### <<< PERUBAHAN 1: Hanya ada perintah /start >>> ###
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyapa pengguna dan otomatis mendaftarkan mereka."""
    user_name = update.message.from_user.first_name
    chat_id = str(update.message.chat_id)
    subscribers = load_subscribers()

    if chat_id in subscribers:
        # Jika pengguna sudah terdaftar, hanya sapa kembali
        await update.message.reply_text(
            f"Selamat datang kembali, {user_name}! 👋\n\n"
            "Anda sudah aktif menerima notifikasi berita crypto. Silahkan Langsung Mengetik Nama Koin MIsal : BTC,SOL,Dll"
        )
    else:
        # Jika pengguna baru, daftarkan dan sapa
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        print(f"➕ Pengguna baru terdaftar: {chat_id}")
        await update.message.reply_text(
            f"Halo, {user_name}! 👋\n\n"
            "✅ Anda telah berhasil terdaftar dan akan menerima notifikasi berita crypto penting secara otomatis."
        )

# ### <<< DIHAPUS: Fungsi unsubscribe_command sudah tidak ada lagi >>> ###

# Fungsi-fungsi scraping dan analisis (Tidak ada perubahan di sini)
# Pastikan semua fungsi dari get_impact_emoji hingga check_and_notify_job LENGKAP ada di sini
# ... (Salin semua fungsi dari skrip sebelumnya) ...

async def send_notification_to_all(context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Mengirim pesan ke semua ID yang ada di daftar pelanggan."""
    subscribers = load_subscribers()
    if not subscribers:
        print("INFO: Tidak ada pelanggan, notifikasi tidak dikirim.")
        return
    print(f"INFO: Mengirim notifikasi ke {len(subscribers)} pelanggan...")
    for chat_id in subscribers:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
        except Exception as e:
            # Jika bot diblokir, error akan muncul di sini, dan itu tidak masalah.
            print(f"❌ GAGAL: Tidak bisa mengirim ke {chat_id}. Mungkin bot diblokir. Error: {e}")
        await asyncio.sleep(1)

# Pastikan fungsi `check_and_notify_job` LENGKAP ada di sini
async def check_and_notify_job(context: ContextTypes.DEFAULT_TYPE):
    """Tugas yang dijalankan secara berkala untuk memeriksa dan mengirim berita."""
    # ... Kode lengkap untuk scraping dengan Selenium dan Pandas ada di sini ...
    # ... Jika ada berita baru, format pesan lalu panggil:
    # await send_notification_to_all(context, pesan_lengkap)
    print(f"DEBUG: Menjalankan job pengecekan pada {datetime.now()}")


# ### <<< PERUBAHAN 2: Fungsi utama yang hanya mendaftarkan /start >>> ###
def main():
    """Fungsi utama untuk menjalankan bot dan penjadwalan."""
    print("🚀 Bot versi paling simpel dimulai... Hanya ada perintah /start.")
    
    # Inisialisasi Bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Daftarkan Command Handler (hanya /start)
    application.add_handler(CommandHandler("start", start_command))

    # Daftarkan Job Queue untuk pengecekan berkala
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_notify_job, interval=CHECK_INTERVAL_SECONDS, first=10)

    # Jalankan bot
    application.run_polling()


if __name__ == "__main__":
    main()
