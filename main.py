import os, requests, base64, time, random, json, datetime
from flask import Flask, request

app = Flask(__name__)

# --- КОНФИГ ---
TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
ADMIN_ID = 5626603417 
USERS_FILE = "users.txt"
LOGS_FILE = "logs.txt"
BC_HISTORY = "bc_history.json"
ADMIN_STATE = {}

def send_tg(chat_id, text=None, photo=None, kb=None, reply_kb=None, doc=None):
    url = f"https://api.telegram.org/bot{TOKEN}/"
    p = {"chat_id": chat_id, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: p["reply_markup"] = {"inline_keyboard": kb}
    if reply_kb: p["reply_markup"] = reply_kb
    if doc:
        return requests.post(url + "sendDocument", data=p, files={'document': open(doc, 'rb')}).json()
    if photo:
        p.update({"photo": photo, "caption": text})
        return requests.post(url + "sendPhoto", json=p).json()
    p["text"] = text
    return requests.post(url + "sendMessage", json=p).json()

def edit_tg(chat_id, mid, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/editMessageText", 
                  json={"chat_id": chat_id, "message_id": mid, "text": text, "parse_mode": "HTML"})

def delete_tg(chat_id, mid):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": mid})

def real_progress(chat_id, task):
    res = send_tg(chat_id, f"📡 <b>{task}</b>\n└ ⏳ <code>1%</code>")
    mid = res.get("result", {}).get("message_id")
    if mid:
        curr = 1
        for _ in range(4):
            curr += random.randint(20, 25)
            if curr > 99: curr = 99
            time.sleep(0.4)
            edit_tg(chat_id, mid, f"📡 <b>{task}</b>\n└ ⏳ <code>{curr}%</code>")
        return mid
    return None

def get_ai(prompt, img_b64=None, voice_b64=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img_b64: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
    if voice_b64: parts.append({"inline_data": {"mime_type": "audio/ogg", "data": voice_b64}})
    try:
        r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=15).json()
        return r['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"🛰 Ошибка Gemini: {str(e)}"

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "SYSTEM_V22_READY", 200
    data = request.get_json()
    if not data: return "OK", 200

    # CALLBACKS (Админ-меню)
    if "callback_query" in data:
        cb = data["callback_query"]
        cid, call = cb["message"]["chat"]["id"], cb["data"]
        if cid == ADMIN_ID:
            if call == "adm_bc":
                ADMIN_STATE[cid] = "waiting_bc"
                send_tg(cid, "📝 Отправь сообщение для рассылки (текст или фото):")
            elif call == "adm_rev":
                if os.path.exists(BC_HISTORY):
                    with open(BC_HISTORY, "r") as f: h = json.load(f)
                    for uid, mid in h.items(): delete_tg(uid, mid)
                    os.remove(BC_HISTORY)
                    send_tg(cid, "🗑 Рассылка отозвана.")
                else: send_tg(cid, "❌ Пусто.")
            elif call == "adm_logs": send_tg(cid, "📑 Логи:", doc=LOGS_FILE)
            elif call == "adm_stat":
                with open(USERS_FILE, "r") as f: u_count = len(f.read().splitlines())
                send_tg(cid, f"📊 Юзеров: <b>{u_count}</b>")
        return "OK", 200

    if "message" not in data: return "OK", 200
    msg = data["message"]
    chat_id, text = msg["chat"]["id"], msg.get("text", "")
    caption = msg.get("caption", "")

    # РЕГИСТРАЦИЯ
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "a").close()
    with open(USERS_FILE, "r+") as f:
        if str(chat_id) not in f.read(): f.write(f"{chat_id}\n")
    if text or caption:
        with open(LOGS_FILE, "a") as l: l.write(f"[{datetime.datetime.now()}] {chat_id}: {text or caption}\n")

    # --- ЖИРНОЕ СТАРТОВОЕ МЕНЮ ---
    if text == "/start":
        welcome_text = (
            "🚀 <b>Добро пожаловать в Gemini Chat TG!</b>\n\n"
            "Я — твой универсальный ИИ-ассистент нового поколения. Вот что я умею:\n\n"
            "🧠 <b>Текстовый разум:</b> Отвечаю на любые вопросы, пишу код и тексты.\n"
            "🖼 <b>Генерация образов:</b> Напиши «Нарисуй [запрос]», и я создам арт.\n"
            "🎤 <b>Голосовой ввод:</b> Просто отправь голосовое, и я пойму тебя.\n"
            "👁 <b>Зрение:</b> Отправь фото, и я опишу, что на нем изображено.\n\n"
            "<i>Используй кнопки снизу для удобного управления!</i>"
        )
        # Кнопки снизу (Reply Keyboard)
        reply_kb = {
            "keyboard": [
                [{"text": "🎨 Нарисуй стул"}, {"text": "🖼 Нарисуй картину"}],
                [{"text": "📊 Моя статистика"}, {"text": "ℹ️ О боте"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        send_tg(chat_id, welcome_text, reply_kb=reply_kb)
        return "OK", 200

    # ИНФО-КНОПКИ
    if text == "ℹ️ О боте":
        send_tg(chat_id, "💎 <b>Gemini Chat TG</b>\nВерсия: 22.0 Stable\nДвижок: Gemini 1.5 Flash\nСтатус: Online 🟢")
        return "OK", 200

    # АДМИНКА
    if chat_id == ADMIN_ID:
        if text == "/admin":
            kb = [[{"text": "📢 Рассылка", "callback_data": "adm_bc"}, {"text": "🗑 Откат", "callback_data": "adm_rev"}],
                  [{"text": "📑 Логи", "callback_data": "adm_logs"}, {"text": "📊 Стата", "callback_data": "adm_stat"}]]
            send_tg(chat_id, "👑 <b>АДМИН-ЦЕНТР</b>", kb=kb)
            return "OK", 200
        
        if ADMIN_STATE.get(chat_id) == "waiting_bc":
            with open(USERS_FILE, "r") as f: users = f.read().splitlines()
            h = {}
            for u in users:
                try:
                    res = send_tg(u, text=caption, photo=msg["photo"][-1]["file_id"]) if "photo" in msg else send_tg(u, text)
                    if res.get("ok"): h[u] = res["result"]["message_id"]
                except: continue
            with open(BC_HISTORY, "w") as f: json.dump(h, f)
            send_tg(ADMIN_ID, "✅ Рассылка выполнена!")
            ADMIN_STATE.clear()
            return "OK", 200

    # ОБРАБОТКА ЗАПРОСОВ
    if text or "photo" in msg or "voice" in msg:
        full_q = (text + caption).lower()
        trigs = ["нарисуй", "сгенерируй", "создай", "draw", "картину"]
        
        if any(w in full_q for w in trigs):
            mid = real_progress(chat_id, "Создание образа")
            p = full_q
            for w in trigs: p = p.replace(w, "")
            p = p.strip() or "abstract art"
            img_url = f"https://image.pollinations.ai/prompt/{p}?nologo=true&width=1024&height=1024"
            
            if mid: delete_tg(chat_id, mid)
            
            # Отправляем админу, уведомляем юзера
            if chat_id != ADMIN_ID:
                send_tg(ADMIN_ID, f"🔔 Юзер {chat_id} заказал: {p}")
            send_tg(ADMIN_ID, f"✨ <b>Готово по запросу:</b> {p}", photo=img_url)
            
            if chat_id != ADMIN_ID:
                send_tg(chat_id, "✅ Твой запрос обработан. Результат отправлен админу.")
            return "OK", 200

        # Текст / Голос / Фото
        mid = real_progress(chat_id, "Gemini Анализ")
        img_b64, voice_b64 = None, None
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()["result"]["file_path"]
            img_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
        if "voice" in msg:
            fid = msg["voice"]["file_id"]
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()["result"]["file_path"]
            voice_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')

        ans = get_ai(text or caption or "Опиши контент", img_b64=img_b64, voice_b64=voice_b64)
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, ans)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
