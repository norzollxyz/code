# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                          TITAN V26.0 OMEGA                                 ║
# ║                Gemini 2.5 Flash-Lite • Render-ready • Monolith            ║
# ║                     Максимально навороченный бот                           ║
# ╚════════════════════════════════════════════════════════════════════════════╝

import os
import sys
import json
import time
import base64
import random
import logging
import threading
import traceback
import requests
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, jsonify

# ──────────────────────────────────────────────────────────────────────────────
#  CONFIG — все важные константы в одном месте
# ──────────────────────────────────────────────────────────────────────────────

class Config:
    VERSION = "26.0 OMEGA (Gemini 2.5 Flash-Lite • Max Visual)"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAA34DLgf16NnjEOUoBiXWd0OKPP_eTXKo"           # твой ключ

    # Модель — самая щедрая бесплатная на март 2026
    GEMINI_MODEL = "gemini-2.5-flash-lite-preview-03-26"
    GEMINI_FALLBACK_MODEL = "gemini-1.5-flash-latest"

    MAIN_ADMIN_ID = 5378010557

    ROOT_DIR = "TITAN_V26_VAULT"
    DIRS = {
        "db":       f"{ROOT_DIR}/database",
        "logs":     f"{ROOT_DIR}/logs",
        "temp":     f"{ROOT_DIR}/temp_media",
        "backups":  f"{ROOT_DIR}/backups"
    }

    FILES = {
        "users":    f"{DIRS['db']}/users.json",
        "admins":   f"{DIRS['db']}/admins.json",
        "bans":     f"{DIRS['db']}/bans.json",
        "stats":    f"{DIRS['db']}/stats.json",
        "settings": f"{DIRS['db']}/settings.json",
        "log":      f"{DIRS['logs']}/titan.log",
        "errors":   f"{DIRS['logs']}/errors.log"
    }

    # Таймауты и защита от бана
    REQUEST_TIMEOUT = 50
    MAX_RETRIES = 5
    FLOOD_SLEEP = 1.4
    MAX_MESSAGE_LENGTH = 3800
    PROGRESS_STAGES = 6

    # Цвета для консоли (если терминал поддерживает)
    COLORS = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }


# ──────────────────────────────────────────────────────────────────────────────
#  LOGGER — красивое логирование с цветами и файлами
# ──────────────────────────────────────────────────────────────────────────────

class TitanLogger:
    @staticmethod
    def setup():
        for d in Config.DIRS.values():
            os.makedirs(d, exist_ok=True)

        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                color = Config.COLORS.get(record.levelname, "")
                reset = Config.COLORS["RESET"]
                msg = super().format(record)
                return f"{color}{msg}{reset}"

        handler_file = logging.FileHandler(Config.FILES["log"], encoding="utf-8")
        handler_console = logging.StreamHandler(sys.stdout)
        handler_errors = logging.FileHandler(Config.FILES["errors"], encoding="utf-8")

        formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        handler_file.setFormatter(formatter)
        handler_console.setFormatter(formatter)
        handler_errors.setLevel(logging.ERROR)
        handler_errors.setFormatter(formatter)

        logging.basicConfig(level=logging.INFO, handlers=[handler_file, handler_console, handler_errors])
        logging.info("✨ TITAN V26.0 OMEGA logger initialized ✨")


# ──────────────────────────────────────────────────────────────────────────────
#  DATABASE — атомарная запись, бэкапы, статистика
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    _lock = Lock()

    @classmethod
    def init(cls):
        defaults = {
            Config.FILES["users"]:    {},
            Config.FILES["admins"]:   [Config.MAIN_ADMIN_ID],
            Config.FILES["bans"]:     [],
            Config.FILES["stats"]:    {
                "total_users": 0,
                "ai_requests": 0,
                "images": 0,
                "errors": 0,
                "daily": {}
            },
            Config.FILES["settings"]: {
                "maintenance": False,
                "ai_enabled": True,
                "welcome_message": "🌌 Добро пожаловать в TITAN V26.0"
            }
        }

        for path, data in defaults.items():
            if not os.path.exists(path):
                with cls._lock:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                logging.info(f"Создана база → {os.path.basename(path)}")

    @classmethod
    def read(cls, path):
        with cls._lock:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Ошибка чтения {path}: {e}")
                return None

    @classmethod
    def write(cls, path, data):
        with cls._lock:
            tmp = path + ".tmp"
            backup = f"{Config.DIRS['backups']}/{os.path.basename(path)}_{int(time.time())}.bak"
            try:
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                if os.path.exists(path):
                    os.replace(path, backup)
                os.replace(tmp, path)
                return True
            except Exception as e:
                logging.error(f"Ошибка записи {path}: {e}")
                if os.path.exists(tmp):
                    os.remove(tmp)
                return False

    @classmethod
    def register_user(cls, uid, username, first_name):
        users = cls.read(Config.FILES["users"]) or {}
        uid_str = str(uid)
        if uid_str not in users:
            users[uid_str] = {
                "id": uid,
                "username": username or "нет",
                "first_name": first_name or "Аноним",
                "joined": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "state": "IDLE",
                "temp": {},
                "ai_count": 0
            }
            cls.write(Config.FILES["users"], users)

            stats = cls.read(Config.FILES["stats"]) or {}
            today = datetime.now().strftime("%Y-%m-%d")
            stats["total_users"] = stats.get("total_users", 0) + 1
            stats["daily"] = stats.get("daily", {})
            stats["daily"][today] = stats["daily"].get(today, 0) + 1
            cls.write(Config.FILES["stats"], stats)

            logging.info(f"Новый пользователь: {uid} (@{username})")
            return True
        return False


# ──────────────────────────────────────────────────────────────────────────────
#  SECURITY
# ──────────────────────────────────────────────────────────────────────────────

class Security:
    @staticmethod
    def is_admin(uid):
        admins = DatabaseManager.read(Config.FILES["admins"]) or []
        return uid == Config.MAIN_ADMIN_ID or uid in admins

    @staticmethod
    def is_banned(uid):
        bans = DatabaseManager.read(Config.FILES["bans"]) or []
        return uid in bans


# ──────────────────────────────────────────────────────────────────────────────
#  FSM — машина состояний
# ──────────────────────────────────────────────────────────────────────────────

class FSM:
    @staticmethod
    def set(uid, state, data=None):
        users = DatabaseManager.read(Config.FILES["users"]) or {}
        uid_str = str(uid)
        if uid_str in users:
            users[uid_str]["state"] = state
            if data is not None:
                users[uid_str]["temp"] = data
            DatabaseManager.write(Config.FILES["users"], users)

    @staticmethod
    def get(uid):
        users = DatabaseManager.read(Config.FILES["users"]) or {}
        u = users.get(str(uid), {})
        return u.get("state", "IDLE"), u.get("temp", {})

    @staticmethod
    def reset(uid):
        FSM.set(uid, "IDLE", {})


# ──────────────────────────────────────────────────────────────────────────────
#  TELEGRAM API WRAPPER — с ретраями и защитой
# ──────────────────────────────────────────────────────────────────────────────

class TG:
    BASE = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/"

    @classmethod
    def api(cls, method, **kwargs):
        url = cls.BASE + method
        for attempt in range(Config.MAX_RETRIES):
            try:
                if "files" in kwargs:
                    r = requests.post(url, data=kwargs.get("data"), files=kwargs["files"], timeout=Config.REQUEST_TIMEOUT)
                else:
                    r = requests.post(url, json=kwargs, timeout=Config.REQUEST_TIMEOUT)

                data = r.json()
                if data.get("ok"):
                    return data
                if data.get("error_code") == 429:
                    retry_after = data.get("parameters", {}).get("retry_after", 2)
                    time.sleep(retry_after + 0.5)
                else:
                    logging.warning(f"TG API error: {data.get('description')}")
            except Exception as e:
                logging.error(f"TG request failed: {e}")
                time.sleep(1.1 ** attempt)

        logging.error(f"Max retries exceeded for {method}")
        return {"ok": False, "description": "max_retries"}


    @classmethod
    def send(cls, chat_id, text, **kwargs):
        payload = {
            "chat_id": chat_id,
            "text": text[:Config.MAX_MESSAGE_LENGTH],
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        payload.update(kwargs)
        return cls.api("sendMessage", **payload)


    @classmethod
    def photo(cls, chat_id, photo, caption=None, **kwargs):
        payload = {"chat_id": chat_id, "photo": photo}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"
        payload.update(kwargs)
        return cls.api("sendPhoto", **payload)


    @classmethod
    def delete(cls, chat_id, message_id):
        return cls.api("deleteMessage", chat_id=chat_id, message_id=message_id)


    @classmethod
    def action(cls, chat_id, action="typing"):
        return cls.api("sendChatAction", chat_id=chat_id, action=action)
    # ──────────────────────────────────────────────────────────────────────────────
#  GEMINI 2.5 FLASH-LITE WRAPPER
# ──────────────────────────────────────────────────────────────────────────────

class Gemini:
    @staticmethod
    def ask(prompt, image_b64=None, temperature=0.75, max_tokens=2048):
        stats = DatabaseManager.read(Config.FILES["stats"]) or {}
        stats["ai_requests"] = stats.get("ai_requests", 0) + 1
        today = datetime.now().strftime("%Y-%m-%d")
        stats["daily"] = stats.get("daily", {})
        stats["daily"][today] = stats["daily"].get(today, 0) + 1
        DatabaseManager.write(Config.FILES["stats"], stats)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"

        parts = [{"text": prompt}]
        if image_b64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_b64
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        try:
            r = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            resp = r.json()
            return resp["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logging.error(f"Gemini failed: {e}")
            # Fallback
            url = url.replace(Config.GEMINI_MODEL, Config.GEMINI_FALLBACK_MODEL)
            try:
                r = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except:
                return "🛑 Ошибка связи с нейросетью. Попробуй позже."


# ──────────────────────────────────────────────────────────────────────────────
#  КРАСИВЫЕ КЛАВИАТУРЫ
# ──────────────────────────────────────────────────────────────────────────────

class Keyboard:
    @staticmethod
    def main(is_admin=False):
        row1 = [{"text": "🧠 Задать вопрос Grok'у"}, {"text": "🎨 Сгенерировать арт"}]
        row2 = [{"text": "👤 Профиль"}, {"text": "📚 Помощь"}]
        kb = [row1, row2]
        if is_admin:
            kb.append([{"text": "🔧 АДМИНКА"}])
        return {"keyboard": kb, "resize_keyboard": True}

    @staticmethod
    def cancel():
        return {"keyboard": [[{"text": "❌ ОТМЕНА"}]], "resize_keyboard": True}

    @staticmethod
    def admin_inline():
        return [
            [{"text": "📢 Рассылка", "callback_data": "admin_broadcast"}],
            [{"text": "📊 Статистика", "callback_data": "admin_stats"}],
            [{"text": "👥 Юзеры (список)", "callback_data": "admin_users"}],
            [{"text": "🔍 Инфа по юзеру", "callback_data": "admin_userinfo"}],
            [{"text": "📜 Логи", "callback_data": "admin_logs"}]
        ]


# ──────────────────────────────────────────────────────────────────────────────
#  ПРОГРЕСС-БАР — максимально красивый
# ──────────────────────────────────────────────────────────────────────────────

class Progress:
    BARS = [
        "▏▏▏▏▏▏▏▏▏▏",
        "█▏▏▏▏▏▏▏▏▏",
        "██▏▏▏▏▏▏▏▏",
        "███▏▏▏▏▏▏▏",
        "████▏▏▏▏▏▏",
        "█████▏▏▏▏▏",
        "██████▏▏▏▏",
        "███████▏▏▏",
        "████████▏▏",
        "█████████▏",
        "██████████"
    ]

    @staticmethod
    def start(chat_id, title):
        msg = TG.send(chat_id, f"<b>⏳ {title}</b>\n<code>[          ] 0%</code>")
        return msg.get("result", {}).get("message_id")

    @staticmethod
    def update(chat_id, mid, percent):
        if not mid:
            return
        bar_idx = min(int(percent / 10), len(Progress.BARS) - 1)
        bar = Progress.BARS[bar_idx]
        TG.api("editMessageText", chat_id=chat_id, message_id=mid,
               text=f"<b>⏳ Обработка</b>\n<code>[{bar}] {percent}%</code>",
               parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
#  МЕДИА — скачивание фото
# ──────────────────────────────────────────────────────────────────────────────

class Media:
    @staticmethod
    def photo_to_b64(photo_array):
        if not photo_array:
            return None
        file_id = photo_array[-1]["file_id"]
        info = TG.api("getFile", file_id=file_id)
        if not info.get("ok"):
            return None
        path = info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{path}"
        try:
            r = requests.get(url, timeout=25)
            return base64.b64encode(r.content).decode("utf-8")
        except:
            return None


# ──────────────────────────────────────────────────────────────────────────────
#  РАССЫЛКА
# ──────────────────────────────────────────────────────────────────────────────

def broadcast(admin_id, message):
    users = DatabaseManager.read(Config.FILES["users"]) or {}
    text = message.get("text") or message.get("caption") or ""
    photo_id = message.get("photo", [{}])[-1].get("file_id") if "photo" in message else None

    success = 0
    total = len(users)
    mid = Progress.start(admin_id, f"Рассылка {total} юзерам")

    for i, uid_str in enumerate(users):
        uid = int(uid_str)
        percent = int((i + 1) / total * 100)
        Progress.update(admin_id, mid, percent)

        try:
            if photo_id:
                TG.photo(uid, photo_id, text)
            else:
                TG.send(uid, text)
            success += 1
        except:
            pass
        time.sleep(0.09)  # защита от бана

    TG.delete(admin_id, mid)
    TG.send(admin_id, f"✅ Рассылка завершена\nДоставлено: {success}/{total}")


# ──────────────────────────────────────────────────────────────────────────────
#  CALLBACK HANDLER
# ──────────────────────────────────────────────────────────────────────────────

def on_callback(cb):
    user_id = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    mid = cb["message"]["message_id"]
    data = cb["data"]

    if not Security.is_admin(user_id):
        return

    users_db = DatabaseManager.read(Config.FILES["users"]) or {}

    if data == "admin_broadcast":
        FSM.set(user_id, "BROADCAST")
        TG.send(chat_id, "Отправь сообщение (текст или фото) для рассылки", rkb=Keyboard.cancel())

    elif data == "admin_stats":
        st = DatabaseManager.read(Config.FILES["stats"]) or {}
        text = (
            f"<b>📊 Статистика TITAN</b>\n\n"
            f"👥 Всего пользователей: {st.get('total_users', 0)}\n"
            f"🧠 Запросов к ИИ: {st.get('ai_requests', 0)}\n"
            f"🎨 Сгенерировано артов: {st.get('images', 0)}\n"
            f"⚠️ Ошибок: {st.get('errors', 0)}"
        )
        TG.api("editMessageText", chat_id=chat_id, message_id=mid, text=text, parse_mode="HTML")

    elif data == "admin_users":
        lines = ["<b>Список пользователей (последние 25):</b>\n"]
        for uid_str, u in list(users_db.items())[-25:]:
            lines.append(f"• {u['first_name']} (@{u['username']}) — ID <code>{uid_str}</code>")
        text = "\n".join(lines)
        TG.api("editMessageText", chat_id=chat_id, message_id=mid, text=text, parse_mode="HTML")

    elif data == "admin_logs":
        TG.api("sendDocument", chat_id=chat_id, document=open(Config.FILES["log"], "rb"))


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN MESSAGE HANDLER
# ──────────────────────────────────────────────────────────────────────────────

def on_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = (msg.get("text") or msg.get("caption") or "").strip()

    DatabaseManager.register_user(user_id, msg["from"].get("username"), msg["from"].get("first_name"))

    if Security.is_banned(user_id):
        TG.send(chat_id, "🚫 Доступ ограничен")
        return

    state, temp = FSM.get(user_id)
    is_admin = Security.is_admin(user_id)

    # Отмена
    if text == "❌ ОТМЕНА":
        FSM.reset(user_id)
        TG.send(chat_id, "Действие отменено", rkb=Keyboard.main(is_admin))
        return

    # Состояния
    if state == "BROADCAST" and is_admin:
        broadcast(user_id, msg)
        FSM.reset(user_id)
        return

    if state in ("AI_PROMPT", "ART_PROMPT"):
        mid = Progress.start(chat_id, "Нейросеть думает...")
        img_b64 = Media.photo_to_b64(msg.get("photo", []))

        if state == "AI_PROMPT":
            answer = Gemini.ask(text or "Опиши это фото", img_b64)
        else:
            prompt = text or "красивый пейзаж в стиле киберпанк"
            answer = f"Генерирую арт...\nЗапрос: {prompt}"
            img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?model=flux&width=1024&height=1024&nologo=true"
            TG.photo(chat_id, img_url, f"🎨 Готово!\n\n{prompt}")
            stats = DatabaseManager.read(Config.FILES["stats"]) or {}
            stats["images"] = stats.get("images", 0) + 1
            DatabaseManager.write(Config.FILES["stats"], stats)

        if mid:
            TG.delete(chat_id, mid)
        TG.send(chat_id, answer or "🤔 Не понял запрос, попробуй по-другому", rkb=Keyboard.main(is_admin))
        FSM.reset(user_id)
        return

    # Главные кнопки
    if text == "🧠 Задать вопрос Grok'у":
        FSM.set(user_id, "AI_PROMPT")
        TG.send(chat_id, "✨ Пиши свой вопрос или присылай фото", rkb=Keyboard.cancel())

    elif text == "🎨 Сгенерировать арт":
        FSM.set(user_id, "ART_PROMPT")
        TG.send(chat_id, "Опиши, что хочешь увидеть (можно очень подробно)", rkb=Keyboard.cancel())

    elif text == "🔧 АДМИНКА" and is_admin:
        TG.send(chat_id, "🔐 Админ-панель", kb=Keyboard.admin_inline())

    elif text == "/start" or text == "🏠 Главное меню":
        welcome = Config.read(Config.FILES["settings"])["welcome_message"]
        TG.send(chat_id, welcome, rkb=Keyboard.main(is_admin))


# ──────────────────────────────────────────────────────────────────────────────
#  FLASK WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "TITAN V26.0 OMEGA • ACTIVE", 200

    try:
        update = request.json
        if not update:
            return "OK", 200

        if "callback_query" in update:
            on_callback(update["callback_query"])
        if "message" in update:
            on_message(update["message"])

    except Exception as e:
        logging.error(f"Webhook crash: {traceback.format_exc()}")
        DatabaseManager.write(Config.FILES["stats"], {"errors": DatabaseManager.read(Config.FILES["stats"]).get("errors", 0) + 1})

    return "OK", 200


if __name__ == "__main__":
    TitanLogger.setup()
    DatabaseManager.init()
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"🚀 Запуск на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
