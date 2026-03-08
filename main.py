import os, requests, json, logging
from flask import Flask, request

# Логируем только важное
logging.basicConfig(level=logging.ERROR)
app = Flask(__name__)

class Config:
    VERSION = "V26.1 STABLE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    ADMIN_ID = 5378010557
    PORT = int(os.environ.get("PORT", 10000))

# Временная база в оперативе
USERS_DB = set()
WAITING_FOR_BROADCAST = {}

def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {Config.GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "Ты ТИТАН. Отвечай на русском, кратко."},
                     {"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10).json()
        return r['choices'][0]['message']['content']
    except: return "⚠️ Ошибка ИИ."

def get_kb():
    keys = [
        ["🤖 ТЕРМИНАЛ ИИ", "🎨 ГЕНЕРАТОР"], ["📢 РАССЫЛКА", "📟 ПРОФИЛЬ"],
        ["🛡 ЗАЩИТА", "📊 СТАТЫ", "⚙️ ОПЦИИ"], ["CMD_X1", "CMD_X2", "CMD_X3", "CMD_X4"],
        ["SYS_0", "SYS_1", "SYS_2", "SYS_3"], ["LOG_A", "LOG_B", "LOG_C", "LOG_D"]
    ]
    return {"keyboard": keys, "resize_keyboard": True}

def send(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    return requests.post(url, json=payload)

@app.route('/', methods=['POST', 'GET', 'HEAD'])
def index():
    # Мгновенный ответ для чека Render (ЭТО ГЛАВНОЕ)
    if request.method in ['GET', 'HEAD']:
        return "OK", 200

    update = request.get_json(silent=True)
    if not update or "message" not in update: return "OK", 200

    msg = update["message"]
    cid = msg["chat"]["id"]
    text = msg.get("text", "")
    USERS_DB.add(cid)

    # Рассылка
    if cid == Config.ADMIN_ID and WAITING_FOR_BROADCAST.get(cid):
        WAITING_FOR_BROADCAST[cid] = False
        for uid in USERS_DB:
            requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage",
                          json={"chat_id": uid, "from_chat_id": cid, "message_id": msg["message_id"]})
        send(cid, "✅ Рассылка выполнена.")
        return "OK", 200

    if text == "/start":
        send(cid, f"<b>ТИТАН {Config.VERSION} ОНЛАЙН</b>", get_kb())
    
    elif text == "📢 РАССЫЛКА":
        if cid == Config.ADMIN_ID:
            WAITING_FOR_BROADCAST[cid] = True
            send(cid, "📥 Пришлите контент для рассылки.")
    
    elif text.startswith("/draw "):
        p = text.replace("/draw ", "")
        img = f"https://pollinations.ai/p/{requests.utils.quote(p)}?width=1024&height=1024"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto", json={"chat_id": cid, "photo": img, "caption": "Готово!"})

    elif text:
        # Убрал циклы с процентами (они вешают поток), просто пишем статус
        load = send(cid, "💿 <b>ОБРАБОТКА...</b>")
        ans = get_ai_response(text)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText",
                      json={"chat_id": cid, "message_id": load.json()['result']['message_id'],
                            "text": f"<b>TITAN:</b>\n\n{ans}", "parse_mode": "HTML"})

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
