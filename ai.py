# ==============================================================================
#                 CRYPTO NEWS BOT with GEMINI AI (Versi Final)
# ==============================================================================
# Deskripsi:
# Versi final yang menggabungkan struktur bot interaktif dengan logika
# scraping, analisis AI yang ringkas, dan pengiriman notifikasi.
# ==============================================================================

import io
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import google.generativeai as genai
import pytz
import asyncio

# Library eksternal, pastikan sudah di-install via requirements.txt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- ⚙️ KONFIGURASI WAJIB (Isi bagian ini) ⚙️ ---
TELEGRAM_BOT_TOKEN = "5693466430:AAFQK4rII8jbty-63wBVL3FaTskVEhyQg1w"
GEMINI_API_KEY = "AIzaSyAgBNsxwQzFSVWQuEUKe7PkKykcX42BAx8"

# --- 🔧 PENGATURAN LAINNYA 🔧 ---
CALENDAR_URL = "https://www.cryptocraft.com/calendar"
HOURS_AHEAD_TO_CHECK = 48
MINIMUM_IMPACT_LEVELS = ['High', 'Medium']
CHECK_INTERVAL_SECONDS = 1800  # 30 menit
NOTIFIED_EVENTS_FILE = "notified_crypto_events_history.txt"
SUBSCRIBERS_FILE = "subscribers.txt"

# --- FUNGSI-FUNGSI UTAMA ---

def setup_gemini():
    """Mengkonfigurasi dan mengembalikan model Gemini."""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        print("✅ Model Gemini berhasil dikonfigurasi.")
        return model
    except Exception as e:
        print(f"❌ Gagal mengkonfigurasi Gemini: {e}")
        return None

gemini_model = setup_gemini()

def load_subscribers():
    """Memuat daftar ID pelanggan dari file."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_subscribers(subscribers):
    """Menyimpan daftar ID pelanggan ke file."""
    with open(SUBSCRIBERS_FILE, 'w') as f:
        for sub_id in subscribers:
            f.write(str(sub_id) + '\n')

### <<< BAGIAN INI DITAMBAHKAN KEMBALI AGAR BOT BISA MENGAMBIL DATA >>> ###
def get_page_source_with_selenium(url):
    """Mengambil source code halaman web menggunakan Selenium."""
    print("🤖 Menjalankan browser Selenium untuk mengambil data kalender...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(7)
        html_content = driver.page_source
        print("✅ Halaman kalender berhasil diambil.")
        return html_content
    except Exception as e:
        print(f"❌ Gagal menjalankan Selenium: {e}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

### <<< FUNGSI ANALISIS DENGAN PROMPT RINGKAS (DITAMBAHKAN KEMBALI) >>> ###
def analyze_with_gemini(event):
    """Menganalisis event dengan Gemini AI (versi prompt ringkas)."""
    if not gemini_model:
        return "_Analisis AI gagal: Model Gemini tidak terkonfigurasi._"
    
    try:
        print(f"🧠 Menganalisis (ringkas): '{event.get('Title', 'Tanpa Judul')}'...")
        prompt = (
            f"Anda adalah analis pasar crypto yang to-the-point. Analisis berita: '{event.get('Title', 'Tanpa Judul')}' "
            f"dengan data Perkiraan: '{event.get('Forecast', '-')}' & Sebelumnya: '{event.get('Previous', '-')}'.\n\n"
            f"Tugas Anda:\n"
            f"1. Jelaskan **inti dampaknya** ke pasar crypto global (BTC, ETH, Dan Koin koin Global / Micin/Meme) dalam satu kalimat.\n"
            f"2. Beri kesimpulan dalam 2 poin: satu untuk skenario **jika data lebih buruk**, dan satu untuk **jika data lebih baik** dari perkiraan."
        )
        response = gemini_model.generate_content(prompt, request_options={'timeout': 120})
        return response.text
    except Exception as e:
        print(f"❌ Error saat memanggil API Gemini: {e}")
        return "_Gagal mendapatkan analisis dari AI._"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyapa pengguna dan otomatis mendaftarkan mereka."""
    user_name = update.message.from_user.first_name
    chat_id = str(update.message.chat_id)
    subscribers = load_subscribers()
    if chat_id in subscribers:
        await update.message.reply_text(
            f"Selamat datang kembali, {user_name}! 👋\n\n"
            "Anda sudah aktif."
        )
    else:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        print(f"➕ Pengguna baru terdaftar: {chat_id}")
        await update.message.reply_text(
            f"Halo, {user_name}! 👋\n\n"
            "✅ Anda telah berhasil terdaftar Ketik Koin Yang Mau Di Scan Ex: BTC,ETH,Dll."
        )

async def send_notification_to_all(context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Mengirim notifikasi ke semua pengguna terdaftar."""
    subscribers = load_subscribers()
    if not subscribers:
        print("INFO: Tidak ada pelanggan, notifikasi tidak dikirim.")
        return
    print(f"INFO: Mengirim notifikasi ke {len(subscribers)} pelanggan...")
    for chat_id in subscribers:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
        except Exception as e:
            print(f"❌ GAGAL: Tidak bisa mengirim ke {chat_id}. Mungkin bot diblokir. Error: {e}")
        await asyncio.sleep(1)

### <<< FUNGSI PENGECEKAN BERITA (DILENGKAPI) >>> ###
async def check_and_notify_job(context: ContextTypes.DEFAULT_TYPE):
    """Tugas utama yang berjalan secara periodik untuk memeriksa dan memberitahu berita."""
    print(f"\n🚀 Memulai siklus pengecekan pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    html_source = get_page_source_with_selenium(CALENDAR_URL)
    if not html_source:
        print("❌ Gagal mengambil konten HTML. Melewati siklus ini.")
        return

    try:
        tables = pd.read_html(io.StringIO(html_source), attrs={'class': 'calendar__table'})
        df = tables[0].iloc[:, :9]
        df.columns = ['Date', 'Time', 'Country', 'Impact', 'Title', 'Actual', 'Forecast', 'Previous', 'Graph']
        df = df[df['Impact'].isin(MINIMUM_IMPACT_LEVELS)]
        df['Date'].fillna(method='ffill', inplace=True)
        df = df.dropna(subset=['Time'])
        df = df[~df['Time'].str.contains('All Day', na=False)]

        eastern = pytz.timezone('America/New_York')
        df['DateTimeStr'] = df['Date'].str.strip() + ' ' + df['Time'].str.replace(r'(am|pm)', r' \1', regex=True).str.strip() + f' {datetime.now().year}'
        df['DateTimeLocalized'] = pd.to_datetime(df['DateTimeStr'], format='%a %b %d %I:%M %p %Y', errors='coerce').dt.tz_localize(eastern, ambiguous='infer')
        df['DateTimeUTC'] = df['DateTimeLocalized'].dt.tz_convert(pytz.utc)
        df = df.dropna(subset=['DateTimeUTC'])

        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        upcoming_events = df[
            (df['DateTimeUTC'] > now_utc) & 
            (df['DateTimeUTC'] <= (now_utc + timedelta(hours=HOURS_AHEAD_TO_CHECK)))
        ].copy().sort_values(by='DateTimeUTC')

        if upcoming_events.empty:
            print("ℹ️ Tidak ada berita crypto yang relevan dalam waktu dekat.")
            return

        print(f"✅ Ditemukan {len(upcoming_events)} berita relevan. Memproses notifikasi...")
        notified_events = {line.strip() for line in open(NOTIFIED_EVENTS_FILE)} if os.path.exists(NOTIFIED_EVENTS_FILE) else set()

        for _, event in upcoming_events.iterrows():
            event_id = f"{event.get('DateTimeUTC')}-{event.get('Title')}-{event.get('Country')}"
            if event_id in notified_events:
                continue

            print(f"PROSES: Event baru '{event.get('Title')}' untuk {event.get('Country')}.")
            analisis_gemini = analyze_with_gemini(event)
            waktu_berita_wib = event.get('DateTimeUTC').astimezone(pytz.timezone('Asia/Jakarta'))
            
            emoji_map = {'High': '🔴', 'Medium': '🟠'}
            impact_emoji = emoji_map.get(event.get('Impact'), '⚪️')

            pesan_lengkap = (
                f"{impact_emoji} *CRYPTO NEWS & ANALYSIS*\n\n"
                f"🗓️ *Berita:* {event.get('Title', 'Tanpa Judul')}\n"
                f"💎 *Aset/Koin:* {event.get('Country', 'N/A')}\n"
                f"💥 *Dampak:* {event.get('Impact', 'Unknown')}\n\n"
                f"⏰ *Waktu Rilis (WIB):* {waktu_berita_wib.strftime('%A, %d %B %Y, %H:%M')}\n\n"
                f"📊 *Data*:\n"
                f"   - Perkiraan: `{event.get('Forecast', '-')}`\n"
                f"   - Sebelumnya: `{event.get('Previous', '-')}`\n\n"
                f"🤖 *Analisis Otomatis:*\n"
                f"{analisis_gemini}"
            )
            
            await send_notification_to_all(context, pesan_lengkap)
            
            with open(NOTIFIED_EVENTS_FILE, 'a') as f:
                f.write(event_id + '\n')
            
            await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ Terjadi error saat memproses data: {e}")

def main():
    """Fungsi utama untuk menjalankan bot."""
    print("🚀 Bot dimulai... Menunggu perintah /start dari pengguna.")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_notify_job, interval=CHECK_INTERVAL_SECONDS, first=10)

    application.run_polling()
    print("👋 Bot dihentikan.")

if __name__ == "__main__":
    main()
