import os
import requests
import json
import logging
import threading
import time
import datetime
import base64
from flask import Flask, request
from github import Github, GithubException

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    VERSION = "V26.1 OMEGA GITHUB"
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE")
    GROQ_KEY = os.environ.get("GROQ_KEY", "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")
    MAIN_ADMIN_ID = int(os.environ.get("ADMIN_ID", "5378010557"))
    PORT = int(os.environ.get("PORT", 10000))
    
    # GitHub настройки (ТВОИ ДАННЫЕ)
    GITHUB_TOKEN = "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"
    GITHUB_REPO = "norzollxyz/code"
    GITHUB_LOGS_PATH = "logs/titan_logs.txt"

app = Flask(__name__)

# ==============================================================================
# 💾 БАЗЫ ДАННЫХ
# ==============================================================================
USERS_DB = set()
ADMINS_DB = set([Config.MAIN_ADMIN_ID])
USER_STATES = {}
USER_SETTINGS = {}
USER_TIMEOUTS = {}
USER_LAST_MSG = {}
BANNED_USERS = set()

ADMIN_STATS = {
    'total_messages': 0,
    'total_images': 0,
    'start_time': datetime.datetime.now()
}

db_lock = threading.Lock()

# ==============================================================================
# 📦 GITHUB СТОРАДЖ
# ==============================================================================
class GitHubStorage:
    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.repo_name = Config.GITHUB_REPO
        self.logs_path = Config.GITHUB_LOGS_PATH
        self.github = None
        self.repo = None
        self.authenticated = False
        self.authenticate()
    
    def authenticate(self):
        try:
            if self.token and self.token != "ghp_твой_токен_сюда":
                self.github = Github(self.token)
                self.repo = self.github.get_repo(self.repo_name)
                self.authenticated = True
                logger.info(f"✅ GitHub авторизация успешна: {self.repo_name}")
            else:
                logger.warning("⚠️ GitHub токен не настроен")
        except Exception as e:
            logger.error(f"❌ GitHub auth error: {e}")
            self.authenticated = False
    
    def save_logs(self, log_entries):
        if not self.authenticated:
            return False
        try:
            log_text = "\n".join(log_entries)
            log_text = f"# TITAN LOGS - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{log_text}"
            try:
                contents = self.repo.get_contents(self.logs_path)
                self.repo.update_file(
                    path=self.logs_path,
                    message=f"Logs update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content=log_text,
                    sha=contents.sha
                )
            except GithubException as e:
                if e.status == 404:
                    self.repo.create_file(
                        path=self.logs_path,
                        message=f"Logs created {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        content=log_text
                    )
                else:
                    raise e
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения логов: {e}")
            return False
    
    def get_logs(self):
        if not self.authenticated:
            return None, "❌ GitHub не настроен"
        try:
            contents = self.repo.get_contents(self.logs_path)
            log_text = base64.b64decode(contents.content).decode('utf-8')
            temp_path = "/tmp/titan_logs.txt"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(log_text)
            return temp_path, log_text
        except GithubException as e:
            if e.status == 404:
                return None, "📝 Логи пока не созданы"
            else:
                return None, f"❌ Ошибка: {e}"
        except Exception as e:
            return None, f"❌ Ошибка: {e}"
    
    def clear_logs(self):
        if not self.authenticated:
            return False
        try:
            empty_log = f"# TITAN LOGS CLEARED - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            try:
                contents = self.repo.get_contents(self.logs_path)
                self.repo.update_file(
                    path=self.logs_path,
                    message=f"Logs cleared {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content=empty_log,
                    sha=contents.sha
                )
            except GithubException as e:
                if e.status == 404:
                    self.repo.create_file(
                        path=self.logs_path,
                        message=f"Logs created {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        content=empty_log
                    )
                else:
                    raise e
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка очистки логов: {e}")
            return False
    
    def get_download_url(self):
        if not self.authenticated:
            return None
        try:
            contents = self.repo.get_contents(self.logs_path)
            return contents.download_url
        except:
            return None

github_storage = GitHubStorage()
SYSTEM_LOGS = []
MAX_LOGS = 100
LAST_SAVE_TIME = time.time()
SAVE_INTERVAL = 300

# ==============================================================================
# 📝 СИСТЕМА ЛОГОВ
# ==============================================================================
def add_log(action, admin_id, target=None, details=""):
    global SYSTEM_LOGS, LAST_SAVE_TIME
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Admin:{admin_id} | Action:{action} | Target:{target} | {details}"
    with db_lock:
        SYSTEM_LOGS.append(log_entry)
        if len(SYSTEM_LOGS) > MAX_LOGS:
            SYSTEM_LOGS = SYSTEM_LOGS[-MAX_LOGS:]
    current_time = time.time()
    if current_time - LAST_SAVE_TIME > SAVE_INTERVAL:
        save_logs_to_github()
        LAST_SAVE_TIME = current_time

def save_logs_to_github():
    if not github_storage.authenticated:
        return
    with db_lock:
        logs_copy = SYSTEM_LOGS.copy()
    if logs_copy:
        github_storage.save_logs(logs_copy)

def force_save_logs():
    with db_lock:
        logs_copy = SYSTEM_LOGS.copy()
    if logs_copy:
        return github_storage.save_logs(logs_copy)
    return False

# ==============================================================================
# 🎨 КЛАВИАТУРЫ
# ==============================================================================
def get_main_keyboard():
    keyboard = [
        ["👤 Личный кабинет", "❓ Помощь"],
        ["💬 Связаться с ИИ", "🎨 Сгенерировать"],
        ["📢 Связь с админом"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_profile_keyboard():
    keyboard = [
        ["⚙️ Настройки", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_help_keyboard():
    keyboard = [
        ["🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_settings_keyboard():
    keyboard = [
        ["🐢 Медленно", "⚡ Средне", "🐇 Быстро"],
        ["📝 Словами", "🔤 Буквами"],
        ["💾 Сохранить", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_cancel_keyboard():
    keyboard = [
        ["❌ Отмена"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_admin_main_keyboard():
    keyboard = [
        ["📊 СТАТИСТИКА", "📢 РАССЫЛКА", "👥 ВСЕ ЮЗЕРЫ"],
        ["👑 АДМИНЫ", "🚫 БАН-ЛИСТ", "📝 ЛОГИ"],
        ["⚙️ УПРАВЛЕНИЕ", "⏱️ ТАЙМАУТЫ", "💾 БЕКАП"],
        ["➕ ДОБАВИТЬ АДМИНА", "➖ УДАЛИТЬ АДМИНА"],
        ["🔒 ЗАБЛОКИРОВАТЬ", "🔓 РАЗБЛОКИРОВАТЬ"],
        ["📨 ОТВЕТИТЬ ЮЗЕРУ", "📤 ГЛОБАЛЬНО"],
        ["⬇️ СКАЧАТЬ ЛОГИ", "🧹 ОЧИСТИТЬ ЛОГИ"],
        ["💾 СОХРАНИТЬ В GITHUB", "🌐 GitHub СТАТУС"],
        ["🔄 ПЕРЕЗАПУСК", "🔙 НАЗАД В МЕНЮ"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_timeout_keyboard():
    keyboard = [
        ["⏱️ 30 сек", "⏱️ 60 сек", "⏱️ 120 сек"],
        ["⏱️ 5 мин", "⏱️ 10 мин", "⏱️ 30 мин"],
        ["⏱️ 1 час", "⏱️ 3 часа", "⏱️ 12 часов"],
        ["⏱️ 24 часа", "⏱️ Без лимита", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_manage_keyboard():
    keyboard = [
        ["🧹 ОЧИСТИТЬ ЛОГИ", "🔄 СБРОС СТАТИСТИКИ"],
        ["💾 СОХРАНИТЬ В GITHUB", "⬇️ СКАЧАТЬ ЛОГИ"],
        ["🌐 GitHub СТАТУС", "🔙 Назад"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# ⚡ БЫСТРЫЙ ИИ
# ==============================================================================
def fast_ai_response(prompt):
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

def send_document(chat_id, file_path, caption=""):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
            return requests.post(url, data=data, files=files, timeout=30)
    except Exception as e:
        logger.error(f"Document error: {e}")
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
# 🎭 АНИМАЦИЯ ПЕЧАТИ
# ==============================================================================
def fast_animate(chat_id, text, settings):
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
        
        if cid in BANNED_USERS:
            return
        
        with db_lock:
            if cid not in USERS_DB:
                USERS_DB.add(cid)
            if cid not in USER_SETTINGS:
                USER_SETTINGS[cid] = {'speed': 0.03, 'mode': 'words'}
            if cid not in USER_TIMEOUTS:
                USER_TIMEOUTS[cid] = 60
        
        is_admin = cid in ADMINS_DB
        
        if text == "❌ Отмена":
            with db_lock:
                if cid in USER_STATES:
                    USER_STATES.pop(cid)
            send_msg(cid, "❌ Действие отменено", get_main_keyboard())
            return
        
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
                if github_storage.authenticated:
                    profile += f"\n🌐 GitHub: ✅"
                else:
                    profile += f"\n🌐 GitHub: ❌"
            send_msg(cid, profile, get_profile_keyboard() if not is_admin else get_admin_main_keyboard())
            return
        
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
👥 Юзеров: {len(USERS_DB)}
🚫 Забанено: {len(BANNED_USERS)}
────────────────
🌐 GitHub: {'✅ Подключен' if github_storage.authenticated else '❌ Не настроен'}"""
            send_msg(cid, profile, get_admin_main_keyboard())
            return
        
        if text == "/start":
            welcome = f"⚡ <b>TITAN {Config.VERSION}</b>\n\nПривет, {user_name}! Я здесь чтобы помочь."
            if is_admin:
                welcome += "\n\n👑 У тебя есть права администратора!"
                if not github_storage.authenticated:
                    welcome += "\n\n⚠️ GitHub не настроен! Логи не будут сохраняться."
                send_msg(cid, welcome, get_admin_main_keyboard())
            else:
                send_msg(cid, welcome, get_main_keyboard())
            return
        
        if text == "❓ Помощь":
            help_text = """
<b>❓ ПОМОЩЬ</b>
💬 <b>Связаться с ИИ</b> - задай любой вопрос
🎨 <b>Сгенерировать</b> - создай изображение
📢 <b>Связь с админом</b> - написать админу
⚙️ <b>Настройки</b> - скорость печати
📝 <b>Команды:</b>
/profile - твой профиль
⚡ <b>Версия:</b> TITAN V26.1 GITHUB"""
            kb = get_admin_main_keyboard() if is_admin else get_help_keyboard()
            send_msg(cid, help_text, kb)
            return
        
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
        
        with db_lock:
            state = USER_STATES.get(cid)
        
        if state == 'msg_admin' and text and text != "❌ Отмена":
            USER_LAST_MSG[cid] = time.time()
            for admin_id in ADMINS_DB:
                header = f"📨 <b>Сообщение от пользователя</b>\n👤 {user_name}\n🆔 <code>{cid}</code>\n⏱️ Таймаут: {USER_TIMEOUTS.get(cid, 60)}сек\n\n"
                send_msg(admin_id, header + text)
            send_msg(cid, "✅ Отправлено!", get_main_keyboard())
            with db_lock:
                USER_STATES.pop(cid, None)
            add_log("user_message", cid, details=f"To admin: {text[:50]}")
            return
        
        if text == "💬 Связаться с ИИ":
            send_msg(cid, "🧠 Напиши свой вопрос:", get_cancel_keyboard())
            with db_lock:
                USER_STATES[cid] = 'ai_chat'
            return
        
        if text == "🎨 Сгенерировать":
            send_msg(cid, "🖼 Что нарисовать? Напиши описание:", get_cancel_keyboard())
            with db_lock:
                USER_STATES[cid] = 'generate'
            return
        
        if text == "⚙️ Настройки":
            send_msg(cid, "⚙️ <b>Настройки печати:</b>", get_settings_keyboard())
            return
        
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
        
        if is_admin:
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
────────────────
🌐 GitHub: {'✅ Активен' if github_storage.authenticated else '❌ Не настроен'}
📝 Логов в буфере: {len(SYSTEM_LOGS)}"""
                send_msg(cid, stats, get_admin_main_keyboard())
                add_log("stats_view", cid)
                return
            
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
            
            if text == "🚫 БАН-ЛИСТ":
                if not BANNED_USERS:
                    send_msg(cid, "🚫 Бан-лист пуст", get_admin_main_keyboard())
                else:
                    banned = "\n".join([f"<code>{uid}</code>" for uid in BANNED_USERS])
                    send_msg(cid, f"<b>🚫 Забанены ({len(BANNED_USERS)}):</b>\n{banned}", get_admin_main_keyboard())
                return
            
            if text == "📝 ЛОГИ":
                if not SYSTEM_LOGS:
                    send_msg(cid, "📝 Логи в памяти пусты", get_admin_main_keyboard())
                else:
                    logs_text = "\n".join(SYSTEM_LOGS[-20:])
                    send_msg(cid, f"<b>📝 Последние логи (в памяти):</b>\n<pre>{logs_text}</pre>", get_admin_main_keyboard())
                return
            
            if text == "⬇️ СКАЧАТЬ ЛОГИ":
                status_msg = send_msg(cid, "🔄 Загружаю логи из GitHub...")
                file_path, content = github_storage.get_logs()
                if file_path and os.path.exists(file_path):
                    send_document(cid, file_path, f"📝 Логи TITAN {datetime.datetime.now().strftime('%Y-%m-%d')}")
                    download_url = github_storage.get_download_url()
                    if download_url:
                        send_msg(cid, f"🔗 <b>Прямая ссылка:</b>\n{download_url}")
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    add_log("logs_downloaded", cid)
                else:
                    send_msg(cid, content, get_admin_main_keyboard())
                if status_msg:
                    delete_msg(cid, status_msg.json()['result']['message_id'])
                return
            
            if text == "🧹 ОЧИСТИТЬ ЛОГИ":
                with db_lock:
                    SYSTEM_LOGS.clear()
                if github_storage.authenticated:
                    result = github_storage.clear_logs()
                    if result:
                        send_msg(cid, "✅ Логи в GitHub очищены", get_admin_main_keyboard())
                    else:
                        send_msg(cid, "⚠️ Логи в памяти очищены, но GitHub ошибка", get_admin_main_keyboard())
                else:
                    send_msg(cid, "✅ Логи в памяти очищены", get_admin_main_keyboard())
                add_log("logs_cleared", cid)
                return
            
            if text == "💾 СОХРАНИТЬ В GITHUB":
                if not github_storage.authenticated:
                    send_msg(cid, "❌ GitHub не настроен", get_admin_main_keyboard())
                    return
                status_msg = send_msg(cid, "🔄 Сохраняю логи в GitHub...")
                result = force_save_logs()
                if status_msg:
                    delete_msg(cid, status_msg.json()['result']['message_id'])
                if result:
                    send_msg(cid, f"✅ Логи сохранены в GitHub!\n📁 {Config.GITHUB_LOGS_PATH}", get_admin_main_keyboard())
                else:
                    send_msg(cid, "❌ Ошибка сохранения в GitHub", get_admin_main_keyboard())
                add_log("logs_saved_github", cid)
                return
            
            if text == "🌐 GitHub СТАТУС":
                if github_storage.authenticated:
                    repo = github_storage.repo
                    status = f"""
<b>🌐 GitHub СТАТУС</b>
────────────────
✅ Авторизация: Успешно
📁 Репозиторий: {Config.GITHUB_REPO}
📝 Файл логов: {Config.GITHUB_LOGS_PATH}
👤 Владелец: {repo.owner.login}
🌿 Ветка: {repo.default_branch}
🔗 Ссылка: {repo.html_url}
────────────────"""
                else:
                    status = f"""
<b>🌐 GitHub СТАТУС</b>
────────────────
❌ Авторизация: Не настроена
📁 Репозиторий: {Config.GITHUB_REPO}
📝 Файл логов: {Config.GITHUB_LOGS_PATH}
────────────────"""
                send_msg(cid, status, get_admin_main_keyboard())
                return
            
            if text == "📢 РАССЫЛКА":
                with db_lock:
                    USER_STATES[cid] = 'broadcast'
                send_msg(cid, "📥 Отправь пост для рассылки:", get_cancel_keyboard())
                return
            
            if text == "⚙️ УПРАВЛЕНИЕ":
                send_msg(cid, "⚙️ <b>Управление системой:</b>", get_manage_keyboard())
                return
            
            if text == "⏱️ ТАЙМАУТЫ":
                send_msg(cid, "⏱️ <b>Настройка таймаутов:</b>\n\nОтправь ID пользователя или выбери время для всех:", get_timeout_keyboard())
                with db_lock:
                    USER_STATES[cid] = 'waiting_timeout_user'
                return
            
            if text == "➕ ДОБАВИТЬ АДМИНА":
                if cid == Config.MAIN_ADMIN_ID:
                    send_msg(cid, "👑 Отправь ID пользователя, которого хочешь сделать админом:", get_cancel_keyboard())
                    with db_lock:
                        USER_STATES[cid] = 'add_admin'
                else:
                    send_msg(cid, "❌ Только главный админ может добавлять админов", get_admin_main_keyboard())
                return
            
            if text == "➖ УДАЛИТЬ АДМИНА":
                if cid == Config.MAIN_ADMIN_ID:
                    admins_list = "\n".join([f"<code>{aid}</code>" for aid in ADMINS_DB if aid != Config.MAIN_ADMIN_ID])
                    send_msg(cid, f"👑 Отправь ID админа для удаления:\n\n{admins_list}", get_cancel_keyboard())
                    with db_lock:
                        USER_STATES[cid] = 'remove_admin'
                else:
                    send_msg(cid, "❌ Только главный админ может удалять админов", get_admin_main_keyboard())
                return
            
            if text == "🔒 ЗАБЛОКИРОВАТЬ":
                send_msg(cid, "🔒 Отправь ID пользователя для блокировки:", get_cancel_keyboard())
                with db_lock:
                    USER_STATES[cid] = 'ban_user'
                return
            
            if text == "🔓 РАЗБЛОКИРОВАТЬ":
                send_msg(cid, "🔓 Отправь ID пользователя для разблокировки:", get_cancel_keyboard())
                with db_lock:
                    USER_STATES[cid] = 'unban_user'
                return
            
            if text == "📨 ОТВЕТИТЬ ЮЗЕРУ":
                send_msg(cid, "📨 Отправь ID пользователя и сообщение в формате:\n<code>123456789 Привет!</code>", get_cancel_keyboard())
                with db_lock:
                    USER_STATES[cid] = 'reply_user'
                return
            
            if text == "💾 БЕКАП":
                backup = f"""
<b>💾 БЕКАП СИСТЕМЫ</b>
────────────────
👥 Юзеров: {len(USERS_DB)}
👑 Админов: {len(ADMINS_DB)}
🚫 Забанено: {len(BANNED_USERS)}
📊 Сообщений: {ADMIN_STATS['total_messages']}
🖼 Картинок: {ADMIN_STATS['total_images']}
📝 Логов в буфере: {len(SYSTEM_LOGS)}
────────────────
🌐 GitHub: {'✅' if github_storage.authenticated else '❌'}"""
                send_msg(cid, backup, get_admin_main_keyboard())
                add_log("backup_created", cid)
                return
            
            if text == "🔙 НАЗАД В МЕНЮ" or text == "🔙 Назад":
                send_msg(cid, "Главное меню:", get_admin_main_keyboard())
                with db_lock:
                    if cid in USER_STATES:
                        USER_STATES.pop(cid)
                return
            
            if text == "🔄 СБРОС СТАТИСТИКИ":
                with db_lock:
                    ADMIN_STATS['total_messages'] = 0
                    ADMIN_STATS['total_images'] = 0
                    ADMIN_STATS['start_time'] = datetime.datetime.now()
                send_msg(cid, "✅ Статистика сброшена", get_manage_keyboard())
                add_log("stats_reset", cid)
                return
            
            if state == 'add_admin' and text and text != "❌ Отмена":
                try:
                    new_admin = int(text)
                    if new_admin in ADMINS_DB:
                        send_msg(cid, "❌ Этот пользователь уже админ", get_admin_main_keyboard())
                    else:
                        with db_lock:
                            ADMINS_DB.add(new_admin)
                        send_msg(cid, f"✅ Пользователь <code>{new_admin}</code> теперь админ!", get_admin_main_keyboard())
                        send_msg(new_admin, "👑 Вам выданы права администратора!", get_admin_main_keyboard())
                        add_log("admin_added", cid, new_admin)
                except:
                    send_msg(cid, "❌ Неверный ID", get_admin_main_keyboard())
                with db_lock:
                    USER_STATES.pop(cid, None)
                return
            
            if state == 'remove_admin' and text and text != "❌ Отмена":
                try:
                    remove_id = int(text)
                    if remove_id == Config.MAIN_ADMIN_ID:
                        send_msg(cid, "❌ Нельзя удалить главного админа", get_admin_main_keyboard())
                    elif remove_id in ADMINS_DB:
                        with db_lock:
                            ADMINS_DB.remove(remove_id)
                        send_msg(cid, f"✅ Админ <code>{remove_id}</code> удален", get_admin_main_keyboard())
                        send_msg(remove_id, "👤 Ваши права администратора отозваны", get_main_keyboard())
                        add_log("admin_removed", cid, remove_id)
                    else:
                        send_msg(cid, "❌ Этот пользователь не админ", get_admin_main_keyboard())
                except:
                    send_msg(cid, "❌ Неверный ID", get_admin_main_keyboard())
                with db_lock:
                    USER_STATES.pop(cid, None)
                return
            
            if state == 'ban_user' and text and text != "❌ Отмена":
                try:
                    ban_id = int(text)
                    if ban_id in ADMINS_DB:
                        send_msg(cid, "❌ Нельзя забанить админа", get_admin_main_keyboard())
                    else:
                        with db_lock:
                            BANNED_USERS.add(ban_id)
                        send_msg(cid, f"✅ Пользователь <code>{ban_id}</code> забанен", get_admin_main_keyboard())
                        add_log("user_banned", cid, ban_id)
                except:
                    send_msg(cid, "❌ Неверный ID", get_admin_main_keyboard())
                with db_lock:
                    USER_STATES.pop(cid, None)
                return
            
            if state == 'unban_user' and text and text != "❌ Отмена":
                try:
                    unban_id = int(text)
                    if unban_id in BANNED_USERS:
                        with db_lock:
                            BANNED_USERS.remove(unban_id)
                        send_msg(cid, f"✅ Пользователь <code>{unban_id}</code> разбанен", get_admin_main_keyboard())
                        add_log("user_unbanned", cid, unban_id)
                    else:
                        send_msg(cid, "❌ Этот пользователь не в бане", get_admin_main_keyboard())
                except:
                    send_msg(cid, "❌ Неверный ID", get_admin_main_keyboard())
                with db_lock:
                    USER_STATES.pop(cid, None)
                return
            
            if state == 'reply_user' and text and text != "❌ Отмена":
                try:
                    parts = text.split(' ', 1)
                    if len(parts) == 2:
                        target_id = int(parts[0])
                        reply_text = parts[1]
                        result =
