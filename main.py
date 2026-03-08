import os, requests, json
from flask import Flask, request

class Config:
    VERSION = "V26.0 RENDER-FIX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    OPENROUTER_KEY = "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"
    # Принудительно берем порт 10000, если переменная пустая
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
    except Exception as e:
        return f"❌ Ошибка API: {str(e)}"

@app.route('/', methods=['POST', 'GET'])
def index():
    # Это то, что проверяет Render своим сканером
    if request.method == 'GET':
        return f"TITAN SYSTEM {Config.VERSION} IS ALIVE", 200
    
    # Логируем в консоль Render, что пришел запрос
    print("--- Входящий запрос от Telegram ---")
    
    data = request.get_json()
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if text == "/start":
            res_text = "🌌 TITAN RENDER-FIX ONLINE\nПорт успешно пробит!"
        else:
            res_text = get_ai_response(text)
        
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": res_text, "parse_mode": "HTML"})
    
    return "OK", 200

if __name__ == "__main__":
    # Хост 0.0.0.0 и порт обязательны!
    app.run(host='0.0.0.0', port=Config.PORT)
        
