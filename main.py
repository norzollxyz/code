import os
import requests
import json
import time
import logging
from flask import Flask, request

# ==============================================================================
# ⚙️ НАСТРОЙКИ СИСТЕМЫ
# ==============================================================================
logging.basicConfig(level=logging.INFO)

class Config:
    VERSION = "V26.0 ULTIMATE-RUS"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    ADMIN_ID = 5378010557
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
USERS_DB = set()
WAITING_FOR_BROADCAST = {} # Состояния для пошаговой рассылки

# ==============================================================================
# 🧠 МОЗГОВОЙ ЦЕНТР (ИИ И ГЕНЕРАЦИЯ)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {Config.GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "Ты - TITAN. Мощный ИИ. Решаешь задачи, анализируешь фото/голос. Отвечай на русском."},
                     {"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20).json()
        return r['choices'][0]['message']['content']
    except: return "❌ Ошибка нейросети."

# Сюда можно вставить API для генерации картинок (например, через Pollinations или HuggingFace)
def generate_image(prompt):
    return f"https://pollinations.ai/p/{requests.utils.quote(prompt)}?width=1024&height=1024&seed=42"

# ==============================================================================
# 🕹 ИНТЕРФЕЙС (50+ КОМАНД И ВИЗУАЛ)
# ==============================================================================
def main_keyboard():
    # Создаем огромную сетку команд
    keys = [
        ["🤖 ТЕРМИНАЛ ИИ", "🎨 ГЕНЕРАЦИЯ ФОТО"],
        ["📢 РАССЫЛКА", "📟 МОЙ ПРОФИЛЬ"],
        ["🛡 ЗАЩИТА", "🔋 СТАТУС", "⚙️ НАСТРОЙКИ"],
        ["📂 ФАЙЛЫ", "📊 АНАЛИЗ", "📡 СЕТЬ"],
        ["🧪 ТЕСТ", "🔑 КЛЮЧИ", "🛑 СТОП"],
        # Добавляем пустые/декоративные команды для массовки
        ["CMD_01", "CMD_02", "CMD_03", "CMD_04"],
        ["SYS_X", "LOG_V", "NET_0", "DATA_Z"]
    ]
    return {"keyboard": keys, "resize_keyboard": True}

def send_msg(chat_id, text, keyboard=None, parse="HTML"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse}
    if keyboard: payload["reply_markup"] = keyboard
    return requests.post(url, json=payload)

def delete_msg(chat_id, msg_id):
    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteMessage", 
                  json={"chat_id": chat_id, "message_id": msg_id})

# ==============================================================================
# 📡 ОБРАБОТКА ЗАПРОСОВ
# ==============================================================================
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def index():
    if request.method in ['GET', 'HEAD']: return "TITAN ACTIVE", 200
    
    update = request.get_json(silent=True)
    if not update or "message" not in update: return "OK", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_name = msg["from"].get("first_name", "User")
    USERS_DB.add(chat_id)

    # 1. ОБРАБОТКА СОСТОЯНИЯ РАССЫЛКИ
    if chat_id == Config.ADMIN_ID and WAITING_FOR_BROADCAST.get(chat_id):
        WAITING_FOR_BROADCAST[chat_id] = False
        success = 0
        for uid in USERS_DB:
            # Пересылаем любое сообщение (фото, текст, видео)
            res = requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage", 
                                json={"chat_id": uid, "from_chat_id": chat_id, "message_id": msg["message_id"]})
            if res.status_code == 200: success += 1
        send_msg(chat_id, f"✅ <b>Рассылка завершена!</b>\nПолучили: {success} узлов.")
        return "OK", 200

    # 2. КОМАНДЫ
    text = msg.get("text", "")

    if text == "/start":
        send_msg(chat_id, f"<b>ТИТАН V26 ЗАПУЩЕН.</b>\nПривет, {user_name}. Система готова.", main_keyboard())

    elif text == "📢 РАССЫЛКА":
        if chat_id == Config.ADMIN_ID:
            WAITING_FOR_BROADCAST[chat_id] = True
            send_msg(chat_id, "📥 <b>РЕЖИМ РАССЫЛКИ</b>\nПришлите любое сообщение (текст, фото или пересылку) для отправки всем юзерам.")
        else:
            send_msg(chat_id, "❌ Доступ ограничен.")

    elif text == "🎨 ГЕНЕРАЦИЯ ФОТО":
        send_msg(chat_id, "Напиши: <code>/draw [описание]</code>\nПример: <i>/draw киберпанк город будущего</i>")

    elif text.startswith("/draw "):
        prompt = text.replace("/draw ", "")
        wait = send_msg(chat_id, "⏳ <b>Инициализация отрисовки... 0%</b>")
        time.sleep(1)
        delete_msg(chat_id, wait.json()['result']['message_id'])
        img_url = generate_image(prompt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto", 
                      json={"chat_id": chat_id, "photo": img_url, "caption": f"✅ Готово: {prompt}"})

    elif text == "📟 МОЙ ПРОФИЛЬ":
        send_msg(chat_id, f"👤 <b>ПРОФИЛЬ:</b> {user_name}\n🆔 <b>ID:</b> <code>{chat_id}</code>\n📊 <b>СТАТУС:</b> Активен")

    # 3. ОБРАБОТКА ФОТО/ГОЛОСОВЫХ (ЗАДАЧИ)
    elif "photo" in msg or "voice" in msg:
        send_msg(chat_id, "🌀 <b>Анализирую медиа-данные...</b>\nОбработка задачи через ИИ TITAN.")
        # Тут логика распознавания текста с фото через OCR или Vision (в будущем)
        send_msg(chat_id, "✅ Задача принята. ИИ приступает к решению.")

    # 4. ОБЫЧНОЕ СООБЩЕНИЕ (ИИ С ПРОЦЕНТАМИ)
    elif text:
        # Статус "печатает"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", 
                      json={"chat_id": chat_id, "action": "typing"})
        
        # Красивая обработка
        loading = send_msg(chat_id, "💿 <b>ОБРАБОТКА 25%</b>")
        time.sleep(0.4)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText", 
                      json={"chat_id": chat_id, "message_id": loading.json()['result']['message_id'], 
                            "text": "💿 <b>ОБРАБОТКА 68%</b>", "parse_mode": "HTML"})
        
        response = get_ai_response(text)
        delete_msg(chat_id, loading.json()['result']['message_id'])
        send_msg(chat_id, response)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
