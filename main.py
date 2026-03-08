import os, json, requests
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (GPT-STABLE)
# ==============================================================================
class Config:
    VERSION = "V26.0 GPT-FINAL"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой новый ключ OpenRouter:
    OPENROUTER_KEY = "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"
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ==============================================================================
# 🧠 МОЗГ (OPENROUTER API)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com", # Важно для OpenRouter
        "X-Title": "TITAN_BOT_V26"
    }
    payload = {
        "model": "openai/gpt-4o-mini", # Самый быстрый и стабильный выбор
        "messages": [
            {"role": "system", "content": "Ты — TITAN, продвинутый ИИ. Отвечай четко, используй эмодзи и помогай юзеру во всем."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        res = r.json()
        if 'choices' in res:
            return res['choices'][0]['message']['content']
        else:
            # Вывод ошибки, если что-то не так с аккаунтом
            err_msg = res.get('error', {}).get('message', 'Ошибка авторизации')
            return f"❌ Ошибка OpenRouter: {err_msg}"
    except Exception as e:
        return f"❌ Ошибка связи: {str(e)}"

# ==============================================================================
# 📡 ОБРАБОТКА СООБЩЕНИЙ
# ==============================================================================
@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET':
        return f"TITAN {Config.VERSION} ONLINE. WAITING FOR TELEGRAM...", 200
    
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]
    cid = m["chat"]["id"]
    txt = m.get("text", "")

    if txt == "/start":
        msg = "🌌 <b>TITAN GPT-ULTIMATE</b>\nСистема запущена через OpenRouter. Жду твой первый запрос!"
    else:
        # Эффект "печатает"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction", 
                      json={"chat_id": cid, "action": "typing"})
        msg = get_ai_response(txt)
    
    # Отправка ответа пользователю
    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage", 
                  json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
    
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
