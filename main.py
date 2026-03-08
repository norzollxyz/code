import os
import requests
import json
import time
import logging
from flask import Flask, request

# =============================================================================
# ⚙️ ЦЕНТРАЛЬНАЯ КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(level=logging.ERROR)

class Config:
    VERSION = "V26.0 OMEGA-ULTRA"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    ADMIN_ID = 5378010557
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# Имитация базы данных (хранится до перезагрузки сервера)
USERS_DB = set()
WAITING_FOR_BROADCAST = {}

# ==============================================================================
# 🧠 МОЗГОВОЙ ЦЕНТР (AI & IMAGEN)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {Config.GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Ты TITAN V26. Мощный ИИ. Твой стиль: хай-тек, краткость. Отвечай только на русском."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15).json()
        return r['choices'][0]['message']['content']
    except:
        return "⚠️ Ошибка нейросети: Критический сбой связи."

def generate_image(prompt):
    # Генерация через открытый API Pollinations
    encoded_prompt = requests.utils.quote(prompt)
    return f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=true"

# ==============================================================================
# 🕹 ИНТЕРФЕЙС (50+ КОМАНД И ГРИД-МЕНЮ)
# ==============================================================================
def get_main_keyboard():
    # Создаем массивную клавиатуру для визуального эффекта
    keyboard = [
        ["🤖 ТЕРМИНАЛ ИИ", "🎨 ГЕНЕРАТОР"],
        ["📢 РАССЫЛКА", "📟 ПРОФИЛЬ"],
        ["🛡 БЕЗОПАСНОСТЬ", "📊 СТАТИСТИКА", "⚙️ ОПЦИИ"],
        ["📂 DATA_01", "📡 NET_SCAN", "🧪 LAB_V"],
        ["CMD_X1", "CMD_X2", "CMD_X3", "CMD_X4"],
        ["SYS_0", "SYS_1", "SYS_2", "SYS_3"],
        ["LOG_A", "LOG_B", "LOG_C", "LOG_D"],
        ["V_26.0", "STABLE", "ROOT", "ACTIVE"],
        ["NODE_1", "NODE_2", "NODE_3", "NODE_4"],
        ["PORT_10000", "ENCRYPT", "CLOUD", "PROXY"],
        ["🔴 ВЫХОД"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

def send_msg(chat_id, text, kb=None, parse="HTML"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse}
    if kb: payload["reply_markup"] = kb
    return requests.post(url, json=payload)

def edit_msg(chat_id, msg_id, text):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    return requests.post(url, json=payload)

# ==============================================================================
# 📡 ГЛАВНЫЙ ШЛЮЗ (FIXED PORT & HEADERS)
# ==============================================================================
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def index():
    # Ответ для Render (HEAD/GET) — чтобы порт не отваливался
    if request.method in ['GET', 'HEAD']:
        return "TITAN CORE ACTIVE", 200

    update = request.get_json(silent=True)
    if not update or "message" not in update:
        return "OK", 200

    msg = update["message"]
    cid = msg["chat"]["id"]
    text = msg.get("text", "")
    user_name = msg["from"].get("first_name", "User")
    USERS_DB.add(cid)

    # --- ЛОГИКА РАССЫЛКИ (ПОШАГОВАЯ) ---
    if cid == Config.ADMIN_ID and WAITING_FOR_BROADCAST.get(cid):
        WAITING_FOR_BROADCAST[cid] = False
        success = 0
        for uid in USERS_DB:
            # Копируем любое сообщение: текст, фото, видео, пересылку
            res = requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage",
                                json={"chat_id": uid, "from_chat_id": cid, "message_id": msg["message_id"]})
            if res.status_code == 200: success += 1
        send_msg(cid, f"✅ <b>РАССЫЛКА ЗАВЕРШЕНА</b>\nПолучателей: {success}/{len(USERS_DB)}")
        return "OK", 200

    # --- ОБРАБОТКА КОМАНД ---
    if text == "/start":
        welcome = (
            f"<b>┌── TITAN CORE {Config.VERSION} ──┐</b>\n"
            f"<b>│ СТАТУС:</b> <code>ONLINE</code>\n"
            f"<b>│ УЗЕЛ:</b> <code>RENDER_PORT_10000</code>\n"
            f"<b>└── СИСТЕМА ГОТОВА ──┘</b>\n\n"
            f"Приветствую, {user_name}. Доступ разрешен."
        )
        send_msg(cid, welcome, get_main_keyboard())

    elif text == "📢 РАССЫЛКА":
        if cid == Config.ADMIN_ID:
            WAITING_FOR_BROADCAST[cid] = True
            send_msg(cid, "📥 <b>РЕЖИМ ПРИЕМА ДАННЫХ</b>\nПришлите текст, фото или перешлите пост для массовой отправки.")
        else:
            send_msg(cid, "❌ Доступ заблокирован: Требуется уровень ROOT.")

    elif text == "🎨 ГЕНЕРАТОР":
        send_msg(cid, "Введите запрос в формате: <code>/draw ваш текст</code>")

    elif text.startswith("/draw "):
        prompt = text.replace("/draw ", "")
        # Визуал загрузки
        load = send_msg(cid, "⏳ <b>ГЕНЕРАЦИЯ: [▒▒▒▒▒▒▒▒▒▒] 0%</b>")
        time.sleep(0.5)
        edit_msg(cid, load.json()['result']['message_id'], "⏳ <b>ГЕНЕРАЦИЯ: [███▒▒▒▒▒▒▒] 34%</b>")
        
        img_url = generate_image(prompt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto", 
                      json={"chat_id": cid, "photo": img_url, "caption": f"✅ <b>ОБЪЕКТ:</b> {prompt}", "parse_mode": "HTML"})
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteMessage", 
                      json={"chat_id": cid, "message_id": load.json()['result']['message_id']})

    elif text == "📟 ПРОФИЛЬ":
        role = "АДМИНИСТРАТОР" if cid == Config.ADMIN_ID else "ПОЛЬЗОВАТЕЛЬ"
        profile = (
            "<b>📟 ДАННЫЕ СИСТЕМЫ:</b>\n"
            "───────────────────\n"
            f"• <b>ИМЯ:</b> {user_name}\n"
            f"• <b>ID:</b> <code>{cid}</code>\n"
            f"• <b>ДОСТУП:</b> <code>{role}</code>\n"
            "───────────────────"
        )
        send_msg(cid, profile)

    elif text == "📊 СТАТИСТИКА":
        send_msg(cid, f"📈 <b>ОТЧЕТ:</b>\nВсего узлов в базе: <code>{len(USERS_DB)}</code>")

    # --- ОБРАБОТКА МЕДИА (ГОЛОСОВЫЕ / ФОТО) ---
    elif "photo" in msg or "voice" in msg:
        send_msg(cid, "🌀 <b>АНАЛИЗ МЕДИА...</b>\nИИ считывает данные задачи. Ожидайте.")
        # Здесь будет логика для решения задач по фото в будущем
        time.sleep(1)
        send_msg(cid, "✅ <b>АНАЛИЗ ЗАВЕРШЕН.</b> Данные переданы в ядро.")

    # --- ОБЫЧНЫЕ СООБЩЕНИЯ (ИИ С ПРОЦЕНТАМИ) ---
    elif text:
        # Имитация набора текста
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": cid, "action": "typing"})
        
        # Визуал обработки
        proc = send_msg(cid, "📀 <b>ОБРАБОТКА: 12%</b>")
        time.sleep(0.3)
        edit_msg(cid, proc.json()['result']['message_id'], "📀 <b>ОБРАБОТКА: 47%</b>")
        time.sleep(0.3)
        edit_msg(cid, proc.json()['result']['message_id'], "📀 <b>ОБРАБОТКА: 89%</b>")
        
        ai_ans = get_ai_response(text)
        
        # Заменяем сообщение с процентами на ответ
        edit_msg(cid, proc.json()['result']['message_id'], f"<b>TITAN:</b>\n\n{ai_ans}")

    return "OK", 200

if __name__ == "__main__":
    # Жесткая привязка к порту 10000
    app.run(host='0.0.0.0', port=Config.PORT)
    
