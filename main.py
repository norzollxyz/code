"""
==============================================================================
ПРОЕКТ: TITAN AI - V26.0 (PROFILE, ACTIONS & COMMANDS)
АРХИТЕКТУРА: PRO-LEVEL (Многопоточность, ООП, Защита от сбоев)
ЧАСТЬ 1: ЯДРО СИСТЕМЫ, ЛОГИРОВАНИЕ И РАБОТА С ФАЙЛАМИ
==============================================================================
"""

import os
import sys
import json
import time
import base64
import random
import logging
import threading
import traceback
from datetime import datetime
from threading import Lock
import requests
from flask import Flask, request, jsonify

# ==============================================================================
# ⚙️ MODULE 1: СИСТЕМНАЯ КОНФИГУРАЦИЯ (CONFIG MANAGER)
# ==============================================================================

class Config:
    """Глобальный класс настроек проекта V26.0"""
    VERSION = "V26.0 (PROFILE, ACTIONS & COMMANDS)"
    
    # Ключи доступа (ВНИМАНИЕ: в рабочих проектах их прячут в .env)
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    
    # Права доступа
    MAIN_ADMIN_ID = 5378010557 # ТВОЙ ID
    
    # Настройки сети и таймаутов
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Файловая система
    ROOT_DIR = "V26_DATA_VAULT"
    DIRS = {
        "db": f"{ROOT_DIR}/database",
        "logs": f"{ROOT_DIR}/logs",
        "temp": f"{ROOT_DIR}/temp_media",
        "backups": f"{ROOT_DIR}/backups"
    }
    
    # Файлы данных
    FILES = {
        "users": f"{DIRS['db']}/users_db.json",
        "admins": f"{DIRS['db']}/admins_db.json",
        "bans": f"{DIRS['db']}/ban_list.json",
        "stats": f"{DIRS['db']}/system_stats.json",
        "settings": f"{DIRS['db']}/bot_settings.json",
        "log": f"{DIRS['logs']}/titan_v26.log"
    }

# ==============================================================================
# 📝 MODULE 2: ПРОДВИНУТАЯ СИСТЕМА ЛОГИРОВАНИЯ (ADVANCED LOGGER)
# ==============================================================================

class TitanLogger:
    """Кастомный логгер для отслеживания всех процессов в боте"""
    
    @staticmethod
    def setup():
        # Создаем директории, если их нет
        for path in Config.DIRS.values():
            if not os.path.exists(path):
                os.makedirs(path)
                
        # Настраиваем формат логов
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s",
            handlers=[
                logging.FileHandler(Config.FILES["log"], encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.info(f"🚀 СИСТЕМА ИНИЦИАЛИЗИРОВАНА: {Config.VERSION}")

    @staticmethod
    def info(msg): logging.info(msg)
    
    @staticmethod
    def warning(msg): logging.warning(msg)
    
    @staticmethod
    def error(msg, exc_info=False): logging.error(msg, exc_info=exc_info)
    
    @staticmethod
    def critical(msg): logging.critical(f"🔥 CRITICAL: {msg}")

# ==============================================================================
# 💾 MODULE 3: МЕНЕДЖЕР БАЗЫ ДАННЫХ (THREAD-SAFE DB MANAGER)
# ==============================================================================

class DatabaseManager:
    """Безопасная работа с JSON базами данных с блокировками потоков (Lock)"""
    _lock = Lock() # Защита от одновременной записи разными юзерами

    @classmethod
    def initialize_databases(cls):
        """Создает пустые базы данных, если сервер был перезагружен"""
        with cls._lock:
            defaults = {
                Config.FILES["users"]: {}, # {chat_id: {"username": str, "joined": date, "role": str}}
                Config.FILES["admins"]: [Config.MAIN_ADMIN_ID],
                Config.FILES["bans"]: [],
                Config.FILES["stats"]: {"messages_total": 0, "ai_requests": 0, "images_generated": 0, "errors": 0},
                Config.FILES["settings"]: {"maintenance_mode": False, "ai_enabled": True}
            }
            
            for filepath, default_data in defaults.items():
                if not os.path.exists(filepath):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, ensure_ascii=False, indent=4)
            TitanLogger.info("✅ Базы данных проверены и готовы к работе.")

    @classmethod
    def read(cls, filepath):
        """Безопасное чтение файла"""
        with cls._lock:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                TitanLogger.error(f"Ошибка чтения {filepath}: {e}")
                return None

    @classmethod
    def write(cls, filepath, data):
        """Безопасная запись в файл"""
        with cls._lock:
            try:
                # Сначала пишем во временный файл, потом переименовываем (защита от краша при записи)
                temp_file = filepath + ".tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                os.replace(temp_file, filepath)
                return True
            except Exception as e:
                TitanLogger.error(f"Ошибка записи {filepath}: {e}")
                return False

    @classmethod
    def add_user(cls, chat_id, username, first_name):
        """Регистрация нового пользователя (PROFILE)"""
        users = cls.read(Config.FILES["users"])
        chat_id_str = str(chat_id)
        
        if chat_id_str not in users:
            users[chat_id_str] = {
                "id": chat_id,
                "username": username or "Unknown",
                "name": first_name or "User",
                "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "state": "IDLE", # Для машины состояний (ACTIONS & COMMANDS)
                "temp_data": {}
            }
            cls.write(Config.FILES["users"], users)
            TitanLogger.info(f"👤 НОВЫЙ ПОЛЬЗОВАТЕЛЬ: {chat_id} ({first_name})")
            return True
        return False

# ==============================================================================
# 🛡️ MODULE 4: СИСТЕМА БЕЗОПАСНОСТИ (SECURITY & PERMISSIONS)
# ==============================================================================

class SecurityManager:
    """Управление доступом, банами и режимом тех. работ"""
    
    @staticmethod
    def is_admin(chat_id):
        if chat_id == Config.MAIN_ADMIN_ID:
            return True
        admins = DatabaseManager.read(Config.FILES["admins"])
        return chat_id in admins if admins else False

    @staticmethod
    def is_banned(chat_id):
        bans = DatabaseManager.read(Config.FILES["bans"])
        return chat_id in bans if bans else False
        
    @staticmethod
    def ban_user(chat_id):
        bans = DatabaseManager.read(Config.FILES["bans"])
        if chat_id not in bans:
            bans.append(chat_id)
            DatabaseManager.write(Config.FILES["bans"], bans)
            TitanLogger.warning(f"🔨 ПОЛЬЗОВАТЕЛЬ {chat_id} ПОЛУЧИЛ БАН.")
            return True
        return False

    @staticmethod
    def check_access(chat_id):
        """Комплексная проверка перед выполнением любого ACTIONS"""
        settings = DatabaseManager.read(Config.FILES["settings"])
        
        if SecurityManager.is_banned(chat_id):
            return {"status": False, "reason": "BANNED"}
            
        if settings.get("maintenance_mode", False) and not SecurityManager.is_admin(chat_id):
            return {"status": False, "reason": "MAINTENANCE"}
            
        return {"status": True, "reason": "OK"}

# ==============================================================================
# ИНИЦИАЛИЗАЦИЯ ПЕРЕД СТАРТОМ FLASK
# ==============================================================================
TitanLogger.setup()
DatabaseManager.initialize_databases()

app = Flask(__name__)

# КОНЕЦ ЧАСТИ 1. ОЖИДАНИЕ СЛЕДУЮЩИХ МОДУЛЕЙ...
       rk = {
            "keyboard": [
                [{"text": "🚀 Как пользоваться?"}, {"text": "👤 Мой профиль"}],
                [{"text": "💎 Premium возможности"}, {"text": "👨‍💻 Связь с создателем"}]
            ],
            "resize_keyboard": True
        }
        send_tg(chat_id, welcome, reply_kb=rk)
        return "OK", 200

    # --- КНОПКИ ПОЛЬЗОВАТЕЛЯ ---
    if text == "🚀 Как пользоваться?":
        cmd_txt = (
            "🛠 <b>СПРАВОЧНИК КОМАНД:</b>\n\n"
            "🖼 <b>Генерация картинок:</b>\n"
            "Напишите слово <code>Нарисуй</code> и ваш запрос.\n"
            "<i>Пример: Нарисуй киберпанк город под дождем</i>\n\n"
            "🎤 <b>Голосовые и Фото:</b>\n"
            "Просто отправьте файл, и я его проанализирую."
        )
        send_tg(chat_id, cmd_txt)
        return "OK", 200

    if text == "👤 Мой профиль":
        role = "👑 Создатель (Admin)" if chat_id == ADMIN_ID else "Пользователь"
        prof = f"👤 <b>ЛИЧНЫЙ КАБИНЕТ</b>\n━━━━━━━━━━━━━━\n🆔 Ваш ID: <code>{chat_id}</code>\n🛡 Ваш статус: <b>{role}</b>\n⚡️ Доступ: Открыт"
        send_tg(chat_id, prof)
        return "OK", 200
        
    if text == "💎 Premium возможности" or text == "👨‍💻 Связь с создателем":
        send_tg(chat_id, "💬 По всем вопросам и предложениям обращайтесь к администратору проекта.")
        return "OK", 200

    # --- АДМИНСКИЙ ВХОД И РАССЫЛКА ---
    if chat_id == ADMIN_ID:
        if text == "/admin":
            send_tg(chat_id, "👑 <b>TITAN MAX ОСНОВНАЯ ПАНЕЛЬ</b>\nВыберите модуль:", kb=get_admin_menu("main"))
            return "OK", 200
            
        if ADMIN_STATE.get(chat_id) == "waiting_broadcast":
            with open(USERS_FILE, "r") as f: users = f.read().splitlines()
            h = {}
            for u in users:
                try:
                    res = send_tg(u, text=caption, photo=msg["photo"][-1]["file_id"]) if "photo" in msg else send_tg(u, text)
                    if res.get("ok"): h[u] = res["result"]["message_id"]
                except: continue
            with open(BC_HISTORY, "w") as f: json.dump(h, f)
            send_tg(ADMIN_ID, f"✅ <b>Рассылка успешно доставлена {len(h)} юзерам.</b>")
            ADMIN_STATE.clear()
            return "OK", 200

    # --- НЕЙРОСЕТЕВАЯ ОБРАБОТКА ЗАПРОСОВ ---
    if text or "photo" in msg or "voice" in msg:
        lower_req = full_text.lower()
        
        # 1. ГЕНЕРАЦИЯ КАРТИНОК (РОУТИНГ АДМИНУ)
        if any(w in lower_req for w in ["нарисуй", "сгенерируй", "draw", "create"]):
            send_action(chat_id, "upload_photo")
            mid = titan_progress(chat_id, "СИНТЕЗ ИЗОБРАЖЕНИЯ")
            
            p = lower_req
            for w in ["нарисуй", "сгенерируй", "draw", "create"]: p = p.replace(w, "")
            prompt = p.strip() or "epic beautiful masterpiece"
            
            img_url = f"https://image.pollinations.ai/prompt/{prompt}?nologo=true&width=1024&height=1024"
            SYS_STATS["images_generated"] += 1
            
            if mid: delete_tg(chat_id, mid)
            
            # ВАЖНО: Отправка только админу
            if chat_id != ADMIN_ID:
                send_tg(ADMIN_ID, f"🔔 <b>ЗАКАЗ АРТА ОТ {chat_id}:</b>\n<i>{prompt}</i>")
            send_tg(ADMIN_ID, f"✨ <b>РЕЗУЛЬТАТ ГЕНЕРАЦИИ:</b>", photo=img_url)
            
            if chat_id != ADMIN_ID:
                send_tg(chat_id, "✅ <b>Изображение успешно сгенерировано и отправлено на проверку администратору.</b>")
            return "OK", 200

        # 2. АНАЛИЗ GEMINI (ТЕКСТ/ФОТО/ГОЛОС)
        send_action(chat_id, "typing")
        mid = titan_progress(chat_id, "НЕЙРОСЕТЕВОЙ АНАЛИЗ")
        
        img_b64, voice_b64 = None, None
        
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            fp = api_call("getFile", {"file_id": fid}).get("result", {}).get("file_path")
            if fp: img_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
            
        if "voice" in msg:
            send_action(chat_id, "record_voice")
            fid = msg["voice"]["file_id"]
            fp = api_call("getFile", {"file_id": fid}).get("result", {}).get("file_path")
            if fp: voice_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')

        ans = get_ai(text or caption or "Опиши этот файл в деталях", img_b64=img_b64, voice_b64=voice_b64)
        
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, ans)

    return "OK", 200

# ==========================================
# 🚀 ЗАПУСК СЕРВЕРА (RENDER STABILITY)
# ==========================================
if __name__ == "__main__":
    # Гарантированный захват порта для хостинга Render
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 СИСТЕМА TITAN ЗАПУСКАЕТСЯ НА ПОРТУ {port}...")
    app.run(host='0.0.0.0', port=port)


# ==============================================================================
# 📡 MODULE 5: ТЕЛЕГРАМ-ИНТЕРФЕЙС УЛЬТИМАТИВНОГО УРОВНЯ (TG_WRAPPER)
# ==============================================================================

class TelegramInterface:
    """Универсальный контроллер для работы с Telegram API с защитой от спама и ошибок"""
    BASE_URL = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/"

    @classmethod
    def call(cls, method, payload=None, files=None):
        """Единая точка входа для всех запросов с автоматическими повторами"""
        url = cls.BASE_URL + method
        for attempt in range(Config.MAX_RETRIES):
            try:
                if files:
                    response = requests.post(url, data=payload, files=files, timeout=Config.REQUEST_TIMEOUT)
                else:
                    response = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
                
                result = response.json()
                if result.get("ok"):
                    return result
                TitanLogger.warning(f"⚠️ TG API Error ({method}): {result.get('description')}")
                if result.get("error_code") == 429: # Flood limit
                    time.sleep(result.get("parameters", {}).get("retry_after", 1))
            except Exception as e:
                TitanLogger.error(f"❌ Attempt {attempt+1} failed for {method}: {e}")
                time.sleep(0.5)
        return {"ok": False}

    @classmethod
    def send_message(cls, chat_id, text, kb=None, rkb=None, parse_mode="HTML", preview=False):
        """Отправка сообщений с поддержкой Inline и Reply клавиатур"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": not preview
        }
        if kb: payload["reply_markup"] = {"inline_keyboard": kb}
        if rkb: payload["reply_markup"] = rkb
        return cls.call("sendMessage", payload)

    @classmethod
    def send_photo(cls, chat_id, photo_url_or_id, caption=None, kb=None, rkb=None):
        """Отправка фото (по URL, ID или файлу)"""
        payload = {"chat_id": chat_id, "photo": photo_url_or_id, "parse_mode": "HTML"}
        if caption: payload["caption"] = caption
        if kb: payload["reply_markup"] = {"inline_keyboard": kb}
        if rkb: payload["reply_markup"] = rkb
        return cls.call("sendPhoto", payload)

    @classmethod
    def delete_message(cls, chat_id, message_id):
        return cls.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    @classmethod
    def send_action(cls, chat_id, action="typing"):
        """Визуальный эффект: 'печатает', 'отправляет фото' и т.д."""
        return cls.call("sendChatAction", {"chat_id": chat_id, "action": action})

# ==============================================================================
# ⌨️ MODULE 6: КОНСТРУКТОР КЛАВИАТУР (UX/UI BUILDER)
# ==============================================================================

class KeyboardFactory:
    """Генератор профессиональных интерфейсов для ACTIONS & COMMANDS"""
    
    @staticmethod
    def main_menu(is_admin=False):
        """Главная нижняя панель управления"""
        buttons = [
            [{"text": "🤖 Нейросеть Gemini"}, {"text": "🎨 Создать Арт"}],
            [{"text": "👤 Мой Профиль"}, {"text": "🛠 Помощь"}]
        ]
        if is_admin:
            buttons.append([{"text": "👑 Панель Управления"}])
        return {"keyboard": buttons, "resize_keyboard": True, "persistent": True}

    @staticmethod
    def cancel_menu():
        """Кнопка отмены, которая всегда под рукой при активных действиях"""
        return {"keyboard": [[{"text": "❌ ОТМЕНИТЬ ДЕЙСТВИЕ"}]], "resize_keyboard": True}

    @staticmethod
    def admin_inline():
        """Многоуровневое инлайн-меню для админки"""
        return [
            [{"text": "📢 Рассылка ОМЕГА", "callback_data": "adm_broadcast"}, {"text": "🗑 Откат", "callback_data": "adm_rollback"}],
            [{"text": "📊 Статистика", "callback_data": "adm_stats"}, {"text": "🛡️ Безопасность", "callback_data": "adm_security"}],
            [{"text": "📑 Логи", "callback_data": "adm_logs"}, {"text": "⚙️ Конфиг ИИ", "callback_data": "adm_ai_config"}]
        ]

# ==============================================================================
# 🔄 MODULE 7: МАШИНА СОСТОЯНИЙ (FINITE STATE MACHINE - FSM)
# ==============================================================================

class FSMContext:
    """Управление текущими шагами пользователя и временными данными"""
    
    @staticmethod
    def set_state(chat_id, state, data=None):
        """Установить новый статус для юзера (например, 'ожидание текста для ИИ')"""
        users = DatabaseManager.read(Config.FILES["users"])
        cid_str = str(chat_id)
        if cid_str in users:
            users[cid_str]["state"] = state
            if data is not None:
                users[cid_str]["temp_data"] = data
            DatabaseManager.write(Config.FILES["users"], users)
            return True
        return False

    @staticmethod
    def get_state(chat_id):
        users = DatabaseManager.read(Config.FILES["users"])
        user = users.get(str(chat_id))
        return (user.get("state", "IDLE"), user.get("temp_data", {})) if user else ("IDLE", {})

    @staticmethod
    def reset(chat_id):
        """Полный сброс в начальное состояние (IDLE)"""
        return FSMContext.set_state(chat_id, "IDLE", {})

# ==============================================================================
# 🎭 MODULE 8: СИСТЕМА ВИЗУАЛИЗАЦИИ ПРОЦЕССОВ (ANIMATION ENGINE)
# ==============================================================================

class TitanVisuals:
    """Создание эффекта живого взаимодействия через анимации"""
    
    @staticmethod
    def progress_bar(chat_id, label):
        """Профессиональный индикатор загрузки"""
        res = TelegramInterface.send_message(chat_id, f"📡 <b>{label}</b>\n<code>[▒▒▒▒▒▒▒▒▒▒] 0%</code>")
        mid = res.get("result", {}).get("message_id")
        
        if mid:
            # Имитация этапов обработки
            steps = [
                (30, "███▒▒▒▒▒▒▒"),
                (60, "██████▒▒▒▒"),
                (90, "█████████▒"),
                (100, "██████████")
            ]
            for p, bar in steps:
                time.sleep(0.3)
                TelegramInterface.call("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": mid,
                    "text": f"📡 <b>{label}</b>\n<code>[{bar}] {p}%</code>",
                    "parse_mode": "HTML"
                })
            return mid
        return None

# ==============================================================================
# ПРОВЕРКА ЧАСТИ 2
# ==============================================================================
TitanLogger.info("✅ ЧАСТЬ 2: Интерфейс и FSM успешно интегрированы.")
# ==============================================================================
# 🧠 MODULE 9: ИНТЕГРАЦИЯ НЕЙРОСЕТЕВОГО ЯДРА (AI CONTROLLER)
# ==============================================================================

class GeminiController:
    """Управление запросами к Gemini 1.5 Flash с многоуровневой проверкой"""
    
    @staticmethod
    def process_request(prompt, image_b64=None):
        """Отправка данных в Gemini и получение чистого ответа"""
        DatabaseManager.write(Config.FILES["stats"], 
            {**DatabaseManager.read(Config.FILES["stats"]), "ai_requests": DatabaseManager.read(Config.FILES["stats"])["ai_requests"] + 1})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        
        # Формируем структуру запроса (Text + Vision)
        parts = [{"text": prompt}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
            
        payload = {"contents": [{"parts": parts}]}
        
        try:
            response = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
            res_data = response.json()
            
            if 'candidates' in res_data:
                return res_data['candidates'][0]['content']['parts'][0]['text']
            
            TitanLogger.warning(f"⚠️ Gemini Response Issue: {res_data}")
            return "❌ <b>Ошибка ИИ:</b> Не удалось сформировать ответ. Попробуйте другой запрос."
        except Exception as e:
            TitanLogger.error(f"❌ Gemini Connection Error: {e}")
            return "🛰 <b>Ошибка связи:</b> Сервер нейросети временно недоступен."

# ==============================================================================
# 🚀 MODULE 10: ГЛАВНЫЙ ОБРАБОТЧИК WEBHOOK (MAIN GATEWAY)
# ==============================================================================

@app.route('/', methods=['POST', 'GET'])
def titan_webhook_gateway():
    """Точка входа для всех событий из Telegram (Webhook)"""
    if request.method == 'GET':
        return f"<h1>SYSTEM {Config.VERSION} ACTIVE</h1>", 200
        
    try:
        update = request.get_json()
        if not update: return "OK", 200
        
        # 1. ОБРАБОТКА CALLBACK QUERIES (Инлайн-кнопки админки)
        if "callback_query" in update:
            process_callback(update["callback_query"])
            return "OK", 200
            
        # 2. ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ
        if "message" in update:
            process_message(update["message"])
            return "OK", 200
            
    except Exception as e:
        TitanLogger.error(f"🔥 CRITICAL CRASH IN GATEWAY: {e}\n{traceback.format_exc()}")
        
    return "OK", 200

# ==============================================================================
# 🛠 MODULE 11: ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ (MESSAGE PROCESSOR)
# ==============================================================================

def process_message(msg):
    """Распределитель команд, текста и медиа для PROFILE & ACTIONS"""
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    caption = msg.get("caption", "")
    full_text = (text or caption or "").strip()
    
    # Регистрация (PROFILE)
    DatabaseManager.add_user(user_id, msg["from"].get("username"), msg["from"].get("first_name"))
    
    # Проверка доступа (SECURITY)
    access = SecurityManager.check_access(user_id)
    if not access["status"]:
        if access["reason"] == "BANNED":
            TelegramInterface.send_message(chat_id, "🚫 <b>Доступ заблокирован.</b> Обратитесь к администратору.")
        return

    # Получаем текущее состояние (FSM)
    state, temp_data = FSMContext.get_state(user_id)
    is_admin = SecurityManager.is_admin(user_id)

    # --- БЛОК УНИВЕРСАЛЬНОЙ ОТМЕНЫ ---
    if full_text == "❌ ОТМЕНИТЬ ДЕЙСТВИЕ":
        FSMContext.reset(user_id)
        TelegramInterface.send_message(chat_id, "✅ <b>Действие отменено.</b> Возврат в главное меню.", 
                                      rkb=KeyboardFactory.main_menu(is_admin))
        return

    # --- ОБРАБОТКА СОСТОЯНИЙ (FSM ACTIONS) ---
    if state != "IDLE":
        handle_state_action(chat_id, user_id, state, msg, full_text, is_admin)
        return

    # --- ГЛАВНЫЕ КОМАНДЫ (COMMANDS) ---
    if full_text == "/start" or full_text == "🏠 Главное меню":
        FSMContext.reset(user_id)
        welcome = f"🌌 <b>TITAN SYSTEM {Config.VERSION}</b>\n\nДобро пожаловать. Выберите действие:"
        TelegramInterface.send_message(chat_id, welcome, rkb=KeyboardFactory.main_menu(is_admin))
        
    elif full_text == "🤖 Нейросеть Gemini":
        FSMContext.set_state(user_id, "WAITING_AI_PROMPT")
        TelegramInterface.send_message(chat_id, "🧠 <b>Режим ИИ активирован.</b>\nВведите ваш вопрос или отправьте фото для анализа:", 
                                      rkb=KeyboardFactory.cancel_menu())

    elif full_text == "🎨 Создать Арт":
        FSMContext.set_state(user_id, "WAITING_ART_PROMPT")
        TelegramInterface.send_message(chat_id, "🎨 <b>Синтез изображений.</b>\nОпишите, что нужно нарисовать:", 
                                      rkb=KeyboardFactory.cancel_menu())

    elif full_text == "👤 Мой Профиль":
        u_data = DatabaseManager.read(Config.FILES["users"]).get(str(user_id), {})
        profile = (f"👤 <b>ВАШ ПРОФИЛЬ</b>\n━━━━━━━━━━━━━━\n"
                   f"🆔 ID: <code>{user_id}</code>\n"
                   f"🛡 Статус: {'Администратор' if is_admin else 'Пользователь'}\n"
                   f"📅 Регистрация: {u_data.get('joined', 'Неизвестно')}")
        TelegramInterface.send_message(chat_id, profile)

    elif full_text == "👑 Панель Управления" and is_admin:
        TelegramInterface.send_message(chat_id, "👑 <b>TITAN ADMIN PANEL</b>\nВыберите модуль управления:", 
                                      kb=KeyboardFactory.admin_inline())

    # --- СВОБОДНЫЙ ВВОД (AI AUTO-RESPONSE) ---
    elif full_text:
        TelegramInterface.send_action(chat_id, "typing")
        ans = GeminiController.process_request(full_text)
        TelegramInterface.send_message(chat_id, ans)

# ==============================================================================
# 🎮 MODULE 12: ОБРАБОТЧИК СОСТОЯНИЙ (STATE HANDLER)
# ==============================================================================

def handle_state_action(chat_id, user_id, state, msg, text, is_admin):
    """Логика выполнения действий в зависимости от FSM"""
    
    if state == "WAITING_AI_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "АНАЛИЗ ИИ")
        img_b64 = None
        if "photo" in msg:
            # Логика получения фото (будет в ЧАСТИ 4)
            pass
        
        ans = GeminiController.process_request(text, img_b64)
        if mid: TelegramInterface.delete_message(chat_id, mid)
        TelegramInterface.send_message(chat_id, ans, rkb=KeyboardFactory.main_menu(is_admin))
        FSMContext.reset(user_id)

    elif state == "WAITING_ART_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "СИНТЕЗ АРТА")
        # Здесь будет интеграция Pollinations
        img_url = f"https://image.pollinations.ai/prompt/{text}?nologo=true&width=1024&height=1024"
        TelegramInterface.send_photo(chat_id, img_url, caption=f"✅ <b>Готово!</b>\nЗапрос: <i>{text}</i>", 
                                    rkb=KeyboardFactory.main_menu(is_admin))
        if mid: TelegramInterface.delete_message(chat_id, mid)
        FSMContext.reset(user_id)

    elif state == "WAITING_BC_CONTENT" and is_admin:
        # Логика рассылки (будет в ЧАСТИ 4)
        pass

# КОНЕЦ ЧАСТИ 3. ПРОЦЕССОР СОЕДИНЕН С ОРГАНАМИ УПРАВЛЕНИЯ.


# ==============================================================================
# 🛠 MODULE 13: АДМИНИСТРАТИВНЫЙ КОНТРОЛЛЕР (ADMIN COMMAND CENTER)
# ==============================================================================

def process_callback(cb):
    """Обработка нажатий на инлайн-кнопки (Интерфейс ACTIONS)"""
    user_id = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    mid = cb["message"]["message_id"]
    data = cb["data"]

    if not SecurityManager.is_admin(user_id):
        TelegramInterface.call("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "❌ Нет доступа"})
        return

    if data == "adm_broadcast":
        FSMContext.set_state(user_id, "WAITING_BC_CONTENT")
        TelegramInterface.send_message(chat_id, "📢 <b>РЕЖИМ РАССЫЛКИ</b>\nОтправьте текст или фото для всех юзеров:", 
                                      rkb=KeyboardFactory.cancel_menu())
        TelegramInterface.call("answerCallbackQuery", {"callback_query_id": cb["id"]})

    elif data == "adm_stats":
        st = DatabaseManager.read(Config.FILES["stats"])
        us = len(DatabaseManager.read(Config.FILES["users"]))
        report = (f"📊 <b>TITAN GLOBAL STATS</b>\n━━━━━━━━━━━━━━\n"
                  f"👤 Всего юзеров: <code>{us}</code>\n"
                  f"🧠 Запросов к ИИ: <code>{st['ai_requests']}</code>\n"
                  f"🎨 Артов создано: <code>{st['images_generated']}</code>\n"
                  f"⚠️ Ошибок лога: <code>{st['errors']}</code>")
        TelegramInterface.call("editMessageText", {"chat_id": chat_id, "message_id": mid, "text": report, 
                                                   "parse_mode": "HTML", "reply_markup": {"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "adm_back"}]]}})

    elif data == "adm_logs":
        TelegramInterface.call("sendDocument", {"chat_id": chat_id, "document": open(Config.FILES["log"], 'rb'), "caption": "📑 Системный лог V26.0"})

    elif data == "adm_back":
        TelegramInterface.call("editMessageText", {"chat_id": chat_id, "message_id": mid, "text": "👑 <b>TITAN ADMIN PANEL</b>", 
                                                   "parse_mode": "HTML", "reply_markup": {"inline_keyboard": KeyboardFactory.admin_inline()}})

# ==============================================================================
# 📡 MODULE 14: МЕНЕДЖЕР МЕДИА-ДАННЫХ (FILE & MEDIA ENGINE)
# ==============================================================================

class MediaManager:
    """Загрузка и конвертация изображений для анализа Gemini"""
    
    @staticmethod
    def get_photo_b64(photo_list):
        """Получение фото самого высокого качества и перевод в Base64"""
        try:
            file_id = photo_list[-1]["file_id"]
            file_info = TelegramInterface.call("getFile", {"file_id": file_id})
            if file_info.get("ok"):
                file_path = file_info["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{file_path}"
                img_data = requests.get(download_url).content
                return base64.b64encode(img_data).decode('utf-8')
        except Exception as e:
            TitanLogger.error(f"Ошибка загрузки фото: {e}")
        return None

# ==============================================================================
# 📢 MODULE 15: СИСТЕМА МАССОВОГО ВЕЩАНИЯ (BROADCAST ENGINE)
# ==============================================================================

def execute_broadcast(admin_id, msg):
    """Рассылка контента по всей базе PROFILE"""
    users = DatabaseManager.read(Config.FILES["users"])
    success = 0
    failed = 0
    
    text = msg.get("text") or msg.get("caption")
    photo = msg.get("photo")[-1]["file_id"] if "photo" in msg else None
    
    mid = TelegramInterface.send_message(admin_id, "🚀 <b>Рассылка запущена...</b>")["result"]["message_id"]
    
    for uid in users:
        try:
            if photo:
                res = TelegramInterface.send_photo(uid, photo, caption=text)
            else:
                res = TelegramInterface.send_message(uid, text)
            
            if res.get("ok"): success += 1
            else: failed += 1
            time.sleep(0.05) # Защита от Flood Limit
        except:
            failed += 1
            
    TelegramInterface.call("editMessageText", {"chat_id": admin_id, "message_id": mid, 
                                               "text": f"✅ <b>Рассылка завершена!</b>\n\n📈 Успешно: {success}\n📉 Ошибок: {failed}", "parse_mode": "HTML"})

# ==============================================================================
# 🛠 MODULE 16: КОРРЕКТИРОВКА STATE HANDLER (ОБНОВЛЕНИЕ ИЗ ЧАСТИ 3)
# ==============================================================================

def handle_state_action(chat_id, user_id, state, msg, text, is_admin):
    """Дополненная логика состояний для обработки фото и рассылки"""
    
    if state == "WAITING_AI_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "АНАЛИЗ ДАННЫХ")
        img_b64 = None
        if "photo" in msg:
            img_b64 = MediaManager.get_photo_b64(msg["photo"])
        
        ans = GeminiController.process_request(text or "Что на этом фото?", img_b64)
        if mid: TelegramInterface.delete_message(chat_id, mid)
        TelegramInterface.send_message(chat_id, ans, rkb=KeyboardFactory.main_menu(is_admin))
        FSMContext.reset(user_id)

    elif state == "WAITING_BC_CONTENT" and is_admin:
        execute_broadcast(user_id, msg)
        FSMContext.reset(user_id)
        TelegramInterface.send_message(chat_id, "🏠 Возврат в меню", rkb=KeyboardFactory.main_menu(True))

    elif state == "WAITING_ART_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "ГЕНЕРАЦИЯ АРТА")
        img_url = f"https://image.pollinations.ai/prompt/{text}?nologo=true&width=1024&height=1024"
        DatabaseManager.write(Config.FILES["stats"], 
            {**DatabaseManager.read(Config.FILES["stats"]), "images_generated": DatabaseManager.read(Config.FILES["stats"])["images_generated"] + 1})
        
        TelegramInterface.send_photo(chat_id, img_url, caption=f"🎨 <b>Ваш арт готов!</b>\nЗапрос: <i>{text}</i>", 
                                    rkb=KeyboardFactory.main_menu(is_admin))
        if mid: TelegramInterface.delete_message(chat_id, mid)
        FSMContext.reset(user_id)

# ==============================================================================
# 🏁 FINAL MODULE: ЗАПУСК СЕРВЕРА
# ==============================================================================

if __name__ == "__main__":
    # Финальная проверка перед стартом
    TitanLogger.info("🚀 Сборка V26.0 OMEGA завершена. Запуск сервера...")
    
    # Порт для Render
    port = int(os.environ.get("PORT", 5000))
    
    # Запуск Flask
    app.run(host='0.0.0.0', port=port)
    
