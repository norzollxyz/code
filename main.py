import os, json, requests
from flask import Flask, request

class Config:
    VERSION = "V26.0 FINAL-FIX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # ПРОВЕРЬ ЭТОТ КЛЮЧ ЕЩЕ РАЗ:
    GEMINI_API_KEY = "AIzaSyBx67MYTv6YgGSLfeR5Vld93XwAHHHYQFE"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

def get_ai_response(prompt):
    # Используем проверенную модель 1.5-flash без лишних приставок
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
        else:
            # Выводим конкретную ошибку от Google
            error_msg = res.get('error', {}).get('message', 'Неизвестная ошибка')
            return f"❌ Ошибка Google: {error_msg}"
    except Exception as e:
        return f"❌ Ошибка сети: {str(e)}"

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET': return "TITAN IS LIVE", 200
    
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    if txt == "/start":
        msg = "🌌 <b>TITAN V26.0: СИСТЕМА СТАБИЛИЗИРОВАНА</b>\nПорт активен, жду твой вопрос!"
    else:
        # Отправляем статус "печатает", чтобы ты видел, что бот думает
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", 
                      json={"chat_id": cid, "action": "typing"})
        msg = get_ai_response(txt)
    
    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", 
                  json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
