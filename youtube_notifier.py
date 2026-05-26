import os
import json
import time
import logging
import requests

from dotenv import load_dotenv
from yt_dlp import YoutubeDL

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =========================
# LOAD ENV
# =========================

load_dotenv()

CHANNEL_ID = os.getenv("CHANNEL_ID")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))

if not all([CHANNEL_ID, TG_BOT_TOKEN, TG_CHAT_ID]):
    raise ValueError("❌ Заполни .env файл")

STATE_FILE = "sent_videos.json"

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# =========================
# REQUESTS SESSION
# =========================

session = requests.Session()

retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry_strategy)

session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# =========================
# SAVE STATE
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
# FETCH YOUTUBE VIDEO
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

            if not video_id:
                logger.warning("⚠️ Не удалось получить video ID")
                return None

            return {
                "id": video_id,
                "title": latest.get("title", "Без названия"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": latest.get("upload_date", "Unknown")
            }

    except Exception as e:
        logger.error(f"❌ Ошибка YouTube: {e}")
        return None

# =========================
# SEND TO TELEGRAM
# =========================

def send_to_telegram(video):

    text = (
        f"🎬 <b>Новое видео</b>\n\n"
        f"📺 {video['title']}\n\n"
        f"🔗 <a href='{video['url']}'>Смотреть на YouTube</a>\n\n"
        f"📅 {video['published']}"
    )

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:

        response = session.post(
            url,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            logger.info("✅ Отправлено в Telegram")
            return True

        logger.error(
            f"❌ Telegram API Error: "
            f"{response.status_code} {response.text}"
        )

        return False

    except Exception as e:
        logger.error(f"❌ Ошибка Telegram: {e}")
        return False

# =========================
# MAIN LOOP
# =========================

def main():

    logger.info("🤖 YouTube Notifier запущен")
    logger.info(f"📺 CHANNEL_ID: {CHANNEL_ID}")
    logger.info(f"⏱ CHECK_INTERVAL: {CHECK_INTERVAL} сек")

    sent_videos = load_sent_videos()

    while True:

        try:

            video = fetch_latest_video()

            if video:

                if video["id"] not in sent_videos:

                    logger.info(f"🆕 Новое видео: {video['title']}")

                    success = send_to_telegram(video)

                    if success:

                        sent_videos.add(video["id"])

                        # хранить только последние 50
                        if len(sent_videos) > 50:
                            sent_videos = set(list(sent_videos)[-50:])

                        save_sent_videos(sent_videos)

                else:
                    logger.info("📭 Новых видео нет")

            else:
                logger.warning("⚠️ Видео не получено")

        except Exception as e:
            logger.error(f"💥 MAIN LOOP ERROR: {e}")

        time.sleep(CHECK_INTERVAL)

# =========================

if __name__ == "__main__":
    main()