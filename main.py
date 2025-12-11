import feedparser
import requests
import time
from datetime import datetime, timedelta
from time import mktime
import os

# --- KONFIGURASI ---
# Gunakan Environment Variables agar aman saat di-hosting
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Keyword pencarian Google News (RSS)
# Contoh: Mencari berita tentang saham BBCA, BBRI, atau IHSG
KEYWORDS = "saham OR IHSG OR BBCA OR BBRI OR GOTO site:kontan.co.id OR site:bisnis.com"
RSS_URL = f"https://news.google.com/rss/search?q={KEYWORDS}&hl=id-ID&gl=ID&ceid=ID:id"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Gagal mengirim pesan: {e}")

def check_news():
    print("Memeriksa berita...")
    feed = feedparser.parse(RSS_URL)
    
    # Kita hanya ambil berita yang rilis dalam X menit terakhir
    # Sesuaikan dengan jadwal cron job (misal: setiap 30 menit)
    time_threshold = datetime.utcnow() - timedelta(minutes=35) 

    count = 0
    for entry in feed.entries:
        # Konversi waktu publikasi berita ke format datetime
        published_time = datetime.fromtimestamp(mktime(entry.published_parsed))
        
        if published_time > time_threshold:
            title = entry.title
            link = entry.link
            source = entry.source.title if 'source' in entry else "Google News"
            
            # Format Pesan
            msg = (
                f"🚨 <b>Berita Pasar Modal Baru!</b>\n\n"
                f"📰 {title}\n"
                f"via {source}\n\n"
                f"🔗 <a href='{link}'>Baca Selengkapnya</a>"
            )
            
            send_telegram_message(msg)
            count += 1
            print(f"Terkirim: {title}")
            
    if count == 0:
        print("Tidak ada berita baru dalam 30 menit terakhir.")

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN dan CHAT_ID belum diset.")
    else:
        check_news()