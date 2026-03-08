import os, requests, json
from flask import Flask, request

# ==============================================================================
# ⚙️ CONFIGURATION (OMEGA-VISUAL)
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA-VISUAL"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 🧠 AI CORE (GROQ / LLAMA 3.1)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {Config.GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Ты — TITAN V26, продвинутый ИИ-терминал. Твой стиль: хай-тек, краткость, использование эмодзи. Ты помогаешь с кодом, OSINT и системным администрированием."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        return res['choices'][0]['message']['content'] if 'choices' in res else "⚠️ Ошибка нейросети."
    except:
        return "❌ Критическая ошибка ядра."

# ==============================================================================
# 🕹 UI & VISUALS
# ==============================================================================
def send_ui(chat_id, text, menu_type="main"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    
    if menu_type == "main":
        keyboard = [
            [{"text": "🤖 Спросить ИИ"}, {"text": "🔍 OSINT-Поиск"}],
            [{"text": "🛰 Статус системы"}, {"text": "🛠 Настройки"}]
        ]
    elif menu_type == "osint":
        keyboard = [
            [{"text": "📱 Поиск по номеру"}, {"text": "📧 Поиск по Email"}],
            [{"text": "🔙 В главное меню"}]
        ]
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"keyboard": keyboard, "resize_keyboard": True}
    }
    requests.post(url, json=payload)

# ==============================================================================
# 📡 GATEWAY
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} ONLINE", 200
    
    data = request.get_json()
    if not data or "message" not in data: return "OK", 200
    
    m = data["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    # --- ОБРАБОТКА КОМАНД ---
    if txt == "/start":
        welcome = (
            "<b>┌── TITAN SYSTEM ──┐</b>\n"
            "<b>│ Status:</b> <code>ONLINE</code>\n"
            "<b>│ Version:</b> <code>V26.0-OMEGA</code>\n"
            "<b>└── SYSTEM READY ──┘</b>\n\n"
            "<i>Добро пожаловать в терминал управления. Выберите модуль для активации:</i>"
        )
        send_ui(cid, welcome)

    elif txt == "🛰 Статус системы":
        status_msg = (
            "<b>💠 МОНИТОРИНГ TITAN</b>\n\n"
            f"<b>• Ядро:</b> <code>Llama-3.1 (Groq)</code>\n"
            f"<b>• Аптайм:</b> <code>Stable</code>\n"
            f"<b>• Порт:</b> <code>{Config.PORT}</code>\n"
            "<b>• Пинг:</b> <code>~0.2s</code>"
        )
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": status_msg, "parse_mode": "HTML"})

    elif txt == "🔍 OSINT-Поиск":
        send_ui(cid, "📡 <b>Вход в OSINT-терминал...</b>\nВыберите метод поиска:", menu_type="osint")

    elif txt == "🔙 В главное меню":
        send_ui(cid, "🔄 Возврат в главный шлюз...")

    elif txt == "🛠 Настройки":
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": "⚙️ <b>Конфигурация:</b>\n\n• API: <i>ACTIVE</i>\n• Stream: <i>OFF</i>\n• Security: <i>MAX</i>", "parse_mode": "HTML"})

    elif txt == "/admin":
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": "🛑 <b>ACCESS DENIED</b>\nТребуется ключ администратора уровня 4.", "parse_mode": "HTML"})

    else:
        # Режим ИИ
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": cid, "action": "typing"})
        ai_res = get_ai_response(txt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"<b>TITAN:</b>\n\n{ai_res}", "parse_mode": "HTML"})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
        
