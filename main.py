import os, requests, json
from flask import Flask, request

class Config:
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    OPENROUTER_KEY = "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"
    # Render передает порт в переменную окружения PORT
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com"
    }
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        return r.json()['choices'][0]['message']['content']
    except:
        return "❌ Ошибка API или ключа."

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'GET':
        return f"TITAN ACTIVE ON PORT {Config.PORT}", 200
    
    data = request.get_json()
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        # Сразу отвечаем, чтобы лог зафиксировал активность
        res_text = get_ai_response(text) if text != "/start" else "🌌 TITAN ONLINE"
        
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": res_text})
    return "OK", 200

if __name__ == "__main__":
    # Выводим в логи для проверки
    print(f"--- STARTING TITAN ON PORT {Config.PORT} ---")
    app.run(host='0.0.0.0', port=Config.PORT)
    
