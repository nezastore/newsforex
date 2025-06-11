# Impor library 'io' di bagian paling atas
import io
import requests
import pandas as pd
from datetime import datetime, timedelta
import dateutil.parser
import time
import os
import google.generativeai as genai

# --- ⚙️ KONFIGURASI WAJIB ⚙️ ---
# Kredensial Anda sudah benar, tidak perlu diubah.
TELEGRAM_BOT_TOKEN = "7671514391:AAEzysUcRtIEnGVjBfZw45wY3S7Qf-foAIk"
TELEGRAM_CHAT_ID = "-1002402298037"
GEMINI_API_KEY = "AIzaSyDn_mFWC3blDrHDArL54pECw-wTKbOESdw"

# --- 🔧 PENGATURAN LAINNYA 🔧 ---
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"
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
        currency = event.get('Currency', 'N/A') # Menggunakan .get() untuk keamanan
        print(f"🧠 Menganalisis '{event.get('Title', 'Tanpa Judul')}' dengan Gemini (Bahasa Indonesia)...")
        prompt = (
            f"Anda adalah seorang analis pasar keuangan. Berikan analisis singkat dalam Bahasa Indonesia mengenai potensi dampak pasar dari berita ekonomi: '{event.get('Title', 'Tanpa Judul')}' yang berpengaruh pada mata uang '{currency}'.\n"
            f"Data perkiraan (forecast) adalah '{event.get('Forecast', '-')}' dan data sebelumnya (previous) adalah '{event.get('Previous', '-')}'.\n"
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
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(CALENDAR_URL, headers=headers)
        response.raise_for_status()
        csv_file = io.StringIO(response.text)
        df = pd.read_csv(csv_file)
        
        # --- PERBAIKAN 1: Hapus baris yang kolom Currency-nya kosong ---
        df.dropna(subset=['Currency'], inplace=True)
        # ----------------------------------------------------------------

        df['DateTimeUTC'] = df.apply(lambda row: dateutil.parser.parse(row['Date'] + ' ' + row['Time']), axis=1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengambil data CSV: {e}")
        return
    except Exception as e:
        print(f"❌ Gagal memproses data CSV: {e}")
        return

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
        # --- PERBAIKAN 2: Gunakan .get() untuk akses yang lebih aman ---
        try:
            event_id = f"{event.get('DateTimeUTC')}-{event.get('Title')}-{event.get('Currency')}"
            currency = event.get('Currency', 'N/A') # N/A = Not Available
            title = event.get('Title', 'Tanpa Judul')
            impact = event.get('Impact', 'Unknown')
            waktu_berita_wib = event.get('DateTimeUTC') + timedelta(hours=7)
            forecast = event.get('Forecast', '-')
            previous = event.get('Previous', '-')

            if event_id in notified_events:
                continue
        except Exception as e:
            print(f"⚠️ Gagal memproses baris data, melewati. Error: {e}")
            continue
        # ---------------------------------------------------------------

        print(f"Menemukan event baru: {title}")
        
        print(f"Meminta analisis untuk {title}...")
        analisis_gemini = analyze_with_gemini(event) # Mengirim 'event' series utuh
        
        pesan_lengkap = (
            f"{get_impact_emoji(impact)} *AUTO NEWS & ANALYSIS* {get_impact_emoji(impact)}\n\n"
            f"🗓️ *Berita:* {title}\n"
            f"🇦🇺 *Mata Uang:* {currency}\n"
            f"💥 *Dampak:* {impact}\n\n"
            f"⏰ *Waktu Rilis (WIB):* {waktu_berita_wib.strftime('%A, %d %B %Y, %H:%M')}\n\n"
            f"📊 *Data*:\n"
            f"   - Perkiraan: `{forecast}`\n"
            f"   - Sebelumnya: `{previous}`\n\n"
            f"🤖 *Analisis Otomatis Gemini (ID):*\n"
            f"{analisis_gemini}"
        )
        
        if send_telegram_notification(pesan_lengkap):
            save_notified_event(event_id)
        
        time.sleep(3)

if __name__ == "__main__":
    if "GANTI_DENGAN" in TELEGRAM_BOT_TOKEN or "GANTI_DENGAN" in GEMINI_API_KEY:
        print("‼️ KESALAHAN: Harap isi TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, dan GEMINI_API_KEY di dalam skrip.")
    else:
        check_and_notify()
