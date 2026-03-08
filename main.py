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
# ⚙️ КОНФИГУРАЦИЯ (С ТВОИМИ ДАННЫМИ)
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
    GITHUB_LOGS_PATH = "logs/titan_logs.txt"  # Путь к файлу логов в репозитории

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
    'start_time': datetime.datetime.now(),
    'commands_used': {}
}

db_lock = threading.Lock()

# ==============================================================================
# 📦 GITHUB СТОРАДЖ (СОХРАНЕНИЕ В РЕПОЗИТОРИЙ)
# ==============================================================================
class GitHubStorage:
    """Класс для работы с GitHub как с хранилищем"""
    
    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.repo_name = Config.GITHUB_REPO
        self.logs_path = Config.GITHUB_LOGS_PATH
        self.github = None
        self.repo = None
        self.authenticated = False
        
        self.authenticate()
    
    def authenticate(self):
        """Авторизация в GitHub"""
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
        """Сохранить логи в GitHub"""
        if not self.authenticated:
            logger.warning("GitHub не авторизован, логи не сохранены")
            return False
        
        try:
            # Формируем текст логов
            log_text = "\n".join(log_entries)
            log_text = f"# TITAN LOGS - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{log_text}"
            
            try:
                # Пытаемся получить существующий файл
                contents = self.repo.get_contents(self.logs_path)
                # Обновляем файл
                self.repo.update_file(
                    path=self.logs_path,
                    message=f"Logs update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content=log_text,
                    sha=contents.sha
                )
                logger.info(f"✅ Логи обновлены в GitHub: {self.logs_path}")
            except GithubException as e:
                if e.status == 404:
                    # Файл не существует - создаём новый
                    self.repo.create_file(
                        path=self.logs_path,
                        message=f"Logs created {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        content=log_text
                    )
                    logger.info(f"✅ Логи созданы в GitHub: {self.logs_path}")
                else:
                    raise e
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения логов в GitHub: {e}")
            return False
    
    def get_logs(self):
        """Получить логи из GitHub"""
        if not self.authenticated:
            return None, "❌ GitHub не настроен"
        
        try:
            contents = self.repo.get_contents(self.logs_path)
            # Декодируем из base64
            log_text = base64.b64decode(contents.content).decode('utf-8')
            
            # Сохраняем временный файл для отправки
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
            logger.error(f"❌ Ошибка получения логов: {e}")
            return None, f"❌ Ошибка: {e}"
    
    def clear_logs(self):
        """Очистить логи (создать пустой файл)"""
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
        """Получить прямую ссылку на скачивание файла"""
        if not self.authenticated:
            return None
        
        try:
            contents = self.repo.get_contents(self.logs_path)
            # GitHub API возвращает download_url
            return contents.download_url
        except:
            return None

# Инициализируем GitHub Storage
github_storage = GitHubStorage()

# Логи в памяти (как буфер)
SYSTEM_LOGS = []
MAX_LOGS = 100
LAST_SAVE_TIME = time.time()
SAVE_INTERVAL = 300  # Сохранять в GitHub каждые 5 минут

# ==============================================================================
# 📝 СИСТЕМА ЛОГОВ (С СОХРАНЕНИЕМ В GITHUB)
# ==============================================================================
def add_log(action, admin_id, target=None, details=""):
    """Добавление записи в лог и сохранение в GitHub"""
    global SYSTEM_LOGS, LAST_SAVE_TIME
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Admin:{admin_id} | Action:{action} | Target:{target} | {details}"
    
    with db_lock:
        SYSTEM_LOGS.append(log_entry)
        if len(SYSTEM_LOGS) > MAX_LOGS:
            SYSTEM_LOGS = SYSTEM_LOGS[-MAX_LOGS:]
    
    # Сохраняем в GitHub каждые SAVE_INTERVAL секунд
    current_time = time.time()
    if current_time - LAST_SAVE_TIME > SAVE_INTERVAL:
        save_logs_to_github()
        LAST_SAVE_TIME = current_time

def save_logs_to_github():
    """Сохранить текущие логи в GitHub"""
    if not github_storage.authenticated:
        return
    
    with db_lock:
        logs_copy = SYSTEM_LOGS.copy()
    
    if logs_copy:
        github_storage.save_logs(logs_copy)
        logger.info(f"Логи автоматически сохранены в GitHub")

def force_save_logs():
    """Принудительно сохранить логи"""
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
    """Главное админ-меню с GitHub кнопками"""
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
    """Отправка файла (для логов)"""
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
                USER_SETTINGS[cid] = {
                    'speed': 0.03,
                    'mode': 'words'
                }
            
            if cid not in USER_TIMEOUTS:
                USER_TIMEOUTS[cid] = 60
        
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
        # 👤 /profile
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
                if github_storage.authenticated:
                    profile += f"\n🌐 GitHub: ✅"
                else:
                    profile += f"\n🌐 GitHub: ❌"
            
            send_msg(cid, profile, get_profile_keyboard() if not is_admin else get_admin_main_keyboard())
            return
        
        # ==========================================================
        # 👑 /adminprofile
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
📊 Команд: {ADMIN
