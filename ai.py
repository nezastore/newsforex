# Menambahkan 'import io' di sini
import io
import requests
import pandas as pd
from datetime import datetime, timedelta
import dateutil.parser
import time
import os
import google.generativeai as genai

# --- ⚙️ KONFIGURASI WAJIB ⚙️ ---
# Kredensial Anda aman dan tidak diubah.

# 1. Kredensial Telegram
TELEGRAM_BOT_TOKEN = "7671514391:AAEzysUcRtIEnGVjBfZw45wY3S7Qf-foAIk"
TELEGRAM_CHAT_ID = "-1002402298037"

# 2. Kredensial Google Gemini
GEMINI_API_KEY = "AIzaSyDn_mFWC3blDrHDArL54pECw-wTKbOESdw"

# 3. URL Kalender Ekonomi (tidak perlu diubah)
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"

# --- 🔧 PENGATURAN NOTIFIKASI 🔧 ---
HOURS_AHEAD_TO_CHECK = 48
MINIMUM_IMPACT_LEVELS = ['High', 'Medium']
NOTIFIED_EVENTS_FILE = "notified_events_history.txt"

# --- KODE UTAMA ---

# Konfigurasi model Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    print("✅ Model Gemini berhasil dikonfigurasi.")
except Exception as e:
    print(f"❌ Gagal mengkonfigurasi Gemini. Periksa API Key Anda. Error: {e}")
    gemini_model = None

def get_impact_emoji(impact):
    return {'High': '🔴', 'Medium': '🟠', 'Low': '🟡'}.get(impact, '⚪️')

def load_notified_events():
    if not os.path.exists(NOTIFIED_EVENTS_FILE):
        return set()
    with open(NOTIFIED_EVENTS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_notified_event(event_id):
    with open(NOTIFIED_EVENTS_FILE, 'a') as f:
        f.write(str(event_id) + '\n')

def send_telegram_notification(message_text):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message_text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Notifikasi berhasil dikirim!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengirim notifikasi: {e}")
        return False

def analyze_with_gemini(event):
    if not gemini_model:
        return "_Analisis AI gagal: Model Gemini tidak terkonfigurasi._"

    try:
        print(f"🧠 Menganalisis '{event['Title']}' dengan Gemini (Bahasa Indonesia)...")
        prompt = (
            f"Anda adalah seorang analis pasar keuangan. Berikan analisis singkat dalam Bahasa Indonesia mengenai potensi dampak pasar dari berita ekonomi: '{event['Title']}' yang berpengaruh pada mata uang '{event['Currency']}'.\n"
            f"Data perkiraan (forecast) adalah '{event['Forecast']}' dan data sebelumnya (previous) adalah '{event['Previous']}'.\n"
            f"Fokus pada kemungkinan reaksi pasar (misalnya pada mata uang terkait, indeks saham, dan Emas) jika data aktual yang dirilis jauh lebih tinggi atau lebih rendah dari perkiraan. Sampaikan secara ringkas dan gunakan poin-poin (bullet points)."
        )
        
        response = gemini_model.generate_content(prompt)
        print("💡 Analisis Gemini (ID) diterima.")
        return response.text
    except Exception as e:
        print(f"❌ Error saat memanggil API Gemini: {e}")
        return "_Gagal mendapatkan analisis dari AI saat ini._"

def check_and_notify():
    print(f"\n🚀 Memulai pengecekan pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # --- BAGIAN YANG DIPERBAIKI UNTUK MENGATASI ERROR 403 ---
    try:
        # Menambahkan headers agar terlihat seperti browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Menggunakan requests untuk mengambil data dengan headers
        response = requests.get(CALENDAR_URL, headers=headers)
        response.raise_for_status()  # Ini akan error jika status bukan 200 OK
        
        # Membaca data CSV dari teks yang didapat
        csv_file = io.StringIO(response.text)
        df = pd.read_csv(csv_file)
        
        df['DateTimeUTC'] = df.apply(lambda row: dateutil.parser.parse(row['Date'] + ' ' + row['Time']), axis=1)
    # Menangkap error lebih spesifik
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengambil data CSV: {e}")
        return
    except Exception as e:
        print(f"❌ Gagal memproses data CSV: {e}")
        return
    # --- AKHIR BAGIAN YANG DIPERBAIKI ---

    now_utc = datetime.utcnow()
    time_limit = now_utc + timedelta(hours=HOURS_AHEAD_TO_CHECK)
    
    upcoming_events = df[
        (df['DateTimeUTC'] > now_utc) &
        (df['DateTimeUTC'] <= time_limit) &
        (df['Impact'].isin(MINIMUM_IMPACT_LEVELS))
    ].sort_values(by='DateTimeUTC')

    if upcoming_events.empty:
        print("ℹ️ Tidak ada berita relevan dalam waktu dekat.")
        return

    print(f"✅ Ditemukan {len(upcoming_events)} berita relevan. Memproses notifikasi...")
    
    notified_events = load_notified_events()

    for index, event in upcoming_events.iterrows():
        event_id = f"{event['DateTimeUTC']}-{event['Title']}-{event['Currency']}"

        if event_id in notified_events:
            continue

        print(f"Menemukan event baru: {event['Title']}")
        waktu_berita_wib = event['DateTimeUTC'] + timedelta(hours=7)
        
        print(f"Meminta analisis untuk {event['Title']}...")
        analisis_gemini = analyze_with_gemini(event)
        
        pesan_lengkap = (
            f"{get_impact_emoji(event['Impact'])} *AUTO NEWS & ANALYSIS* {get_impact_emoji(event['Impact'])}\n\n"
            f"🗓️ *Berita:* {event['Title']}\n"
            f"🇦🇺 *Mata Uang:* {event['Currency']}\n"
            f"💥 *Dampak:* {event['Impact']}\n\n"
            f"⏰ *Waktu Rilis (WIB):* {waktu_berita_wib.strftime('%A, %d %B %Y, %H:%M')}\n\n"
            f"📊 *Data*:\n"
            f"   - Perkiraan: `{event['Forecast']}`\n"
            f"   - Sebelumnya: `{event['Previous']}`\n\n"
            f"🤖 *Analisis Otomatis Gemini (ID):*\n"
            f"{analisis_gemini}"
        )
        
        if send_telegram_notification(pesan_lengkap):
            save_notified_event(event_id)
        
        time.sleep(3)

if __name__ == "__main__":
    # Pemeriksaan ini sekarang akan lolos karena kunci Anda sudah diisi
    if "GANTI_DENGAN" in TELEGRAM_BOT_TOKEN or "GANTI_DENGAN" in GEMINI_API_KEY:
        print("‼️ KESALAHAN: Harap isi TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, dan GEMINI_API_KEY di dalam skrip.")
    else:
        check_and_notify()
