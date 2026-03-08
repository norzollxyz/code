import os
import requests
import json
import logging
import threading
import time
import datetime
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    VERSION = "V26.1 OMEGA"
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE")
    GROQ_KEY = os.environ.get("GROQ_KEY", "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")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "5378010557"))
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

USERS_DB = set()
USER_STATES = {}
ADMIN_STATS = {
    'total_messages': 0,
    'total_images': 0,
    'start_time': datetime.datetime.now()
}
db_lock = threading.Lock()

# ==============================================================================
# 🎨 ГЛАВНОЕ МЕНЮ (ПО СТАРОМУ - РАБОЧЕЕ)
# ==============================================================================
def get_main_keyboard():
    """Главное меню - работает всегда"""
    keyboard = [
        ["👤 Личный кабинет", "❓ Помощь"],
        ["💬 Связаться с ИИ", "🎨 Сгенерировать"],
        ["📢 Связь с админом"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# 👑 АДМИН-МЕНЮ (ТОЛЬКО НУЖНОЕ)
# ==============================================================================
def get_admin_keyboard():
    """Только полезные функции для админа"""
    keyboard = [
        ["📢 РАССЫЛКА", "📊 СТАТИСТИКА"],
        ["👥 ВСЕ ЮЗЕРЫ", "📤 БЕКАП"],
        ["🧹 ОЧИСТИТЬ ЛОГИ", "🔄 ПЕРЕЗАПУСК"],
        ["🔙 НАЗАД В МЕНЮ"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# ⚡ БЫСТРЫЙ ИИ (Groq - реально быстрый)
# ==============================================================================
def fast_ai_response(prompt):
    """Максимально быстрый ответ от ИИ"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",  # Самая быстрая модель
        "messages": [
            {"role": "system", "content": "Ты TITAN. Отвечай кратко, по делу, без воды."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300,  # Меньше токенов = быстрее ответ
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"GROQ Error: {e}")
        return "⚠️ Ошибка связи. Попробуй еще раз."

# ==============================================================================
# 🖼 ИСПРАВЛЕННАЯ ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ
# ==============================================================================
def generate_image_fixed(prompt):
    """Рабочая генерация изображений"""
    try:
        # Используем правильный API
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        params = {
            "width": 1024,
            "height": 1024,
            "nologo": "true",
            "model": "flux"  # Хорошая модель
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.url  # Возвращаем прямую ссылку
        else:
            # Запасной вариант
            return f"https://pollinations.ai/p/{requests.utils.quote(prompt)}"
    except Exception as e:
        logger.error(f"Image gen error: {e}")
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

def send_typing(chat_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction"
    try:
        requests.post(url, json={"chat_id": chat_id, "action": "typing"}, timeout=2)
    except:
        pass

def send_photo(chat_id, photo_url, caption=""):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    try:
        return requests.post(url, json=payload, timeout=10)
    except:
        return None

def edit_msg(chat_id, msg_id, text):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    try:
        return requests.post(url, json=payload, timeout=5)
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
        response = requests.post(url, json={"chat_id": to_chat, "from_chat_id": from_chat, "message_id": msg_id}, timeout=10)
        return response.status_code == 200
    except:
        return False

# ==============================================================================
# 🎭 КРАСИВАЯ АНИМАЦИЯ ПЕЧАТИ
# ==============================================================================
def animate_typing(chat_id, final_text, delay=0.1):
    """
    Создает эффект печатания текста
    delay = скорость печати (меньше = быстрее)
    """
    try:
        # Сначала отправляем пустое сообщение
        msg = send_msg(chat_id, "⏳")
        if not msg:
            return
        
        msg_id = msg.json()['result']['message_id']
        
        # Печатаем по буквам
        current_text = ""
        for char in final_text:
            current_text += char
            edit_msg(chat_id, msg_id, current_text)
            time.sleep(delay)  # Задержка между буквами
        
        return msg_id
    except Exception as e:
        logger.error(f"Animation error: {e}")
        # Если анимация сломалась, отправляем обычное сообщение
        send_msg(chat_id, final_text)
        return None

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
        
        # Регистрируем пользователя
        with db_lock:
            if cid not in USERS_DB:
                USERS_DB.add(cid)
                logger.info(f"New user: {cid}")
        
        # Проверка на рассылку
        with db_lock:
            is_broadcast = USER_STATES.get(cid) == 'broadcast'
        
        # РАССЫЛКА (для админа)
        if cid == Config.ADMIN_ID and is_broadcast:
            with db_lock:
                USER_STATES.pop(cid, None)
            
            success = 0
            users_copy = list(USERS_DB)
            status_msg = send_msg(cid, f"📢 Рассылка: 0/{len(users_copy)}")
            
            for i, uid in enumerate(users_copy):
                if copy_msg(uid, cid, msg["message_id"]):
                    success += 1
                if i % 5 == 0 and status_msg:
                    edit_msg(cid, status_msg.json()['result']['message_id'], f"📢 Рассылка: {i+1}/{len(users_copy)}")
                time.sleep(0.03)  # Небольшая задержка
            
            send_msg(cid, f"✅ Рассылка завершена!\nДоставлено: {success}/{len(users_copy)}", get_admin_keyboard())
            return
        
        # ГЛАВНОЕ МЕНЮ - СТАРТ
        if text == "/start":
            welcome = f"<b>⚡ TITAN {Config.VERSION}</b>\n\nПривет, {user_name}! Я здесь, чтобы помочь."
            send_msg(cid, welcome, get_main_keyboard())
            return
        
        # КНОПКИ ГЛАВНОГО МЕНЮ
        if text == "👤 Личный кабинет":
            role = "👑 АДМИН" if cid == Config.ADMIN_ID else "👤 ПОЛЬЗОВАТЕЛЬ"
            profile = f"""
<b>👤 ПРОФИЛЬ</b>
─────────────────
👤 Имя: {user_name}
🆔 ID: <code>{cid}</code>
👑 Роль: {role}
👥 Всего юзеров: {len(USERS_DB)}
─────────────────"""
            send_msg(cid, profile)
            return
        
        if text == "❓ Помощь":
            help_text = """
<b>❓ ПОМОЩЬ</b>

💬 <b>Связаться с ИИ</b> - нажми и пиши вопрос
🎨 <b>Сгенерировать</b> - создай картинку
📢 <b>Связь с админом</b> - написать мне

⚡ Версия: TITAN V26.1
"""
            send_msg(cid, help_text)
            return
        
        if text == "💬 Связаться с ИИ":
            send_msg(cid, "🧠 Напиши свой вопрос...")
            with db_lock:
                USER_STATES[cid] = 'ai_chat'
            return
        
        if text == "🎨 Сгенерировать":
            send_msg(cid, "🖼 Напиши, что сгенерировать. Например: <i>кот в космосе</i>")
            with db_lock:
                USER_STATES[cid] = 'generate_image'
            return
        
        if text == "📢 Связь с админом":
            send_msg(cid, "📝 Напиши сообщение для админа:")
            with db_lock:
                USER_STATES[cid] = 'message_admin'
            return
        
        # АДМИНКА
        if cid == Config.ADMIN_ID:
            if text == "📢 РАССЫЛКА":
                with db_lock:
                    USER_STATES[cid] = 'broadcast'
                send_msg(cid, "📥 Отправь пост для рассылки:", get_admin_keyboard())
                return
            
            if text == "📊 СТАТИСТИКА":
                uptime = datetime.datetime.now() - ADMIN_STATS['start_time']
                stats = f"""
<b>📊 СТАТИСТИКА</b>
─────────────────
👥 Юзеров: {len(USERS_DB)}
📨 Сообщений: {ADMIN_STATS['total_messages']}
🖼 Картинок: {ADMIN_STATS['total_images']}
⏱ Аптайм: {str(uptime).split('.')[0]}
─────────────────"""
                send_msg(cid, stats)
                return
            
            if text == "👥 ВСЕ ЮЗЕРЫ":
                users_list = "\n".join([f"<code>{uid}</code>" for uid in list(USERS_DB)[:50]])
                if len(USERS_DB) > 50:
                    users_list += f"\n...и еще {len(USERS_DB)-50}"
                send_msg(cid, f"<b>👥 Всего {len(USERS_DB)}:</b>\n{users_list}")
                return
            
            if text == "🔙 НАЗАД В МЕНЮ":
                send_msg(cid, "Главное меню:", get_main_keyboard())
                return
        
        # ОБРАБОТКА СОСТОЯНИЙ
        with db_lock:
            state = USER_STATES.get(cid)
        
        # СОСТОЯНИЕ: AI ЧАТ
        if state == 'ai_chat' and text:
            # Сначала показываем "печатает"
            send_typing(cid)
            
            # Отправляем статус обработки (2 шага - быстро)
            status = send_msg(cid, "🔄 ОБРАБОТКА: 0%")
            if status:
                msg_id = status.json()['result']['message_id']
                time.sleep(0.2)
                edit_msg(cid, msg_id, "🔄 ОБРАБОТКА: 50%")
                time.sleep(0.2)
                delete_msg(cid, msg_id)
            
            # Получаем ответ от ИИ (быстро)
            response = fast_ai_response(text)
            
            # Анимируем печать ответа
            animate_typing(cid, response, delay=0.05)  # Быстрая печать
            
            ADMIN_STATS['total_messages'] += 1
            with db_lock:
                USER_STATES.pop(cid, None)
            return
        
        # СОСТОЯНИЕ: ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ
        if state == 'generate_image' and text:
            # Статус генерации
            status = send_msg(cid, "🎨 ГЕНЕРАЦИЯ: 0%")
            if status:
                msg_id = status.json()['result']['message_id']
                time.sleep(0.3)
                edit_msg(cid, msg_id, "🎨 ГЕНЕРАЦИЯ: 50%")
                time.sleep(0.3)
                delete_msg(cid, msg_id)
            
            # Генерируем картинку
            send_typing(cid)
            img_url = generate_image_fixed(text)
            
            if img_url:
                send_photo(cid, img_url, f"🖼 <b>Запрос:</b> {text}")
                ADMIN_STATS['total_images'] += 1
            else:
                send_msg(cid, "⚠️ Не удалось сгенерировать. Попробуй еще раз.")
            
            with db_lock:
                USER_STATES.pop(cid, None)
            return
        
        # СОСТОЯНИЕ: СООБЩЕНИЕ АДМИНУ
        if state == 'message_admin' and text:
            send_msg(Config.ADMIN_ID, f"📨 <b>От {user_name} (ID: {cid}):</b>\n\n{text}")
            animate_typing(cid, "✅ Сообщение отправлено админу!", delay=0.03)
            with db_lock:
                USER_STATES.pop(cid, None)
            return
        
        # ЛЮБОЙ ТЕКСТ (если не в состоянии) - тоже через ИИ
        if text and not text.startswith("/"):
            send_typing(cid)
            
            # Быстрая обработка
            status = send_msg(cid, "🔄 0%")
            if status:
                msg_id = status.json()['result']['message_id']
                time.sleep(0.2)
                edit_msg(cid, msg_id, "🔄 50%")
                time.sleep(0.2)
                delete_msg(cid, msg_id)
            
            response = fast_ai_response(text)
            animate_typing(cid, response, delay=0.05)
            ADMIN_STATS['total_messages'] += 1
    
    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            send_msg(cid, "⚠️ Ошибка. Попробуй еще раз.")
        except:
            pass

# ==============================================================================
# 🚀 ЗАПУСК
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"TITAN {Config.VERSION} starting on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, threaded=True)
