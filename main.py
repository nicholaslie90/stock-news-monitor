import feedparser
import requests
import time
from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote
from email.utils import parsedate_to_datetime
import json
import sys

# --- KONFIGURASI ---
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# File to persist links we've already sent so we don't resend them
SENT_FILE = os.environ.get('SENT_LINKS_FILE', 'sent_links.json')

# UPDATED: Menambahkan 'OR site:investor.id'
# Google News akan mencari kata kunci "saham/IHSG/dll" di dalam 3 website ini
RAW_KEYWORDS = "saham OR IHSG OR BBCA OR BBRI OR GOTO site:kontan.co.id OR site:bisnis.com OR site:investor.id"

encoded_keywords = quote(RAW_KEYWORDS)
RSS_URL = f"https://news.google.com/rss/search?q={encoded_keywords}&hl=id-ID&gl=ID&ceid=ID:id"


def load_sent_links(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"Warning: gagal membaca {path}: {e}")
    return set()


def save_sent_links(path, sent_set):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(sent_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: gagal menyimpan {path}: {e}")


def send_telegram_message(session, message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diatur.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # disable_web_page_preview=True agar chat tidak penuh dengan gambar thumbnail link
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true"
    }
    try:
        resp = session.post(url, data=data, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Error network saat kirim Telegram: {e}")
        return False


def parse_entry_published(entry):
    # Try RSS published/updated string and parse into timezone-aware datetime (UTC)
    raw = entry.get("published") or entry.get("updated") or ""
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            # parsedate_to_datetime may return naive datetime for some feeds: assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                # Normalize to UTC
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            pass

    # Fallback: try published_parsed if present (struct_time)
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            # feedparser struct_time is usually in UTC -> convert properly
            ts = time.mktime(entry.published_parsed)  # seconds since epoch (local)
            # To be safe, prefer parsedate_to_datetime approach above. If we get here,
            # assume struct_time is UTC and build datetime directly.
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt
    except Exception:
        pass

    # Last resort: now in UTC
    return datetime.now(timezone.utc)


def check_news():
    print("--- Memulai Pengecekan Berita ---")

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = session.get(RSS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        print(f"Error mengambil RSS: {e}")
        return

    # Filter waktu: 45 menit (overlap aman dengan jadwal cron 30 menit)
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=45)

    sent_links = load_sent_links(SENT_FILE)

    count = 0
    # Membalik urutan agar berita terlama (dalam window waktu) dikirim duluan
    for entry in reversed(feed.entries):
        link = entry.get("link") or ""
        if not link:
            continue

        # Skip already sent links (persisted)
        if link in sent_links:
            continue

        published_time = parse_entry_published(entry)

        # only consider items within our time window
        if published_time and published_time > time_threshold:
            title = entry.get("title", "").replace("<b>", "").replace("</b>", "")
            source = entry.get("source", {}).get("title") if entry.get("source") else "Google News"

            # --- FORMAT COMPACT ---
            wib_time = published_time.astimezone(timezone.utc) + timedelta(hours=7)
            time_str = wib_time.strftime("%H:%M")

            # escape single quotes in URL to avoid breaking HTML attribute if present
            link_safe = link.replace("'", "%27")

            msg = (
                f"🗞 <a href='{link_safe}'><b>{title}</b></a>\n"
                f"↳ <i>{source} • {time_str} WIB</i>"
            )

            success = send_telegram_message(session, msg)
            if success:
                sent_links.add(link)
                # persist after each successful send to avoid duplicates if process stops
                save_sent_links(SENT_FILE, sent_links)
                count += 1
                print(f"-> Terkirim: {title}")
                time.sleep(1)  # small delay agar urutan di Telegram rapi
            else:
                print(f"-> Gagal mengirim: {title}")

    if count == 0:
        print("Tidak ada berita baru.")
    else:
        print(f"Selesai. {count} pesan terkirim.")


if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: Config belum lengkap. Set TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID.")
        sys.exit(1)
    check_news()
