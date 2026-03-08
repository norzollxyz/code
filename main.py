import os, requests, json
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 ULTIMATE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой ключ OpenRouter
    OPENROUTER_KEY = "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"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 🧠 МОЗГ (OPENROUTER / GPT-4o-mini)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "TITAN_ULTIMATE"
    }
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Ты — TITAN, мощный ИИ-помощник. Отвечай кратко, дерзко и по делу. Используй эмодзи."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        res = r.json()
        
        if 'choices' in res and len(res['choices']) > 0:
            return res['choices'][0]['message']['content']
        
        if 'error' in res:
            return f"⚠️ Ошибка API: {res['error'].get('message', 'Баланс или Ключ')}"
        
        return "❌ Система перегружена. Попробуй позже."
    except Exception as e:
        return f"❌ Ошибка связи: {str(e)}"

# ==============================================================================
# 🕹 МЕНЮ И КНОПКИ
# ==============================================================================
def send_main_menu(chat_id, text="🌌 Главное меню TITAN:"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    reply_markup = {
        "keyboard": [
            [{"text": "🤖 Спросить ИИ"}, {"text": "📊 Статус системы"}],
            [{"text": "🛠 Настройки"}, {"text": "ℹ️ Инфо"}]
        ],
        "resize_keyboard": True
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    requests.post(url, json=payload)

# ==============================================================================
# 📡 ОБРАБОТЧИК ЗАПРОСОВ
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} IS RUNNING ON PORT {Config.PORT}", 200
    
    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200
    
    m = data["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    # Логика команд
    if txt == "/start":
        send_main_menu(cid, "🌌 <b>TITAN SYSTEM ONLINE</b>\n\nДобро пожаловать в терминал управления. Все системы в норме.")
    
    elif txt == "📊 Статус системы":
        msg = f"🛰 <b>Статус:</b> Online\n🛠 <b>Версия:</b> {Config.VERSION}\n⚡️ <b>Порт:</b> {Config.PORT}"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    elif txt == "ℹ️ Инфо":
        msg = "TITAN V26.0 — это высокотехнологичный бот на базе GPT-4o-mini. Развернут на Render."
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg})

    else:
        # Обычный запрос к ИИ
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": cid, "action": "typing"})
        ai_res = get_ai_response(txt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": ai_res})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
