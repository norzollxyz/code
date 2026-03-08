import os, requests, json, logging
from flask import Flask, request

# Логирование только критических ошибок для скорости
logging.basicConfig(level=logging.ERROR)
app = Flask(__name__)

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 PRIME"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GROQ_KEY = "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"
    ADMIN_ID = 5378010557
    PORT = int(os.environ.get("PORT", 10000))

USERS_DB = set()
WAITING_FOR_CONTENT = {}

# ==============================================================================
# 🧠 МОЗГ (ИИ И ГЕНЕРАЦИЯ)
# ==============================================================================
def get_ai_response(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {Config.GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "Ты ТИТАН. Мощный ИИ. Отвечай коротко и по делу на русском."},
                     {"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10).json()
        return r['choices'][0]['message']['content']
    except: return "⚠️ Ошибка связи с ядром."

# ==============================================================================
# 🕹 ИНТЕРФЕЙС (50+ КОМАНД)
# ==============================================================================
def main_kb():
    # Огромная сетка для вида
    keys = [
        ["🤖 ТЕРМИНАЛ", "🎨 СОЗДАТЬ ФОТО"],
        ["📢 РАССЫЛКА", "📟 ПРОФИЛЬ"],
        ["⚙️ НАСТРОЙКИ", "🛡 ЗАЩИТА", "📊 СТАТЫ"],
        ["CMD_1", "CMD_2", "CMD_3", "CMD_4"],
        ["SYS_X", "NET_0", "DATA_Z", "LOG_V"],
        ["A1", "A2", "A3", "A4"], ["B1", "B2", "B3", "B4"],
        ["C1", "C2", "C3", "C4"], ["D1", "D2", "D3", "D4"]
    ]
    return {"keyboard": keys, "resize_keyboard": True}

def send_msg(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    return requests.post(url, json=payload)

# ==============================================================================
# 📡 ОБРАБОТКА (ИСПРАВЛЕННЫЙ ПОРТ)
# ==============================================================================
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def index():
    if request.method in ['GET', 'HEAD']:
        return "OK", 200 # Мгновенный ответ для Render

    data = request.get_json(silent=True)
    if not data or "message" not in data: return "OK", 200

    msg = data["message"]
    cid = msg["chat"]["id"]
    text = msg.get("text", "")
    USERS_DB.add(cid)

    # --- РАССЫЛКА (ШАГ 2: ПРИЕМ КОНТЕНТА) ---
    if cid == Config.ADMIN_ID and WAITING_FOR_CONTENT.get(cid):
        WAITING_FOR_CONTENT[cid] = False
        count = 0
        for uid in USERS_DB:
            res = requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage",
                                json={"chat_id": uid, "from_chat_id": cid, "message_id": msg["message_id"]})
            if res.status_code == 200: count += 1
        send_msg(cid, f"✅ Рассылка завершена! Узлов: {count}")
        return "OK", 200

    # --- КОМАНДЫ ---
    if text == "/start":
        send_msg(cid, "<b>ТИТАН V26 СИСТЕМА АКТИВНА</b>", main_kb())

    elif text == "📢 РАССЫЛКА":
        if cid == Config.ADMIN_ID:
            WAITING_FOR_CONTENT[cid] = True
            send_msg(cid, "📥 <b>ОЖИДАНИЕ КОНТЕНТА...</b>\nПришли текст, фото или пересылку.")
        else: send_msg(cid, "🛑 Отказ в доступе.")

    elif text == "🎨 СОЗДАТЬ ФОТО":
        send_msg(cid, "Используй: <code>/draw запрос</code>")

    elif text.startswith("/draw "):
        p = text.replace("/draw ", "")
        send_msg(cid, "⏳ <b>ГЕНЕРАЦИЯ...</b>")
        img = f"https://pollinations.ai/p/{requests.utils.quote(p)}?width=1024&height=1024"
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto", json={"chat_id": cid, "photo": img, "caption": "Готово!"})

    elif text == "📟 ПРОФИЛЬ":
        send_msg(cid, f"👤 Юзер: {cid}\n🔓 Доступ: {'ADMIN' if cid == Config.ADMIN_ID else 'USER'}")

    # --- ОБРАБОТКА ИИ ---
    elif text:
        # Визуал обработки
        load = send_msg(cid, "💿 <b>ОБРАБОТКА 45%...</b>")
        ans = get_ai_response(text)
        requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText",
                      json={"chat_id": cid, "message_id": load.json()['result']['message_id'],
                            "text": f"✅ <b>РЕЗУЛЬТАТ:</b>\n\n{ans}", "parse_mode": "HTML"})

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=Config.PORT)
    
