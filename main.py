import os, json, requests
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (GPT EDITION)
# ==============================================================================
class Config:
    VERSION = "V26.0 GPT-STABLE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой ключ OpenRouter:
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
        "HTTP-Referer": "https://render.com", # Обязательно для OpenRouter
        "X-Title": "TITAN BOT"
    }
    payload = {
        "model": "openai/gpt-4o-mini", 
        "messages": [
            {"role": "system", "content": "Ты — TITAN, мощный ИИ-помощник. Отвечай кратко и по делу."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        res = r.json()
        if 'choices' in res:
            return res['choices'][0]['message']['content']
        else:
            error_info = res.get('error', {}).get('message', 'Ошибка авторизации')
            return f"❌ Ошибка OpenRouter: {error_info}"
    except Exception as e:
        return f"❌ Ошибка сети: {str(e)}"

# ==============================================================================
# 📡 ОБРАБОТЧИК ТЕЛЕГРАМ
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def main_gateway():
    if request.method == 'GET': 
        return f"TITAN {Config.VERSION} IS RUNNING ON PORT {Config.PORT}", 200
    
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    if txt == "/start":
        msg = "🌌 <b>TITAN GPT-STABLE</b>\nСвязь с OpenRouter установлена. Я готов к работе!"
    else:
        # Показываем, что бот печатает
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", 
                      json={"chat_id": cid, "action": "typing"})
        msg = get_ai_response(txt)
    
    # Отправка ответа
    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", 
                  json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    return "OK", 200

if __name__ == "__main__":
    # Запуск на 0.0.0.0 для Render
    app.run(host='0.0.0.0', port=Config.PORT)
                          
