import os, requests, json
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (GROQ-STABLE)
# ==============================================================================
class Config:
    VERSION = "V26.0 GROQ-SPEED"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой ключ Groq:
    GROQ_KEY = "Gsk_ai97zf6OjIMxe3ig2U9kWGdyb3FYPjvSGDMeq641ibpXfPKZLk6l"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 🧠 МОЗГ (GROQ / LLAMA 3.1 8B)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant", # Самая быстрая модель на текущий момент
        "messages": [
            {"role": "system", "content": "Ты — TITAN V26, мощный ИИ. Твои ответы четкие, быстрые и дерзкие. Помогай юзеру во всем."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        if 'choices' in res:
            return res['choices'][0]['message']['content']
        else:
            return f"⚠️ Ошибка Groq: {res.get('error', {}).get('message', 'Неизвестная ошибка')}"
    except Exception as e:
        return f"❌ Ошибка сети: {str(e)}"

# ==============================================================================
# 🕹 МЕНЮ И КНОПКИ
# ==============================================================================
def send_main_menu(chat_id, text="🌌 TITAN SYSTEM ONLINE"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    reply_markup = {
        "keyboard": [
            [{"text": "🤖 Спросить ИИ"}, {"text": "🛰 Статус"}],
            [{"text": "ℹ️ Инфо"}]
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
# 📡 ГЛАВНЫЙ ОБРАБОТЧИК
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} IS ALIVE", 200
    
    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200
    
    m = data["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    if txt == "/start":
        send_main_menu(cid, "🌌 <b>TITAN V26.0: GROQ EDITION</b>\n\nГемини отправлен на свалку. Теперь работаем на Llama 3. Жду команд, босс.")
    
    elif txt == "🛰 Статус":
        msg = f"🟢 <b>Статус:</b> Online\n🛠 <b>Версия:</b> {Config.VERSION}\n⚡️ <b>Ядро:</b> Llama-3.1-8B-Instant"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    elif txt == "ℹ️ Инфо":
        msg = "TITAN V26.0 — Перезагрузка. Прямое подключение к мощностям Groq Cloud."
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg})

    elif txt == "🤖 Спросить ИИ":
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": "Я слушаю. Что хочешь узнать?"})

    else:
        # Эффект "печатает"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": cid, "action": "typing"})
        ai_res = get_ai_response(txt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": ai_res})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
