import os
import json
import logging
import requests

from dotenv import load_dotenv
from yt_dlp import YoutubeDL

# =========================
# LOAD ENV
# =========================

load_dotenv()

CHANNEL_ID = os.getenv("CHANNEL_ID")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not all([CHANNEL_ID, TG_BOT_TOKEN, TG_CHAT_ID]):
    raise ValueError("❌ Заполни ENV переменные")

STATE_FILE = "sent_videos.json"

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# =========================
# STATE
# =========================

def load_sent_videos():

    if os.path.exists(STATE_FILE):

        try:

            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))

        except:
            return set()

    return set()


def save_sent_videos(videos):

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(videos), f)

# =========================
# FETCH VIDEO
# =========================

def fetch_latest_video():

    try:

        logger.info("📡 Проверяю YouTube канал")

        url = f"https://www.youtube.com/channel/{CHANNEL_ID}/videos"

        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True
        }

        with YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=False)

            entries = info.get("entries", [])

            if not entries:
                logger.warning("⚠️ Видео не найдены")
                return None

            latest = entries[0]

            video_id = latest.get("id")

            return {
                "id": video_id,
                "title": latest.get("title", "Без названия"),
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }

    except Exception as e:
        logger.error(f"❌ Ошибка YouTube: {e}")
        return None

# =========================
# TELEGRAM
# =========================

def send_to_telegram(video):

    text = (
        f"🎬 <b>Новое видео</b>\n\n"
        f"📺 {video['title']}\n\n"
        f"🔗 <a href='{video['url']}'>Смотреть</a>"
    )

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        logger.info("✅ Отправлено в Telegram")
    else:
        logger.error(response.text)

# =========================
# MAIN
# =========================

def main():

    sent_videos = load_sent_videos()

    video = fetch_latest_video()

    if not video:
        return

    if video["id"] not in sent_videos:

        logger.info(f"🆕 Новое видео: {video['title']}")

        send_to_telegram(video)

        sent_videos.add(video["id"])

        save_sent_videos(sent_videos)

    else:
        logger.info("📭 Новых видео нет")


if __name__ == "__main__":
    main()