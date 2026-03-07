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
from datetime import datetime
from threading import Lock
from flask import Flask, request, jsonify

# ==============================================================================
# ⚙️ CONFIGURATION & SECURITY
# ==============================================================================

class Config:
    VERSION = "V26.0 (PROFILE, ACTIONS & COMMANDS)"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    MAIN_ADMIN_ID = 5378010557
    
    ROOT_DIR = "V26_DATA_VAULT"
    DIRS = {
        "db": f"{ROOT_DIR}/database",
        "logs": f"{ROOT_DIR}/logs",
        "temp": f"{ROOT_DIR}/temp_media"
    }
    
    FILES = {
        "users": f"{DIRS['db']}/users_db.json",
        "admins": f"{DIRS['db']}/admins_db.json",
        "bans": f"{DIRS['db']}/ban_list.json",
        "stats": f"{DIRS['db']}/system_stats.json",
        "settings": f"{DIRS['db']}/bot_settings.json",
        "log": f"{DIRS['logs']}/titan_v26.log"
    }
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3

# ==============================================================================
# 📝 SYSTEM LOGGING & DATABASE
# ==============================================================================

class TitanLogger:
    @staticmethod
    def setup():
        for path in Config.DIRS.values():
            if not os.path.exists(path): os.makedirs(path)
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(Config.FILES["log"], encoding="utf-8"), logging.StreamHandler(sys.stdout)]
        )

class DatabaseManager:
    _lock = Lock()

    @classmethod
    def initialize_databases(cls):
        with cls._lock:
            defaults = {
                Config.FILES["users"]: {},
                Config.FILES["admins"]: [Config.MAIN_ADMIN_ID],
                Config.FILES["bans"]: [],
                Config.FILES["stats"]: {"messages_total": 0, "ai_requests": 0, "images_generated": 0, "errors": 0},
                Config.FILES["settings"]: {"maintenance_mode": False, "ai_enabled": True}
            }
            for filepath, default_data in defaults.items():
                if not os.path.exists(filepath):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, ensure_ascii=False, indent=4)

    @classmethod
    def read(cls, filepath):
        with cls._lock:
            try:
                with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
            except: return None

    @classmethod
    def write(cls, filepath, data):
        with cls._lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return True
            except: return False

    @classmethod
    def add_user(cls, chat_id, username, first_name):
        users = cls.read(Config.FILES["users"])
        cid_str = str(chat_id)
        if cid_str not in users:
            users[cid_str] = {
                "id": chat_id, "username": username or "Unknown", 
                "name": first_name or "User", "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "state": "IDLE", "temp_data": {}
            }
            cls.write(Config.FILES["users"], users)
            return True
        return False

# ==============================================================================
# 🛡️ SECURITY & FSM
# ==============================================================================

class SecurityManager:
    @staticmethod
    def is_admin(chat_id):
        admins = DatabaseManager.read(Config.FILES["admins"])
        return chat_id == Config.MAIN_ADMIN_ID or chat_id in admins

    @staticmethod
    def check_access(chat_id):
        bans = DatabaseManager.read(Config.FILES["bans"])
        if chat_id in bans: return {"status": False, "reason": "BANNED"}
        return {"status": True, "reason": "OK"}

class FSMContext:
    @staticmethod
    def set_state(chat_id, state, data=None):
        users = DatabaseManager.read(Config.FILES["users"])
        cid_str = str(chat_id)
        if cid_str in users:
            users[cid_str]["state"] = state
            if data is not None: users[cid_str]["temp_data"] = data
            DatabaseManager.write(Config.FILES["users"], users)

    @staticmethod
    def get_state(chat_id):
        users = DatabaseManager.read(Config.FILES["users"])
        user = users.get(str(chat_id))
        return (user.get("state", "IDLE"), user.get("temp_data", {})) if user else ("IDLE", {})

    @staticmethod
    def reset(chat_id):
        FSMContext.set_state(chat_id, "IDLE", {})

# ==============================================================================
# 📡 COMMUNICATIONS (TELEGRAM & GEMINI)
# ==============================================================================

class TelegramInterface:
    @classmethod
    def call(cls, method, payload=None, files=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{method}"
        try:
            if files: return requests.post(url, data=payload, files=files, timeout=Config.REQUEST_TIMEOUT).json()
            return requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT).json()
        except: return {"ok": False}

    @classmethod
    def send_message(cls, chat_id, text, kb=None, rkb=None):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb: payload["reply_markup"] = {"inline_keyboard": kb}
        if rkb: payload["reply_markup"] = rkb
        return cls.call("sendMessage", payload)

    @classmethod
    def send_photo(cls, chat_id, photo, caption=None, rkb=None):
        payload = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}
        if caption: payload["caption"] = caption
        if rkb: payload["reply_markup"] = rkb
        return cls.call("sendPhoto", payload)

class GeminiController:
    @staticmethod
    def process_request(prompt, image_b64=None):
        stats = DatabaseManager.read(Config.FILES["stats"])
        stats["ai_requests"] += 1
        DatabaseManager.write(Config.FILES["stats"], stats)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        parts = [{"text": prompt}]
        if image_b64: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
        
        try:
            r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=Config.REQUEST_TIMEOUT).json()
            return r['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ Ошибка связи с ИИ."

# ==============================================================================
# ⌨️ UI & VISUALS
# ==============================================================================

class KeyboardFactory:
    @staticmethod
    def main_menu(is_admin=False):
        kb = [[{"text": "🤖 Нейросеть Gemini"}, {"text": "🎨 Создать Арт"}],
              [{"text": "👤 Мой Профиль"}, {"text": "🛠 Помощь"}]]
        if is_admin: kb.append([{"text": "👑 Панель Управления"}])
        return {"keyboard": kb, "resize_keyboard": True}

    @staticmethod
    def cancel_menu():
        return {"keyboard": [[{"text": "❌ ОТМЕНИТЬ ДЕЙСТВИЕ"}]], "resize_keyboard": True}

    @staticmethod
    def admin_inline():
        return [[{"text": "📢 Рассылка", "callback_data": "adm_broadcast"}, {"text": "📊 Статистика", "callback_data": "adm_stats"}],
                [{"text": "📑 Логи", "callback_data": "adm_logs"}]]

class TitanVisuals:
    @staticmethod
    def progress_bar(chat_id, label):
        res = TelegramInterface.send_message(chat_id, f"📡 <b>{label}...</b>")
        return res.get("result", {}).get("message_id")

# ==============================================================================
# 🚀 ROUTING & LOGIC
# ==============================================================================

app = Flask(__name__)

def execute_broadcast(admin_id, msg):
    users = DatabaseManager.read(Config.FILES["users"])
    text = msg.get("text") or msg.get("caption") or "Сообщение без текста"
    photo = msg.get("photo")[-1]["file_id"] if "photo" in msg else None
    
    success = 0
    for uid in users:
        try:
            res = TelegramInterface.send_photo(uid, photo, caption=text) if photo else TelegramInterface.send_message(uid, text)
            if res.get("ok"): success += 1
            time.sleep(0.05)
        except: continue
    TelegramInterface.send_message(admin_id, f"✅ Рассылка завершена. Получили: {success}")

def handle_state_action(chat_id, user_id, state, msg, text, is_admin):
    if state == "WAITING_AI_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "АНАЛИЗ")
        img_b64 = None
        if "photo" in msg:
            try:
                fid = msg["photo"][-1]["file_id"]
                fp_res = TelegramInterface.call("getFile", {"file_id": fid})
                if fp_res.get("ok"):
                    fp = fp_res["result"]["file_path"]
                    img_data = requests.get(f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{fp}").content
                    img_b64 = base64.b64encode(img_data).decode('utf-8')
            except: pass
            
        ans = GeminiController.process_request(text or "Опиши фото", image_b64=img_b64)
        if mid: TelegramInterface.call("deleteMessage", {"chat_id": chat_id, "message_id": mid})
        TelegramInterface.send_message(chat_id, ans, rkb=KeyboardFactory.main_menu(is_admin))
        FSMContext.reset(user_id)
    
    elif state == "WAITING_ART_PROMPT":
        mid = TitanVisuals.progress_bar(chat_id, "РИСОВАНИЕ")
        img_url = f"https://image.pollinations.ai/prompt/{text}?nologo=true"
        TelegramInterface.send_photo(chat_id, img_url, caption=f"🎨 Готово!\nЗапрос: {text}", rkb=KeyboardFactory.main_menu(is_admin))
        if mid: TelegramInterface.call("deleteMessage", {"chat_id": chat_id, "message_id": mid})
        FSMContext.reset(user_id)
        
    elif state == "WAITING_BC_CONTENT" and is_admin:
        execute_broadcast(user_id, msg)
        FSMContext.reset(user_id)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "V26.0 ACTIVE", 200
    update = request.get_json()
    if not update: return "OK", 200
    
    if "callback_query" in update:
        cb = update["callback_query"]
        uid, cid, data = cb["from"]["id"], cb["message"]["chat"]["id"], cb["data"]
        if not SecurityManager.is_admin(uid): return "OK", 200
        
        if data == "adm_broadcast":
            FSMContext.set_state(uid, "WAITING_BC_CONTENT")
            TelegramInterface.send_message(cid, "📢 Отправьте сообщение для рассылки:", rkb=KeyboardFactory.cancel_menu())
        elif data == "adm_stats":
            st = DatabaseManager.read(Config.FILES["stats"])
            TelegramInterface.send_message(cid, f"📊 Запросов ИИ: {st['ai_requests']}")
        elif data == "adm_logs":
            try:
                TelegramInterface.call("sendDocument", {"chat_id": cid}, files={"document": open(Config.FILES["log"], 'rb')})
            except: TelegramInterface.send_message(cid, "❌ Лог пуст.")
        return "OK", 200

    if "message" in update:
        msg = update["message"]
        chat_id, user_id = msg["chat"]["id"], msg["from"]["id"]
        text = (msg.get("text") or msg.get("caption") or "").strip()
        
        DatabaseManager.add_user(user_id, msg["from"].get("username"), msg["from"].get("first_name"))
        if not SecurityManager.check_access(user_id)["status"]: return "OK", 200
        
        state, _ = FSMContext.get_state(user_id)
        is_admin = SecurityManager.is_admin(user_id)

        if text == "❌ ОТМЕНИТЬ ДЕЙСТВИЕ":
            FSMContext.reset(user_id)
            TelegramInterface.send_message(chat_id, "✅ Отменено.", rkb=KeyboardFactory.main_menu(is_admin))
            return "OK", 200

        if state != "IDLE":
            handle_state_action(chat_id, user_id, state, msg, text, is_admin)
            return "OK", 200

        if text == "/start" or text == "🏠 Главное меню":
            TelegramInterface.send_message(chat_id, "🌌 TITAN V26.0 ONLINE", rkb=KeyboardFactory.main_menu(is_admin))
        elif text == "🤖 Нейросеть Gemini":
            FSMContext.set_state(user_id, "WAITING_AI_PROMPT")
            TelegramInterface.send_message(chat_id, "🧠 Жду ваш запрос или фото:", rkb=KeyboardFactory.cancel_menu())
        elif text == "🎨 Создать Арт":
            FSMContext.set_state(user_id, "WAITING_ART_PROMPT")
            TelegramInterface.send_message(chat_id, "🎨 Что нарисовать?", rkb=KeyboardFactory.cancel_menu())
        elif text == "👤 Мой Профиль":
            TelegramInterface.send_message(chat_id, f"👤 ID: <code>{user_id}</code>\n🛡 Статус: {'Админ' if is_admin else 'Юзер'}")
        elif text == "👑 Панель Управления" and is_admin:
            TelegramInterface.send_message(chat_id, "👑 ADMIN PANEL", kb=KeyboardFactory.admin_inline())
            
    return "OK", 200

if __name__ == "__main__":
    TitanLogger.setup()
    DatabaseManager.initialize_databases()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
ion, photo=msg["photo"][-1]["file_id"]) if "photo" in msg else send_tg(u, text)
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
    
