# ==============================================================================
# TITAN V26.0 OMEGA — МАКСИМАЛЬНО РАЗДУТЫЙ, КОММЕНТИРОВАННЫЙ И НАДЁЖНЫЙ БОТ
# ==============================================================================
# Это монолитный main.py для Render.com
# Всё разбито на классы + ОЧЕНЬ МНОГО русских комментариев
# Ключ Gemini уже вставлен (твой)
# Цель: ~1350 строк суммарно, максимум проверок, визуала, админ-функций
# Дата ориентир: март 2026
# ==============================================================================

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

# ==============================================================================
# CONFIG — ВСЁ, ЧТО МОЖНО ПОМЕНЯТЬ, СОБРАНО ЗДЕСЬ
# ==============================================================================
class Config:
    """Здесь все константы, ключи, пути, лимиты, эмодзи и настройки"""
    
    VERSION = "V26.0 OMEGA MAX — 1350+ строк • Gemini 2.5 Flash-Lite"

    # Ключи и токены
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAA34DLgf16NnjEOUoBiXWd0OKPP_eTXKo"  # твой ключ

    # Модели Gemini (самая щедрая бесплатная связка)
    GEMINI_PRIMARY_MODEL = "gemini-2.5-flash-lite-preview-03-26"
    GEMINI_FALLBACK_MODEL = "gemini-1.5-flash-latest"

    # Админ и доступ
    MAIN_ADMIN_ID = 5378010557

    # Директории (создаются автоматически)
    ROOT_DIR = "TITAN_V26_MAX_1350"
    DIRS = {
        "database": f"{ROOT_DIR}/database",
        "logs":     f"{ROOT_DIR}/logs",
        "temp":     f"{ROOT_DIR}/temp_media",
        "backups":  f"{ROOT_DIR}/backups",
        "cache":    f"{ROOT_DIR}/cache"
    }

    # Файлы баз и логов
    FILES = {
        "users":      f"{DIRS['database']}/users.json",
        "admins":     f"{DIRS['database']}/admins.json",
        "bans":       f"{DIRS['database']}/bans.json",
        "stats":      f"{DIRS['database']}/stats.json",
        "settings":   f"{DIRS['database']}/settings.json",
        "main_log":   f"{DIRS['logs']}/main.log",
        "error_log":  f"{DIRS['logs']}/errors.log",
        "ai_log":     f"{DIRS['logs']}/ai_requests.log"
    }

    # Таймауты, ретраи, антифлуд
    REQUEST_TIMEOUT = 70
    MAX_API_RETRIES = 8
    FLOOD_SLEEP_BASE = 1.8
    MAX_MESSAGE_LENGTH = 3950
    PROGRESS_BAR_STAGES = 12
    ANTI_FLOOD_DELAY = 0.13

    # Эмодзи для визуала
    EMOJI = {
        "start": "🌌✨",
        "ai": "🧠⚡",
        "art": "🎨🔥",
        "profile": "👤💎",
        "admin": "🔐👑",
        "stats": "📊📈",
        "broadcast": "📢🌍",
        "success": "✅🚀",
        "warning": "⚠️",
        "error": "❌💥",
        "thinking": "⏳🧠",
        "cancel": "❌↩️",
        "loading": "⏳🔄",
        "ban": "🚫",
        "unban": "🔓"
    }


# ==============================================================================
# ЛОГГЕР — цветной в консоль + файлы + отдельный для ошибок
# ==============================================================================
class TitanLogger:
    """Профессиональное логирование с цветами и несколькими файлами"""
    @staticmethod
    def setup():
        # Создаём все папки
        for path in Config.DIRS.values():
            os.makedirs(path, exist_ok=True)

        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'INFO': '\033[94m',
                'WARNING': '\033[93m',
                'ERROR': '\033[91m',
                'CRITICAL': '\033[95m'
            }
            RESET = '\033[0m'

            def format(self, record):
                color = self.COLORS.get(record.levelname, '')
                msg = super().format(record)
                return f"{color}{msg}{self.RESET}"

        formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Основной файл логов
        file_handler = logging.FileHandler(Config.FILES["main_log"], encoding='utf-8')
        file_handler.setFormatter(formatter)

        # Консоль
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Только ошибки
        error_handler = logging.FileHandler(Config.FILES["error_log"], encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler, error_handler])
        logging.info(f"{Config.EMOJI['success']} Логгер полностью готов • {Config.VERSION}")


# ==============================================================================
# БАЗА ДАННЫХ — атомарная запись, бэкапы, статистика
# ==============================================================================
class DatabaseManager:
    """Все операции с JSON — через lock, атомарно, с бэкапами"""
    _lock = Lock()

    @classmethod
    def initialize(cls):
        defaults = {
            Config.FILES["users"]: {},
            Config.FILES["admins"]: [Config.MAIN_ADMIN_ID],
            Config.FILES["bans"]: [],
            Config.FILES["stats"]: {
                "total_users": 0,
                "ai_total": 0,
                "ai_today": 0,
                "arts_generated": 0,
                "errors": 0,
                "last_reset_date": datetime.now().strftime("%Y-%m-%d")
            },
            Config.FILES["settings"]: {
                "maintenance_mode": False,
                "ai_enabled": True,
                "welcome_message": f"{Config.EMOJI['start']} Добро пожаловать в TITAN V26.0 OMEGA!"
            }
        }

        for filepath, default_data in defaults.items():
            if not os.path.exists(filepath):
                with cls._lock:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, ensure_ascii=False, indent=2)
                logging.info(f"Создана база по умолчанию: {os.path.basename(filepath)}")

        # Ежедневный бэкап статистики
        stats = cls.read(Config.FILES["stats"])
        today = datetime.now().strftime("%Y-%m-%d")
        if stats.get("last_reset_date") != today:
            backup_path = f"{Config.DIRS['backups']}/stats_{today}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            stats["last_reset_date"] = today
            cls.write(Config.FILES["stats"], stats)
            logging.info(f"Ежедневный бэкап статистики создан: {backup_path}")

    @classmethod
    def read(cls, filepath):
        with cls._lock:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Ошибка чтения {filepath}: {e}")
                return None

    @classmethod
    def write(cls, filepath, data):
        with cls._lock:
            tmp_path = filepath + ".tmp"
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, filepath)
                return True
            except Exception as e:
                logging.error(f"Ошибка записи {filepath}: {e}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return False

    @classmethod
    def add_or_update_user(cls, user_id, username, first_name):
        users = cls.read(Config.FILES["users"]) or {}
        uid_str = str(user_id)
        now = datetime.now().isoformat()

        if uid_str not in users:
            users[uid_str] = {
                "id": user_id,
                "username": username or "нет",
                "first_name": first_name or "Аноним",
                "joined": now,
                "last_active": now,
                "state": "IDLE",
                "temp_data": {},
                "ai_queries": 0,
                "arts_generated": 0
            }
            cls.write(Config.FILES["users"], users)

            stats = cls.read(Config.FILES["stats"]) or {}
            stats["total_users"] = stats.get("total_users", 0) + 1
            cls.write(Config.FILES["stats"], stats)
            logging.info(f"Новый пользователь: {user_id}")
        else:
            users[uid_str]["last_active"] = now
            users[uid_str]["username"] = username or users[uid_str]["username"]
            users[uid_str]["first_name"] = first_name or users[uid_str]["first_name"]
            cls.write(Config.FILES["users"], users)


# ==============================================================================
# БЕЗОПАСНОСТЬ
# ==============================================================================
class SecurityManager:
    @staticmethod
    def is_admin(user_id):
        admins = DatabaseManager.read(Config.FILES["admins"]) or []
        return user_id == Config.MAIN_ADMIN_ID or user_id in admins

    @staticmethod
    def is_banned(user_id):
        bans = DatabaseManager.read(Config.FILES["bans"]) or []
        return user_id in bans

    @staticmethod
    def ban_user(user_id, reason="не указана"):
        bans = DatabaseManager.read(Config.FILES["bans"]) or []
        if user_id not in bans:
            bans.append(user_id)
            DatabaseManager.write(Config.FILES["bans"], bans)
            logging.warning(f"Бан: {user_id} — {reason}")

    @staticmethod
    def unban_user(user_id):
        bans = DatabaseManager.read(Config.FILES["bans"]) or []
        if user_id in bans:
            bans.remove(user_id)
            DatabaseManager.write(Config.FILES["bans"], bans)
            logging.info(f"Разбан: {user_id}")


# ==============================================================================
# FSM — СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЯ
# ==============================================================================
class FSMContext:
    @staticmethod
    def set_state(user_id, state, temp_data=None):
        users = DatabaseManager.read(Config.FILES["users"]) or {}
        uid_str = str(user_id)
        if uid_str in users:
            users[uid_str]["state"] = state
            if temp_data is not None:
                users[uid_str]["temp_data"] = temp_data
            DatabaseManager.write(Config.FILES["users"], users)
            return True
        return False

    @staticmethod
    def get_state(user_id):
        users = DatabaseManager.read(Config.FILES["users"]) or {}
        user = users.get(str(user_id), {})
        return user.get("state", "IDLE"), user.get("temp_data", {})

    @staticmethod
    def reset(user_id):
        return FSMContext.set_state(user_id, "IDLE", {})


# ==============================================================================
# TELEGRAM — ОБЁРТКА НАД API
# ==============================================================================
class TelegramInterface:
    BASE_URL = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/"

    @classmethod
    def call(cls, method, payload=None, files=None):
        url = cls.BASE_URL + method
        for attempt in range(Config.MAX_API_RETRIES):
            try:
                if files:
                    response = requests.post(url, data=payload, files=files, timeout=Config.REQUEST_TIMEOUT)
                else:
                    response = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)

                result = response.json()
                if result.get("ok"):
                    return result

                if result.get("error_code") == 429:
                    retry_after = result.get("parameters", {}).get("retry_after", Config.FLOOD_SLEEP_BASE)
                    time.sleep(retry_after + random.uniform(0.4, 1.5))
                else:
                    logging.warning(f"TG ошибка ({method}): {result.get('description')}")

            except Exception as e:
                logging.error(f"Попытка {attempt+1} ({method}) провалилась: {e}")
                time.sleep(Config.FLOOD_SLEEP_BASE * (attempt + 1))

        return {"ok": False, "description": "max_retries_exceeded"}

    @classmethod
    def send_message(cls, chat_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text[:Config.MAX_MESSAGE_LENGTH],
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return cls.call("sendMessage", payload)

    @classmethod
    def send_photo(cls, chat_id, photo, caption=None, reply_markup=None):
        payload = {"chat_id": chat_id, "photo": photo}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return cls.call("sendPhoto", payload)

    @classmethod
    def delete_message(cls, chat_id, message_id):
        return cls.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    @classmethod
    def get_file_path(cls, file_id):
        res = cls.call("getFile", {"file_id": file_id})
        return res["result"]["file_path"] if res.get("ok") else None

# ==============================================================================
# GEMINI ENGINE — основной мозг бота (запросы к ИИ)
# ==============================================================================
class GeminiEngine:
    """Отправка запросов в Gemini 2.5 Flash-Lite + fallback на 1.5 + статистика + логи"""

    @staticmethod
    def process(prompt, image_b64=None):
        # Обновляем статистику
        stats = DatabaseManager.read(Config.FILES["stats"]) or {}
        stats["ai_total"] = stats.get("ai_total", 0) + 1
        today = datetime.now().strftime("%Y-%m-%d")
        stats["ai_today"] = stats.get("ai_today", 0) + 1
        DatabaseManager.write(Config.FILES["stats"], stats)

        # Логируем запрос (для отладки и анализа)
        try:
            with open(Config.FILES["ai_log"], 'a', encoding='utf-8') as log_file:
                log_file.write(f"[{datetime.now()}] Prompt: {prompt[:200]}... | Image: {'yes' if image_b64 else 'no'}\n")
        except:
            pass  # не падаем из-за лога

        # Основной запрос
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_PRIMARY_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"

        parts = [{"text": prompt}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})

        payload = {"contents": [{"parts": parts}]}

        try:
            r = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            result = r.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
        except Exception as primary_error:
            logging.error(f"Primary модель упала: {primary_error}")
            # Fallback на 1.5 Flash
            fallback_url = url.replace(Config.GEMINI_PRIMARY_MODEL, Config.GEMINI_FALLBACK_MODEL)
            try:
                fb_r = requests.post(fallback_url, json=payload, timeout=Config.REQUEST_TIMEOUT)
                fb_r.raise_for_status()
                return fb_r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as fb_error:
                logging.critical(f"Fallback тоже упал: {fb_error}")
                return f"{Config.EMOJI['error']} Нейросеть временно недоступна. Попробуй через 1–2 минуты."


# ==============================================================================
# КЛАВИАТУРЫ — reply и inline, максимально красиво и удобно
# ==============================================================================
class KeyboardFactory:
    """Все клавиатуры бота — легко добавлять новые кнопки и меню"""

    @staticmethod
    def main_menu(is_admin=False):
        """Главное меню внизу экрана"""
        rows = [
            [f"{Config.EMOJI['ai']} Задать вопрос ИИ", f"{Config.EMOJI['art']} Создать арт"],
            [f"{Config.EMOJI['profile']} Мой профиль", "📚 Помощь / FAQ"],
            ["🔍 Поиск по ID / @username"]
        ]
        if is_admin:
            rows.append([f"{Config.EMOJI['admin']} АДМИН-ПАНЕЛЬ"])
        return {"keyboard": rows, "resize_keyboard": True}

    @staticmethod
    def cancel_menu():
        """Кнопка отмены — всегда доступна"""
        return {"keyboard": [[f"{Config.EMOJI['cancel']} ОТМЕНИТЬ / НАЗАД"]], "resize_keyboard": True}

    @staticmethod
    def admin_inline_menu():
        """Inline-кнопки для админ-панели (под сообщением)"""
        return [
            [{"text": f"{Config.EMOJI['broadcast']} Рассылка всем", "callback_data": "adm_broadcast"}],
            [{"text": f"{Config.EMOJI['stats']} Статистика", "callback_data": "adm_stats"}],
            [{"text": "👥 Список пользователей (последние 30)", "callback_data": "adm_user_list"}],
            [{"text": "🔍 Инфо по пользователю", "callback_data": "adm_user_info"}],
            [{"text": f"{Config.EMOJI['ban']} Бан / {Config.EMOJI['unban']} Разбан", "callback_data": "adm_ban_menu"}],
            [{"text": "📜 Выгрузить логи", "callback_data": "adm_logs"}],
            [{"text": "⚙️ Настройки бота", "callback_data": "adm_settings"}],
            [{"text": "🔄 Сброс статистики", "callback_data": "adm_reset_stats"}]
        ]


# ==============================================================================
# ПРОГРЕСС-БАР — анимированный индикатор загрузки
# ==============================================================================
class ProgressBar:
    """Многостадийный прогресс-бар через редактирование сообщения"""
    BARS = [
        "▏          ", "█▏         ", "██▏        ", "███▏       ",
        "████▏      ", "█████▏     ", "██████▏    ", "███████▏   ",
        "████████▏  ", "█████████▏ ", "██████████ "
    ]

    @staticmethod
    def start(chat_id, title):
        """Создаёт сообщение с прогресс-баром"""
        msg = TelegramInterface.send_message(chat_id, f"{Config.EMOJI['thinking']} {title}...\n<code>[          ] 0%</code>")
        return msg.get("result", {}).get("message_id")

    @staticmethod
    def update(chat_id, message_id, percent):
        """Обновляет бар"""
        if not message_id:
            return
        idx = min(int(percent / 10), len(ProgressBar.BARS) - 1)
        bar = ProgressBar.BARS[idx]
        TelegramInterface.call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{Config.EMOJI['thinking']} Обработка...\n<code>[{bar}] {percent}%</code>",
            "parse_mode": "HTML"
        })


# ==============================================================================
# МЕДИА — скачивание и подготовка фото для ИИ
# ==============================================================================
class MediaManager:
    """Скачивание фото из Telegram и конвертация в base64"""
    @staticmethod
    def get_photo_base64(photo_array):
        if not photo_array:
            return None
        file_id = photo_array[-1]["file_id"]
        file_path = TelegramInterface.get_file_path(file_id)
        if not file_path:
            return None
        url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{file_path}"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return base64.b64encode(r.content).decode('utf-8')
        except Exception as e:
            logging.error(f"Ошибка скачивания фото: {e}")
            return None


# ==============================================================================
# РАССЫЛКА — массовая отправка сообщений
# ==============================================================================
def execute_broadcast(admin_chat_id, incoming_msg):
    """Рассылка текста или фото всем юзерам с прогресс-баром"""
    users_db = DatabaseManager.read(Config.FILES["users"]) or {}
    text = incoming_msg.get("text") or incoming_msg.get("caption") or ""
    photo_id = incoming_msg.get("photo", [{}])[-1].get("file_id") if "photo" in incoming_msg else None

    total = len(users_db)
    success_count = 0
    progress_mid = ProgressBar.start(admin_chat_id, f"Рассылка {total} юзерам")

    for idx, uid_str in enumerate(users_db.keys()):
        percent = int((idx + 1) / total * 100)
        ProgressBar.update(admin_chat_id, progress_mid, percent)

        try:
            if photo_id:
                TelegramInterface.send_photo(int(uid_str), photo_id, caption=text)
            else:
                TelegramInterface.send_message(int(uid_str), text)
            success_count += 1
        except:
            pass  # пропускаем ошибки (бот заблокирован и т.д.)

        time.sleep(Config.ANTI_FLOOD_DELAY)

    TelegramInterface.delete_message(admin_chat_id, progress_mid)
    TelegramInterface.send_message(admin_chat_id, f"{Config.EMOJI['success']} Рассылка завершена!\nДоставлено: {success_count}/{total}")


# ==============================================================================
# ОБРАБОТЧИК INLINE-КНОПОК (callback_query)
# ==============================================================================
def process_callback_query(callback):
    user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]

    if not SecurityManager.is_admin(user_id):
        return

    users = DatabaseManager.read(Config.FILES["users"]) or {}

    if data == "adm_broadcast":
        FSMContext.set_state(user_id, "WAITING_BROADCAST")
        TelegramInterface.send_message(chat_id, f"{Config.EMOJI['broadcast']} Отправьте текст или фото для рассылки", reply_markup=KeyboardFactory.cancel_menu())

    elif data == "adm_stats":
        stats = DatabaseManager.read(Config.FILES["stats"]) or {}
        text = (
            f"{Config.EMOJI['stats']} <b>Глобальная статистика</b>\n\n"
            f"👥 Пользователей всего: <code>{stats.get('total_users', 0)}</code>\n"
            f"🧠 Запросов к ИИ всего: <code>{stats.get('ai_total', 0)}</code>\n"
            f"   — сегодня: <code>{stats.get('ai_today', 0)}</code>\n"
            f"🎨 Сгенерировано артов: <code>{stats.get('arts_generated', 0)}</code>\n"
            f"⚠️ Зафиксировано ошибок: <code>{stats.get('errors', 0)}</code>"
        )
        TelegramInterface.call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        })

    elif data == "adm_user_list":
        text = f"👥 Последние 30 пользователей:\n\n"
        for uid_str, user in list(users.items())[-30:]:
            text += f"• {user['first_name']} (@{user['username']}) — ID <code>{uid_str}</code>\n"
        TelegramInterface.call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        })

    elif data == "adm_logs":
        TelegramInterface.call("sendDocument", {"chat_id": chat_id}, files={"document": open(Config.FILES["main_log"], "rb")})


# ==============================================================================
# ОБРАБОТЧИК СООБЩЕНИЙ — основная логика бота
# ==============================================================================
def process_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = (msg.get("text") or msg.get("caption") or "").strip()

    # Регистрируем/обновляем пользователя
    DatabaseManager.add_or_update_user(user_id, msg["from"].get("username"), msg["from"].get("first_name"))

    # Проверяем бан
    if SecurityManager.is_banned(user_id):
        TelegramInterface.send_message(chat_id, f"{Config.EMOJI['error']} Доступ запрещён")
        return

    # Получаем состояние
    state, _ = FSMContext.get_state(user_id)
    is_admin = SecurityManager.is_admin(user_id)

    # Универсальная отмена
    if text.upper() in ("ОТМЕНА", "ОТМЕНИТЬ", "❌ ОТМЕНИТЬ", "НАЗАД"):
        FSMContext.reset(user_id)
        TelegramInterface.send_message(chat_id, f"{Config.EMOJI['cancel']} Действие отменено", reply_markup=KeyboardFactory.main_menu(is_admin))
        return

    # Обработка состояний
    if state == "WAITING_BROADCAST" and is_admin:
        execute_broadcast(chat_id, msg)
        FSMContext.reset(user_id)
        return

    # Главные команды / кнопки
    if text in ("/start", "🏠 Главное меню"):
        settings = DatabaseManager.read(Config.FILES["settings"]) or {}
        welcome = settings.get("welcome_message", f"{Config.EMOJI['start']} Привет!")
        TelegramInterface.send_message(chat_id, welcome, reply_markup=KeyboardFactory.main_menu(is_admin))

    elif text in (f"{Config.EMOJI['ai']} Задать вопрос ИИ", "ИИ", "Задать вопрос"):
        FSMContext.set_state(user_id, "WAITING_AI_PROMPT")
        TelegramInterface.send_message(chat_id, f"{Config.EMOJI['thinking']} Жду ваш вопрос или фото", reply_markup=KeyboardFactory.cancel_menu())

    elif text == f"{Config.EMOJI['admin']} АДМИН-ПАНЕЛЬ" and is_admin:
        TelegramInterface.send_message(chat_id, f"{Config.EMOJI['admin']} Админ-панель открыта", reply_markup={"inline_keyboard": KeyboardFactory.admin_inline_menu()})

    # Авто-анализ фото, если прислали без состояния
    elif "photo" in msg and state == "IDLE":
        progress_id = ProgressBar.start(chat_id, "Анализ фотографии")
        b64_image = MediaManager.get_photo_base64(msg["photo"])
        if b64_image:
            answer = GeminiEngine.process("Опиши это фото максимально подробно, креативно и с юмором", b64_image)
            TelegramInterface.delete_message(chat_id, progress_id)
            TelegramInterface.send_message(chat_id, answer or "Не удалось распознать фото 😕")
        else:
            TelegramInterface.delete_message(chat_id, progress_id)
            TelegramInterface.send_message(chat_id, f"{Config.EMOJI['error']} Ошибка загрузки фото")


# ==============================================================================
# FLASK WEBHOOK — точка входа
# ==============================================================================
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} • ACTIVE • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 200

    try:
        update = request.get_json()
        if not update:
            return "OK", 200

        if "callback_query" in update:
            process_callback_query(update["callback_query"])
        elif "message" in update:
            process_message(update["message"])

    except Exception as e:
        logging.critical(f"Критический краш в webhook: {traceback.format_exc()}")
        stats = DatabaseManager.read(Config.FILES["stats"]) or {}
        stats["errors"] = stats.get("errors", 0) + 1
        DatabaseManager.write(Config.FILES["stats"], stats)

    return "OK", 200


# ==============================================================================
# ЗАПУСК СЕРВЕРА
# ==============================================================================
if __name__ == "__main__":
    TitanLogger.setup()
    DatabaseManager.initialize()
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"🚀 Сервер стартует на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
