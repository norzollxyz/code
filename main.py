import os
import requests
import json
import logging
from flask import Flask, request
from datetime import datetime

# ==============================================================================
# 🛠 СИСТЕМНОЕ ЛОГИРОВАНИЕ И БАЗА ДАННЫХ
# ==============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TITAN-CORE")

USERS_DB = set()

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ СИСТЕМЫ
# ==============================================================================
class Config:
    VERSION = "V26.0 RENDER-PORT-FIX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    PORT = int(os.environ.get("PORT", 10000))
    ADMIN_ID = 5378010557  # Твой ID

app = Flask(__name__)

# ==============================================================================
# 🧠 AI ENGINE (GROQ / LLAMA 3.1)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "Ты — TITAN V26, ИИ-система высшего уровня. Твой создатель — admin. Общайся в стиле киберпанка, кратко и дерзко. Используй эмодзи."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        if 'choices' in res:
            return res['choices'][0]['message']['content']
        return f"⚠️ SYSTEM ERROR: {res.get('error', {}).get('message', 'Unknown')}"
    except Exception as e:
        return f"❌ CORE CRITICAL ERROR: {str(e)}"

# ==============================================================================
# 🕹 UI BUILDER & VISUALS
# ==============================================================================
def build_keyboard(menu_type):
    if menu_type == "main":
        return {
            "keyboard": [
                [{"text": "🤖 AI TERMINAL"}, {"text": "🔍 OSINT HUB"}],
                [{"text": "🛰 SYSTEM STATUS"}, {"text": "🛠 SETTINGS"}],
                [{"text": "📟 МОЙ ПРОФИЛЬ"}]
            ],
            "resize_keyboard": True
        }
    elif menu_type == "osint":
        return {
            "keyboard": [
                [{"text": "📱 Поиск: Номер"}, {"text": "📧 Поиск: Email"}, {"text": "🌐 Поиск: IP"}],
                [{"text": "🔙 ВЕРНУТЬСЯ"}]
            ],
            "resize_keyboard": True
        }
    return None

def send_msg(chat_id, text, keyboard=None):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(url, json=payload)

def notify_admin(text):
    send_msg(Config.ADMIN_ID, f"🔔 <b>[АЛЕРТ СИСТЕМЫ]</b>\n{text}")

# ==============================================================================
# 📡 ГЛАВНЫЙ ШЛЮЗ (ИСПРАВЛЕННЫЙ ПОРТ)
# ==============================================================================
# ДОБАВЛЕН МЕТОД HEAD, ЧТОБЫ RENDER НЕ ВЫДАВАЛ ОШИБКУ 415
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def index():
    # Отвечаем сканеру Render мгновенно
    if request.method in ['GET', 'HEAD']:
        return f"TITAN CORE {Config.VERSION} ACTIVE", 200

    # silent=True игнорирует ошибки формата данных
    update = request.get_json(silent=True)
    if not update or "message" not in update:
        return "OK", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    user_name = msg["from"].get("first_name", "Unknown")

    if chat_id not in USERS_DB:
        USERS_DB.add(chat_id)
        if chat_id != Config.ADMIN_ID:
            notify_admin(f"Новый пользователь: <code>{user_name}</code> (ID: {chat_id})")

    if text.startswith("/start"):
        welcome = (
            f"<b>┌── TITAN CORE {Config.VERSION} ──┐</b>\n"
            f"<b>│ User:</b> <code>{user_name}</code>\n"
            f"<b>│ Access:</b> <code>GRANTED</code>\n"
            f"<b>└── SYSTEM INITIALIZED ──┘</b>\n\n"
            "<i>Все узлы подключены. Ожидаю ввода...</i>"
        )
        send_msg(chat_id, welcome, build_keyboard("main"))

    elif text == "/admin":
        if chat_id == Config.ADMIN_ID:
            admin_panel = (
                "<b>⚡️ ROOT-ТЕРМИНАЛ TITAN</b>\n"
                "───────────────────\n"
                f"• <b>Юзеров:</b> <code>{len(USERS_DB)}</code>\n"
                "• <b>Команды:</b>\n"
                "<code>/broadcast [текст]</code> — Рассылка\n"
                "<code>/stats</code> — Сводка\n"
                "───────────────────"
            )
            send_msg(chat_id, admin_panel)
        else:
            send_msg(chat_id, "⚠️ <b>ACCESS DENIED</b>")

    elif text.startswith("/broadcast "):
        if chat_id == Config.ADMIN_ID:
            b_text = text.replace("/broadcast ", "")
            for uid in USERS_DB:
                send_msg(uid, f"📢 <b>СИСТЕМНОЕ СООБЩЕНИЕ:</b>\n\n{b_text}")
            send_msg(chat_id, "✅ Рассылка завершена.")

    elif text == "/stats" and chat_id == Config.ADMIN_ID:
        send_msg(chat_id, f"📊 <b>СТАТИСТИКА:</b>\nАктивных юзеров: {len(USERS_DB)}")

    elif text == "🛰 SYSTEM STATUS":
        send_msg(chat_id, "<b>🛰 МОНИТОРИНГ УЗЛОВ:</b>\n───────────────────\n• <b>Core:</b> <code>Llama-3.1</code>\n• <b>Platform:</b> <code>Render Cloud</code>\n───────────────────")

    elif text == "🔍 OSINT HUB":
        send_msg(chat_id, "📡 <b>Инициализация модулей...</b>\nВыберите цель:", build_keyboard("osint"))

    elif text == "🔙 ВЕРНУТЬСЯ":
        send_msg(chat_id, "🔄 Возврат в главный шлюз...", build_keyboard("main"))

    elif text == "🤖 AI TERMINAL":
        send_msg(chat_id, "🧠 <b>Канал открыт.</b>\nВведите запрос:")

    elif text == "📟 МОЙ ПРОФИЛЬ":
        rank = "ROOT ADMIN" if chat_id == Config.ADMIN_ID else "GUEST"
        send_msg(chat_id, f"<b>📟 ДАННЫЕ СУБЪЕКТА:</b>\n───────────────────\n• <b>Имя:</b> {user_name}\n• <b>ID:</b> <code>{chat_id}</code>\n• <b>Доступ:</b> <code>{rank}</code>\n───────────────────")

    elif text == "🛠 SETTINGS":
        send_msg(chat_id, "<b>🛠 НАСТРОЙКИ СИСТЕМЫ:</b>\n\n• <b>Шифрование:</b> <code>AES-256</code>\n• <b>Интерфейс:</b> <code>Neon-Dark</code>")

    elif text.startswith("📱 Поиск:") or text.startswith("📧 Поиск:") or text.startswith("🌐 Поиск:"):
        send_msg(chat_id, f"⚠️ <b>МОДУЛЬ В РАЗРАБОТКЕ</b>\nРежим: <code>{text}</code>")

    else:
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
        response = get_ai_response(text)
        send_msg(chat_id, f"<b>[ TITAN_AI ]</b>\n\n{response}")

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
            
