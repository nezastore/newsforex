import io
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import google.generativeai as genai
import pytz

# Import library baru untuk Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- ⚙️ KONFIGURASI WAJIB ⚙️ ---
# Kredensial Anda sudah benar, tidak perlu diubah.
TELEGRAM_BOT_TOKEN = "7671514391:AAEzysUcRtIEnGVjBfZw45wY3S7Qf-foAIk"
TELEGRAM_CHAT_ID = "-1002402298037"
GEMINI_API_KEY = "AIzaSyDn_mFWC3blDrHDArL54pECw-wTKbOESdw"

# --- 🔧 PENGATURAN LAINNYA 🔧 ---
CALENDAR_URL = "https://www.forexfactory.com/calendar?day=this" 
HOURS_AHEAD_TO_CHECK = 48
MINIMUM_IMPACT_LEVELS = ['High', 'Medium', 'Holiday']
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
    if not os.path.exists(NOTIFIED_EVENTS_FILE): return set()
    with open(NOTIFIED_EVENTS_FILE, 'r') as f: return set(line.strip() for line in f)

def save_notified_event(event_id):
    with open(NOTIFIED_EVENTS_FILE, 'a') as f: f.write(str(event_id) + '\n')

def send_telegram_notification(message_text):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message_text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Notifikasi berhasil dikirim!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengirim notifikasi: {e}"); return False

def analyze_with_gemini(event):
    if not gemini_model: return "_Analisis AI gagal: Model Gemini tidak terkonfigurasi._"
    
    country = event.get('Country', 'N/A')
    if event.get('Impact') == 'Holiday':
        return "_Hari libur bank, tidak ada dampak pasar yang signifikan._"

    try:
        print(f"🧠 Menganalisis '{event.get('Title', 'Tanpa Judul')}'...")
        prompt = (
            f"Anda adalah seorang analis pasar keuangan. Berikan analisis singkat dalam Bahasa Indonesia mengenai potensi dampak pasar dari berita ekonomi: '{event.get('Title', 'Tanpa Judul')}' yang berpengaruh pada mata uang '{country}'.\n"
            f"Data perkiraan (forecast) adalah '{event.get('Forecast', '-')}' dan data sebelumnya (previous) adalah '{event.get('Previous', '-')}'.\n"
            f"Fokus pada kemungkinan reaksi pasar (misalnya pada mata uang terkait, indeks saham, dan Emas) jika data aktual yang dirilis jauh lebih tinggi atau lebih rendah dari perkiraan. Sampaikan secara ringkas dan gunakan poin-poin."
        )
        response = gemini_model.generate_content(prompt)
        print("💡 Analisis Gemini diterima.")
        return response.text
    except Exception as e:
        print(f"❌ Error saat memanggil API Gemini: {e}"); return "_Gagal mendapatkan analisis dari AI._"

def get_page_source_with_selenium(url):
    """Menggunakan Selenium untuk mengambil HTML dari halaman yang dilindungi."""
    print("🤖 Menjalankan browser Selenium untuk melewati keamanan...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Berjalan tanpa membuka jendela browser
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.get(url)
    time.sleep(5)  # Beri waktu 5 detik untuk halaman memuat semua JavaScript
    
    html_content = driver.page_source
    driver.quit()
    print("✅ Halaman berhasil diambil oleh Selenium.")
    return html_content

def check_and_notify():
    print(f"\n🚀 Memulai pengecekan pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        # --- PERBAIKAN FINAL MENGGUNAKAN SELENIUM ---
        html_source = get_page_source_with_selenium(CALENDAR_URL)
        tables = pd.read_html(io.StringIO(html_source), attrs={'class': 'calendar__table'})
        # --- AKHIR PERBAIKAN ---
        
        df = tables[0]
        df.columns = ['_'.join(map(str, col)) for col in df.columns.values]
        df = df.rename(columns={'Date_Date': 'Date', 'Country_Country': 'Country', 'Time_Time': 'Time', 'Impact_Impact':'Impact', 'Event_Event':'Title', 'Forecast_Forecast':'Forecast', 'Previous_Previous':'Previous'})
        df = df[['Date', 'Time', 'Country', 'Impact', 'Title', 'Forecast', 'Previous']]
        df = df[df['Impact'].isin(MINIMUM_IMPACT_LEVELS)]

        df['Date'].fillna(method='ffill', inplace=True)
        df['DateTimeStr'] = df['Date'] + ' ' + df['Time']
        df['DateTimeStr'] = df['DateTimeStr'].str.replace('pm', ' PM').str.replace('am', ' AM').str.strip()
        df = df[~df['Time'].str.contains('All Day', na=False)]
        df = df.dropna(subset=['Time']) # Hapus baris tanpa waktu

        eastern = pytz.timezone('America/New_York')
        current_year = datetime.now().year
        df['DateTimeLocalized'] = df['DateTimeStr'].apply(
            lambda x: eastern.localize(pd.to_datetime(f"{x} {current_year}", format='%a %b %d %I:%M %p %Y', errors='coerce'), is_dst=None)
        )
        df['DateTimeUTC'] = df['DateTimeLocalized'].dt.tz_convert(pytz.utc)
        df = df.dropna(subset=['DateTimeUTC'])

    except Exception as e:
        print(f"❌ Gagal mengambil atau memproses data: {e}")
        return

    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    time_limit = now_utc + timedelta(hours=HOURS_AHEAD_TO_CHECK)
    
    upcoming_events = df[
        (df['DateTimeUTC'] > now_utc) & (df['DateTimeUTC'] <= time_limit)
    ].sort_values(by='DateTimeUTC')

    if upcoming_events.empty:
        print("ℹ️ Tidak ada berita relevan dalam waktu dekat.")
        return

    print(f"✅ Ditemukan {len(upcoming_events)} berita relevan. Memproses notifikasi...")
    
    notified_events = load_notified_events()

    for index, event in upcoming_events.iterrows():
        try:
            event_id = f"{event.get('DateTimeUTC')}-{event.get('Title')}-{event.get('Country')}"
            if event_id in notified_events: continue
            
            # ... (sisa kode sama)
            country = event.get('Country', 'N/A')
            title = event.get('Title', 'Tanpa Judul')
            impact = event.get('Impact', 'Unknown')
            waktu_berita_wib = event.get('DateTimeUTC').astimezone(pytz.timezone('Asia/Jakarta'))
            forecast = event.get('Forecast', '-')
            previous = event.get('Previous', '-')
        except Exception as e:
            print(f"⚠️ Gagal memproses baris data, melewati. Error: {e}"); continue

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
    check_and_notify()
