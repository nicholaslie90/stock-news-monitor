import feedparser
import requests
import time
from datetime import datetime, timedelta
import os
from urllib.parse import quote
from time import mktime

# --- KONFIGURASI ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Keyword (sudah di-encode)
RAW_KEYWORDS = "saham OR IHSG OR BBCA OR BBRI OR GOTO site:kontan.co.id OR site:bisnis.com"
encoded_keywords = quote(RAW_KEYWORDS)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_keywords}&hl=id-ID&gl=ID&ceid=ID:id"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Gagal kirim ke Telegram: {response.text}")
    except Exception as e:
        print(f"Error network: {e}")

def check_news():
    print("--- Memulai Pengecekan Berita ---")
    
    # 1. Gunakan Header Browser agar tidak diblokir Google
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Fetch manual dengan requests
        response = requests.get(RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse konten XML
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"Error mengambil RSS: {e}")
        return

    print(f"Total item ditemukan di RSS: {len(feed.entries)}")

    # 2. Perlebar filter waktu jadi 4 JAM untuk tes
    #    (Karena delay indexing Google News bisa 1-2 jam)
    time_threshold = datetime.utcnow() - timedelta(hours=4) 
    
    count = 0
    for entry in feed.entries:
        # Ambil waktu publish (convert struct_time ke datetime object)
        if hasattr(entry, 'published_parsed'):
            published_time = datetime.fromtimestamp(mktime(entry.published_parsed))
        else:
            published_time = datetime.utcnow() # Fallback jika tidak ada tanggal

        # Debugging: Print judul dan waktu tiap berita yang ditemukan
        # print(f"Cek: {entry.title[:30]}... | Waktu: {published_time}")

        if published_time > time_threshold:
            title = entry.title
            link = entry.link
            source = entry.source.title if 'source' in entry else "Google News"
            
            # Bersihkan HTML tags dari title jika ada
            title = title.replace("<b>", "").replace("</b>", "")

            msg = (
                f"🚨 <b>Berita Pasar Modal</b>\n\n"
                f"📰 {title}\n"
                f"via {source}\n\n"
                f"🔗 <a href='{link}'>Baca Selengkapnya</a>"
            )
            
            send_telegram_message(msg)
            count += 1
            print(f"-> TERKIRIM: {title}")
            
    if count == 0:
        print("Tidak ada berita yang lolos filter waktu (4 jam terakhir).")
    else:
        print(f"Selesai. {count} pesan terkirim.")

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN dan CHAT_ID belum diset di Secrets.")
    else:
        check_news()
