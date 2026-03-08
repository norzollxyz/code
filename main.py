import os, requests, json
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (GROQ-FINAL)
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA-FLOW"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой новый ключ Groq (принудительно в нижнем регистре для стабильности)
    GROQ_KEY = "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"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 🧠 МОЗГ (GROQ / LLAMA 3.1)
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
            {"role": "system", "content": "Ты — TITAN V26. Отвечай кратко, четко, без лишней воды. Тон уверенный и техничный."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        if 'choices' in res:
            return res['choices'][0]['message']['content']
        else:
            err = res.get('error', {}).get('message', 'Неизвестная ошибка')
            return f"⚠️ Ошибка API: {err}\n\nПроверь ключ тут: https://console.groq.com/keys"
    except Exception as e:
        return f"❌ Ошибка сети: {str(e)}"

# ==============================================================================
# 🕹 МЕНЮ
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
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": reply_markup}
    requests.post(url, json=payload)

# ==============================================================================
# 📡 ГЛАВНЫЙ ШЛЮЗ
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} ACTIVE", 200
    
    data = request.get_json()
    if not data or "message" not in data:
        return "OK", 200
    
    m = data["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    if txt == "/start":
        send_main_menu(cid, "🌌 <b>TITAN V26.0: GROQ OMEGA</b>\n\nСвязь установлена. Система готова к работе.")
    
    elif txt == "🛰 Статус":
        msg = f"🟢 <b>Статус:</b> ONLINE\n🛠 <b>Версия:</b> {Config.VERSION}\n⚡️ <b>Процессор:</b> Llama-3.1-8B-Instant"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    elif txt == "ℹ️ Инфо":
        msg = "TITAN V26.0 — Высокоскоростной терминал на базе Groq Cloud. Скорость ответа < 0.5 сек."
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg})

    else:
        # Индикация "печатает"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", json={"chat_id": cid, "action": "typing"})
        ai_res = get_ai_response(txt)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": ai_res})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
