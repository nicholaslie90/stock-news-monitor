import feedparser
import requests
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote
from time import mktime

# --- KONFIGURASI ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# UPDATED: Menambahkan 'OR site:investor.id'
# Google News akan mencari kata kunci "saham/IHSG/dll" di dalam 3 website ini
RAW_KEYWORDS = "saham OR IHSG OR BBCA OR BBRI OR GOTO site:kontan.co.id OR site:bisnis.com OR site:investor.id"

encoded_keywords = quote(RAW_KEYWORDS)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_keywords}&hl=id-ID&gl=ID&ceid=ID:id"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # disable_web_page_preview=True agar chat tidak penuh dengan gambar thumbnail link
    data = {
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": "true"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error network: {e}")

def check_news():
    print("--- Memulai Pengecekan Berita ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"Error mengambil RSS: {e}")
        return

    # Filter waktu: 45 menit (overlap aman dengan jadwal cron 30 menit)
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=45) 
    
    count = 0
    # Membalik urutan agar berita terlama (dalam window waktu) dikirim duluan
    for entry in reversed(feed.entries):
        if hasattr(entry, 'published_parsed'):
            published_time = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
        else:
            published_time = datetime.now(timezone.utc)

        if published_time > time_threshold:
            title = entry.title
            link = entry.link
            source = entry.source.title if 'source' in entry else "Google News"
            
            # Bersihkan judul
            title = title.replace("<b>", "").replace("</b>", "")
            
            # --- FORMAT COMPACT ---
            wib_time = published_time + timedelta(hours=7)
            time_str = wib_time.strftime("%H:%M")

            msg = (
                f"🗞 <a href='{link}'><b>{title}</b></a>\n"
                f"↳ <i>{source} • {time_str} WIB</i>"
            )
            
            send_telegram_message(msg)
            count += 1
            print(f"-> Terkirim: {title}")
            time.sleep(2) # Delay agar urutan di Telegram rapi
            
    if count == 0:
        print("Tidak ada berita baru.")
    else:
        print(f"Selesai. {count} pesan terkirim.")

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: Config belum lengkap.")
    else:
        check_news()
