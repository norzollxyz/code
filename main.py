import os, json, requests, threading
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 PORT-FIX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyBx67MYTv6YgGSLfeR5Vld93XwAHHHYQFE"
    # Render ВСЕГДА ждет порт 10000 или тот, что в переменной PORT
    PORT = int(os.environ.get("PORT", 10000))

# ==============================================================================
# 🚀 ЯДРО ИИ И БОТА (УПРОЩЕНО ДЛЯ СТАБИЛЬНОСТИ)
# ==============================================================================
app = Flask(__name__)

def get_ai_response(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=15).json()
        return r['candidates'][0]['content']['parts'][0]['text']
    except:
        return "❌ Ошибка связи с ИИ. Проверь ключ."

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET': 
        return "TITAN IS ALIVE", 200
    
    upd = request.get_json()
    if upd and "message" in upd:
        m = upd["message"]
        chat_id = m["chat"]["id"]
        text = m.get("text", "")

        if text == "/start":
            msg = "🌌 TITAN V26.0 ONLINE\nПорт успешно открыт!"
        else:
            msg = get_ai_response(text)
        
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg})
    
    return "OK", 200

# ==============================================================================
# ⚡ ЗАПУСК (КРИТИЧЕСКИ ВАЖНО)
# ==============================================================================
if __name__ == "__main__":
    # Хост 0.0.0.0 обязателен для Render!
    app.run(host='0.0.0.0', port=Config.PORT)
    
