import os
import requests
import json
import logging
import threading
import time
import datetime
import random
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    VERSION = "V26.1 OMEGA FULL-ADMIN"
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE")
    GROQ_KEY = os.environ.get("GROQ_KEY", "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")
    MAIN_ADMIN_ID = int(os.environ.get("ADMIN_ID", "5378010557"))
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 💾 БАЗЫ ДАННЫХ
# ==============================================================================
USERS_DB = set()  # Все пользователи
ADMINS_DB = set([Config.MAIN_ADMIN_ID])  # Админы (главный уже там)
USER_STATES = {}  # Состояния
USER_SETTINGS = {}  # Настройки пользователей
USER_TIMEOUTS = {}  # Индивидуальные таймауты {user_id: seconds}
USER_LAST_MSG = {}  # Для КД
BANNED_USERS = set()

ADMIN_STATS = {
    'total_messages': 0,
    'total_images': 0,
    'start_time': datetime.datetime.now(),
    'commands_used': {}
}

# Логи
SYSTEM_LOGS = []
MAX_LOGS = 100

db_lock = threading.Lock()

# ==============================================================================
# 🎨 КЛАВИАТУРЫ
# ==============================================================================
def get_main_keyboard():
    """Главное меню для всех"""
    keyboard = [
        ["👤 Личный кабинет", "❓ Помощь"],
        ["💬 Связаться с ИИ", "🎨 Сгенерировать"],
        ["📢 Связь с админом"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_profile_keyboard():
    """Клавиатура в личном кабинете"""
    keyboard = [
        ["⚙️ Настройки", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_settings_keyboard():
    """Клавиатура настроек"""
    keyboard = [
        ["🐢 Медленно", "⚡ Средне", "🐇 Быстро"],
        ["📝 Словами", "🔤 Буквами"],
        ["💾 Сохранить", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_cancel_keyboard():
    """Клавиатура с отменой"""
    keyboard = [
        ["❌ Отмена"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_admin_main_keyboard():
    """Главное админ-меню (50+ кнопок)"""
    keyboard = [
        ["📊 СТАТИСТИКА", "📢 РАССЫЛКА", "👥 ВСЕ ЮЗЕРЫ"],
        ["👑 АДМИНЫ", "🚫 БАН-ЛИСТ", "📝 ЛОГИ"],
        ["⚙️ УПРАВЛЕНИЕ", "⏱️ ТАЙМАУТЫ", "💾 БЕКАП"],
        ["➕ ДОБАВИТЬ АДМИНА", "➖ УДАЛИТЬ АДМИНА"],
        ["🔒 ЗАБЛОКИРОВАТЬ", "🔓 РАЗБЛОКИРОВАТЬ"],
        ["📨 ОТВЕТИТЬ ЮЗЕРУ", "📤 ГЛОБАЛЬНО"],
        ["⚡ БЫСТРЫЕ КОМАНДЫ", "🔄 ПЕРЕЗАПУСК"],
        ["🔙 НАЗАД В МЕНЮ"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_timeout_keyboard():
    """Клавиатура для настройки таймаутов"""
    keyboard = [
        ["⏱️ 30 сек", "⏱️ 60 сек", "⏱️ 120 сек"],
        ["⏱️ 5 мин", "⏱️ 10 мин", "⏱️ 30 мин"],
        ["⏱️ 1 час", "⏱️ 3 часа", "⏱️ 12 часов"],
        ["⏱️ 24 часа", "⏱️ Без лимита", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_manage_keyboard():
    """Клавиатура управления"""
    keyboard = [
        ["📊 ОЧИСТИТЬ ЛОГИ", "🔄 СБРОС СТАТИСТИКИ"],
        ["💾 СОХРАНИТЬ БД", "📥 ЗАГРУЗИТЬ БД"],
        ["📢 ОБЪЯВЛЕНИЕ", "🔔 УВЕДОМЛЕНИЕ"],
        ["🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# ⚡ БЫСТРЫЙ ИИ
# ==============================================================================
def fast_ai_response(prompt):
    """Быстрый ответ от нейросети"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Ты TITAN. Отвечай кратко и по делу."},
            {"role": "user", "content": prompt[:500]}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"GROQ Error: {e}")
        return "⚠️ Ошибка связи. Попробуй позже."

# ==============================================================================
# 🖼 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ
# ==============================================================================
def generate_image(prompt):
    """Генерация изображения"""
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&nologo=true&model=flux"
        return url
    except Exception as e:
        logger.error(f"Image error: {e}")
        return None

# ==============================================================================
# 📤 ФУНКЦИИ TELEGRAM
# ==============================================================================
def send_msg(chat_id, text, kb=None, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if kb:
        payload["reply_markup"] = kb
    try:
        return requests.post(url, json=payload, timeout=5)
    except:
        return None

def send_photo(chat_id, photo_url, caption=""):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    try:
        return requests.post(url, json=payload, timeout=10)
    except:
        return None

def send_typing(chat_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction"
    try:
        requests.post(url, json={"chat_id": chat_id, "action": "typing"}, timeout=1)
    except:
        pass

def edit_msg(chat_id, msg_id, text):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    try:
        return requests.post(url, json=payload, timeout=3)
    except:
        return None

def delete_msg(chat_id, msg_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "message_id": msg_id})
    except:
        pass

def copy_msg(to_chat, from_chat, msg_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage"
    try:
        response = requests.post(url, json={"chat_id": to_chat, "from_chat_id": from_chat, "message_id": msg_id}, timeout=5)
        return response.status_code == 200
    except:
        return False

# ==============================================================================
# 📝 ЛОГИРОВАНИЕ
# ==============================================================================
def add_log(action, admin_id, target=None, details=""):
    """Добавление записи в лог"""
    global SYSTEM_LOGS
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Admin:{admin_id} | Action:{action} | Target:{target} | {details}"
    
    with db_lock:
        SYSTEM_LOGS.append(log_entry)
        if len(SYSTEM_LOGS) > MAX_LOGS:
            SYSTEM_LOGS = SYSTEM_LOGS[-MAX_LOGS:]

# ==============================================================================
# 🎭 АНИМАЦИЯ ПЕЧАТИ
# ==============================================================================
def fast_animate(chat_id, text, settings):
    """Быстрая анимация печати"""
    try:
        if settings.get('mode') == 'words':
            words = text.split()
            if len(words) <= 3:
                send_msg(chat_id, text)
                return
            
            msg = send_msg(chat_id, "⏳")
            if not msg:
                send_msg(chat_id, text)
                return
            
            msg_id = msg.json()['result']['message_id']
            current = ""
            delay = settings.get('speed', 0.03)
            
            for word in words:
                current += word + " "
                edit_msg(chat_id, msg_id, current.strip())
                time.sleep(delay)
        else:
            if len(text) < 20:
                send_msg(chat_id, text)
                return
            
            msg = send_msg(chat_id, "⏳")
            if not msg:
                send_msg(chat_id, text)
                return
            
            msg_id = msg.json()['result']['message_id']
            current = ""
            delay = settings.get('speed', 0.01)
            
            for char in text:
                current += char
                if len(current) % 5 == 0:
                    edit_msg(chat_id, msg_id, current)
                    time.sleep(delay)
            edit_msg(chat_id, msg_id, text)
    except Exception as e:
        logger.error(f"Animation error: {e}")
        send_msg(chat_id, text)

# ==============================================================================
# 📡 ОБРАБОТЧИК
# ==============================================================================
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def webhook():
    if request.method == 'HEAD':
        return '', 200
    if request.method == 'GET':
        return "TITAN ACTIVE", 200

    if request.method == 'POST':
        update = request.get_json(silent=True)
        if update and "message" in update:
            thread = threading.Thread(target=process_message, args=(update,))
            thread.daemon = True
            thread.start()
        return "OK", 200

def process_message(update):
    try:
        msg = update["message"]
        cid = msg["chat"]["id"]
        text = msg.get("text", "")
        user_name = msg["from"].get("first_name", "User")
        
        # Проверка бана
        if cid in BANNED_USERS:
            return
        
        # Регистрация
        with db_lock:
            if cid not in USERS_DB:
                USERS_DB.add(cid)
            
            if cid not in USER_SETTINGS:
                USER_SETTINGS[cid] = {
                    'speed': 0.03,
                    'mode': 'words'
                }
            
            if cid not in USER_TIMEOUTS:
                USER_TIMEOUTS[cid] = 60  # По умолчанию 60 сек
        
        # Проверка админ ли?
        is_admin = cid in ADMINS_DB
        
        # ==========================================================
        # ❌ ОТМЕНА
        # ==========================================================
        if text == "❌ Отмена":
            with db_lock:
                if cid in USER_STATES:
                    USER_STATES.pop(cid)
            send_msg(cid, "❌ Действие отменено", get_main_keyboard())
            return
        
        # ==========================================================
        # 👤 /profile ДЛЯ ВСЕХ
        # ==========================================================
        if text == "/profile" or text == "👤 Личный кабинет":
            role = "👑 Админ" if is_admin else "👤 Пользователь"
            settings = USER_SETTINGS.get(cid, {})
            timeout = USER_TIMEOUTS.get(cid, 60)
            
            speed_text = "Быстро" if settings.get('speed') == 0.02 else "Средне" if settings.get('speed') == 0.03 else "Медленно"
            
            profile = f"""
<b>👤 ПРОФИЛЬ</b>
────────────────
👤 Имя: {user_name}
🆔 ID: <code>{cid}</code>
👑 Роль: {role}
⚡ Скорость: {speed_text}
📝 Режим: {'Словами' if settings.get('mode') == 'words' else 'Буквами'}
⏱️ Таймаут: {timeout} сек
────────────────"""
            
            if is_admin:
                profile += f"\n👥 Админов: {len(ADMINS_DB)}"
            
            send_msg(cid, profile, get_profile_keyboard() if not is_admin else get_admin_main_keyboard())
            return
        
        # ==========================================================
        # 👑 /adminprofile ДЛЯ АДМИНОВ
        # ==========================================================
        if is_admin and (text == "/adminprofile" or text == "👑 АДМИНЫ"):
            admins_list = []
            for admin_id in ADMINS_DB:
                role = "👑 ГЛАВНЫЙ" if admin_id == Config.MAIN_ADMIN_ID else "👤 АДМИН"
                admins_list.append(f"{role}: <code>{admin_id}</code>")
            
            admins_text = "\n".join(admins_list)
            
            profile = f"""
<b>👑 АДМИН ПАНЕЛЬ</b>
────────────────
👑 Главный админ: <code>{Config.MAIN_ADMIN_ID}</code>
👥 Всего админов: {len(ADMINS_DB)}
────────────────
{admins_text}
────────────────
📊 Команд: {ADMIN_STATS['commands_used']}
👥 Юзеров: {len(USERS_DB)}
🚫 Забанено: {len(BANNED_USERS)}
────────────────"""
            
            send_msg(cid, profile, get_admin_main_keyboard())
            return
        
        # ==========================================================
        # ГЛАВНОЕ МЕНЮ - СТАРТ
        # ==========================================================
        if text == "/start":
            welcome = f"⚡ <b>TITAN {Config.VERSION}</b>\n\nПривет, {user_name}! Я здесь чтобы помочь."
            
            if is_admin:
                welcome += "\n\n👑 У тебя есть права администратора!"
                send_msg(cid, welcome, get_admin_main_keyboard())
            else:
                send_msg(cid, welcome, get_main_keyboard())
            return
        
        # ==========================================================
        # ❓ ПОМОЩЬ
        # ==========================================================
        if text == "❓ Помощь":
            help_text = """
<b>❓ ПОМОЩЬ</b>

💬 <b>Связаться с ИИ</b> - задай любой вопрос
🎨 <b>Сгенерировать</b> - создай изображение
📢 <b>Связь с админом</b> - написать админу
⚙️ <b>Настройки</b> - скорость печати

📝 <b>Команды:</b>
/profile - твой профиль

⚡ <b>Версия:</b> TITAN V26.1 FULL-ADMIN"""
            
            kb = get_admin_main_keyboard() if is_admin else get_help_keyboard()
            send_msg(cid, help_text, kb)
            return
        
        # ==========================================================
        # 📢 СВЯЗЬ С АДМИНОМ
        # ==========================================================
        if text == "📢 Связь с админом":
            last_time = USER_LAST_MSG.get(cid, 0)
            current_time = time.time()
            timeout = USER_TIMEOUTS.get(cid, 60)
            
            if current_time - last_time < timeout:
                wait = int(timeout - (current_time - last_time))
                send_msg(cid, f"⏳ Подожди {wait} сек.", get_cancel_keyboard())
                return
            
            with db_lock:
                USER_STATES[cid] = 'msg_admin'
            send_msg(cid, "📝 Напиши сообщение для админа:", get_cancel_keyboard())
            return
        
        # ==========================================================
        # ОБРАБОТКА СООБЩЕНИЯ ДЛЯ АДМИНА
        # ==========================================================
        with db_lock:
            state = USER_STATES.get(cid)
        
        if state == 'msg_admin' and text and text != "❌ Отмена":
            USER_LAST_MSG[cid] = time.time()
            
            # Отправляем всем админам
            for admin_id in ADMINS_DB:
                header = f"📨 <b>Сообщение от пользователя</b>\n👤 {user_name}\n🆔 <code>{cid}</code>\n⏱️ Таймаут: {USER_TIMEOUTS.get(cid, 60)}сек\n\n"
                send_msg(admin_id, header + text)
            
            send_msg(cid, "✅ Отправлено!", get_main_keyboard())
            with db_lock:
                USER_STATES.pop(cid, None)
            return
        
        # ==========================================================
        # 💬 СВЯЗАТЬСЯ С ИИ
        # ==========================================================
        if text == "💬 Связаться с ИИ":
            send_msg(cid, "🧠 Напиши свой вопрос:", get_cancel_keyboard())
            with db_lock:
                USER_STATES[cid] = 'ai_chat'
            return
        
        # ==========================================================
        # 🎨 СГЕНЕРИРОВАТЬ
        # ==========================================================
        if text == "🎨 Сгенерировать":
            send_msg(cid, "🖼 Что нарисовать? Напиши описание:", get_cancel_keyboard())
            with db_lock:
                USER_STATES[cid] = 'generate'
            return
        
        # ==========================================================
        # ⚙️ НАСТРОЙКИ
        # ==========================================================
        if text == "⚙️ Настройки":
            send_msg(cid, "⚙️ <b>Настройки печати:</b>", get_settings_keyboard())
            return
        
        # Обработка настроек
        if text in ["🐢 Медленно", "⚡ Средне", "🐇 Быстро"]:
            speeds = {"🐢 Медленно": 0.05, "⚡ Средне": 0.03, "🐇 Быстро": 0.02}
            with db_lock:
                USER_SETTINGS[cid]['speed'] = speeds[text]
            send_msg(cid, f"✅ Скорость: {text}", get_settings_keyboard())
            return
        
        if text in ["📝 Словами", "🔤 Буквами"]:
            modes = {"📝 Словами": "words", "🔤 Буквами": "letters"}
            with db_lock:
                USER_SETTINGS[cid]['mode'] = modes[text]
            send_msg(cid, f"✅ Режим: {text}", get_settings_keyboard())
            return
        
        if text == "💾 Сохранить":
            kb = get_profile_keyboard() if not is_admin else get_admin_main_keyboard()
            send_msg(cid, "✅ Настройки сохранены!", kb)
            return
        
        # ==========================================================
        # 👑 АДМИН ПАНЕЛЬ (ТОЛЬКО ДЛЯ АДМИНОВ)
        # ==========================================================
        if is_admin:
            
            # СТАТИСТИКА
            if text == "📊 СТАТИСТИКА":
                uptime = datetime.datetime.now() - ADMIN_STATS['start_time']
                stats = f"""
<b>📊 СТАТИСТИКА</b>
────────────────
👥 Юзеров: {len(USERS_DB)}
👑 Админов: {len(ADMINS_DB)}
📨 Сообщений: {ADMIN_STATS['total_messages']}
🖼 Картинок: {ADMIN_STATS['total_images']}
⏱ Аптайм: {str(uptime).split('.')[0]}
🚫 Забанено: {len(BANNED_USERS)}
────────────────"""
                send_msg(cid, stats, get_admin_main_keyboard())
                add_log("stats_view", cid)
                return
            
            # ВСЕ ЮЗЕРЫ
            if text == "👥 ВСЕ ЮЗЕРЫ":
                users_list = []
                for i, uid in enumerate(list(USERS_DB)[:30]):
                    is_ban = "🚫" if uid in BANNED_USERS else "✅"
                    is_admin_flag = "👑" if uid in ADMINS_DB else ""
                    users_list.append(f"{is_ban}{is_admin_flag} <code>{uid}</code>")
                
                if len(USERS_DB) > 30:
                    users_list.append(f"... и еще {len(USERS_DB)-30}")
                
                text = f"<b>👥 Всего {len(USERS_DB)}:</b>\n" + "\n".join(users_list)
                send_msg(cid, text, get_admin_main_keyboard())
                return
            
            # БАН-ЛИСТ
            if text == "🚫 БАН-ЛИСТ":
                if not BANNED_USERS:
                    send_msg(cid, "🚫 Бан-лист пуст", get_admin_main_keyboard())
                else:
                    banned = "\n".join([f"<code>{uid}</code>" for uid in BANNED_USERS])
            
