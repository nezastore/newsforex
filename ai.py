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
# URL Kalender Ekonomi dari Forex Factory
CALENDAR_URL = "https://www.forexfactory.com/calendar.php?day=this" 
# Pengaturan notifikasi
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
    return {'High': '🔴', 'Medium': '🟠', 'Low': '🟡', 'Holiday': '🎉'}.get(impact, '⚪️')

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
    
    country = event.get('Country', 'N/A')
    # Jangan minta analisis untuk Holiday
    if event.get('Impact') == 'Holiday':
        return "_Hari libur bank, tidak ada dampak pasar yang signifikan._"

    try:
        print(f"🧠 Menganalisis '{event.get('Title', 'Tanpa Judul')}' dengan Gemini (Bahasa Indonesia)...")
        prompt = (
            f"Anda adalah seorang analis pasar keuangan. Berikan analisis singkat dalam Bahasa Indonesia mengenai potensi dampak pasar dari berita ekonomi: '{event.get('Title', 'Tanpa Judul')}' yang berpengaruh pada mata uang '{country}'.\n"
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
        # Menggunakan pandas untuk membaca tabel HTML langsung dari URL
        tables = pd.read_html(CALENDAR_URL, attrs={'class': 'calendar__table'})
        df = tables[0]

        # Membersihkan dan merapikan data
        df = df.dropna(subset=[('Impact', 'Impact')])
        df = df.rename(columns={('Unnamed: 3_level_0', 'Graph'): 'Graph', 
                                ('Impact', 'Impact'): 'Impact',
                                ('Forecast', 'Forecast'): 'Forecast',
                                ('Previous', 'Previous'): 'Previous',
                                ('Unnamed: 2_level_0', 'Time'): 'Time',
                                ('Unnamed: 1_level_0', 'Country'): 'Country',
                                ('Unnamed: 0_level_0', 'Date'): 'Date',
                                ('Event', 'Event'): 'Title'
                               })
        df = df[['Date', 'Time', 'Country', 'Impact', 'Title', 'Forecast', 'Previous']]
        
        # Mengisi tanggal yang kosong
        df['Date'].fillna(method='ffill', inplace=True)
        # Gabungkan Date dan Time, lalu konversi ke datetime object
        df['DateTimeStr'] = df['Date'] + ' ' + df['Time']
        # Ganti 'pm' dan 'am' dengan format yang benar
        df['DateTimeStr'] = df['DateTimeStr'].str.replace('pm', ' PM').str.replace('am', ' AM')
        df['DateTimeUTC'] = pd.to_datetime(df['DateTimeStr'], format='%b %d %I:%M %p', errors='coerce').dt.tz_localize('America/New_York').dt.tz_convert('UTC')

    except Exception as e:
        print(f"❌ Gagal mengambil atau memproses data: {e}")
        return

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
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
        try:
            event_id = f"{event.get('DateTimeUTC')}-{event.get('Title')}-{event.get('Country')}"
            country = event.get('Country', 'N/A')
            title = event.get('Title', 'Tanpa Judul')
            impact = event.get('Impact', 'Unknown')
            waktu_berita_wib = event.get('DateTimeUTC').astimezone(pytz.timezone('Asia/Jakarta'))
            forecast = event.get('Forecast', '-')
            previous = event.get('Previous', '-')

            if event_id in notified_events:
                continue
        except Exception as e:
            print(f"⚠️ Gagal memproses baris data, melewati. Error: {e}")
            continue

        print(f"Menemukan event baru: {title}")
        
        analisis_gemini = analyze_with_gemini(event)
        
        pesan_lengkap = (
            f"{get_impact_emoji(impact)} *AUTO NEWS & ANALYSIS*\n\n"
            f"🗓️ *Berita:* {title}\n"
            f"🇦🇺 *Mata Uang:* {country}\n"
            f"💥 *Dampak:* {impact}\n\n"
            f"⏰ *Waktu Rilis (WIB):* {waktu_berita_wib.strftime('%A, %d %B %Y, %H:%M')}\n\n"
            f"📊 *Data*:\n"
            f"   - Perkiraan: `{forecast}`\n"
            f"   - Sebelumnya: `{previous}`\n\n"
            f"🤖 *Analisis Otomatis Gemini:*\n"
            f"{analisis_gemini}"
        )
        
        if send_telegram_notification(pesan_lengkap):
            save_notified_event(event_id)
        
        time.sleep(3)

if __name__ == "__main__":
    if "GANTI_DENGAN" in TELEGRAM_BOT_TOKEN or "GANTI_DENGAN" in GEMINI_API_KEY:
        print("‼️ KESALAHAN: Harap isi TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, dan GEMINI_API_KEY di dalam skrip.")
    else:
        # Import pytz di sini agar tidak error jika __name__ != "__main__"
        import pytz
        check_and_notify()
