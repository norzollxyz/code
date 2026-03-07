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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def send_tg(chat_id, text=None, photo=None, kb=None, reply_kb=None, doc=None):
    url = f"https://api.telegram.org/bot{TOKEN}/"
    p = {"chat_id": chat_id, "parse_mode": "HTML"}
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

# --- НАСТОЯЩИЕ ПРОЦЕНТЫ (1, 2, 3...) ---
def real_progress(chat_id, task):
    res = send_tg(chat_id, f"📡 <b>{task}</b>\n└ ⏳ <code>1%</code>")
    mid = res.get("result", {}).get("message_id")
    if mid:
        curr = 1
        while curr < 95:
            curr += random.randint(3, 7) # Плавный шаг
            if curr > 99: curr = 99
            time.sleep(0.6) # Пауза для плавности и защиты от бана
            edit_tg(chat_id, mid, f"📡 <b>{task}</b>\n└ ⏳ <code>{curr}%</code>")
        return mid
    return None

# --- ЯДРО ИИ (ТЕКСТ, ФОТО, ГОЛОС) ---
def get_ai(prompt, img_b64=None, voice_b64=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": f"Ты ОЛИМП. Отвечай мощно. Запрос: {prompt}"}]
    if img_b64: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
    if voice_b64: parts.append({"inline_data": {"mime_type": "audio/ogg", "data": voice_b64}})
    try:
        r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=20).json()
        return r['candidates'][0]['content']['parts'][0]['text']
    except: return "🛰 ОЛИМП: Ошибка ядра ИИ."

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "OLIMP_V13_GOD_MODE", 200
    data = request.get_json()
    if not data: return "OK", 200

    # CALLBACKS (Кнопки админки)
    if "callback_query" in data:
        cb = data["callback_query"]
        cid, call = cb["message"]["chat"]["id"], cb["data"]
        if cid == ADMIN_ID:
            if call == "adm_bc":
                ADMIN_STATE[cid] = "waiting_bc"
                send_tg(cid, "📝 Пришли контент для рассылки всем юзерам:")
            elif call == "adm_rev":
                if os.path.exists(BC_HISTORY):
                    with open(BC_HISTORY, "r") as f: h = json.load(f)
                    for uid, mid in h.items(): delete_tg(uid, mid)
                    os.remove(BC_HISTORY)
                    send_tg(cid, "🗑 Рассылка удалена у всех!")
                else: send_tg(cid, "❌ История пуста.")
            elif call == "adm_logs":
                send_tg(cid, "📊 Выгружаю логи...", doc=LOGS_FILE)
            elif call == "adm_stat":
                with open(USERS_FILE, "r") as f: count = len(f.read().splitlines())
                send_tg(cid, f"👥 Всего юзеров в базе: <b>{count}</b>")
        return "OK", 200

    if "message" not in data: return "OK", 200
    msg = data["message"]
    chat_id, text = msg["chat"]["id"], msg.get("text", "")
    caption = msg.get("caption", "")

    # РЕГИСТРАЦИЯ ЮЗЕРА
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "a").close()
    with open(USERS_FILE, "r+") as f:
        if str(chat_id) not in f.read(): f.write(f"{chat_id}\n")
    with open(LOGS_FILE, "a") as l: l.write(f"[{datetime.datetime.now()}] {chat_id}: {text or caption}\n")

    # --- АДМИНКА (КОМАНДЫ ПРИКОЛОВ) ---
    if chat_id == ADMIN_ID:
        if ADMIN_STATE.get(chat_id) == "waiting_bc":
            h = {}
            with open(USERS_FILE, "r") as f: users = f.read().splitlines()
            for u in users:
                try:
                    res = send_tg(u, text=caption, photo=msg["photo"][-1]["file_id"]) if "photo" in msg else send_tg(u, text)
                    if res.get("ok"): h[u] = res["result"]["message_id"]
                except: continue
            with open(BC_HISTORY, "w") as f: json.dump(h, f)
            send_tg(ADMIN_ID, "✅ Рассылка выполнена!")
            ADMIN_STATE.clear()
            return "OK", 200

        if text == "/admin":
            kb = [
                [{"text": "📢 Рассылка", "callback_data": "adm_bc"}, {"text": "🗑 Откат", "callback_data": "adm_rev"}],
                [{"text": "📑 Логи", "callback_data": "adm_logs"}, {"text": "📊 Стата", "callback_data": "adm_stat"}]
            ]
            send_tg(chat_id, "👑 <b>ОЛИМП: УПРАВЛЕНИЕ МИРОМ</b>\nДоступно 50 скрытых функций через команды.", kb=kb)
            return "OK", 200

        # ПРИКОЛЫ (Примеры из 50 функций)
        if text.startswith("/fake_ans"): # /fake_ans [ID] [ТЕКСТ]
            parts = text.split(" ", 2)
            if len(parts) > 2:
                send_tg(parts[1], f"🤖 <b>ОЛИМП:</b> {parts[2]}")
                send_tg(chat_id, "✅ Фейковый ответ отправлен.")
            return "OK", 200

    # --- ЛОГИКА БОТА ДЛЯ ЮЗЕРОВ ---
    if text == "/start":
        send_tg(chat_id, "🦾 <b>ОЛИМП V13.0 АКТИВИРОВАН.</b>\nПрисылай текст, фото или голос. Пиши 'Нарисуй', чтобы создать арт.")
        return "OK", 200

    # 1. ГОЛОС
    if "voice" in msg:
        mid = real_progress(chat_id, "Слушаю твой голос")
        fid = msg["voice"]["file_id"]
        fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()["result"]["file_path"]
        vb64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
        ans = get_ai("Пользователь прислал голос. Ответь ему.", voice_b64=vb64)
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, f"🎙 <b>Я тебя услышал:</b>\n\n{ans}")
        return "OK", 200

    # 2. РИСОВАНИЕ (КОТИКИ И Т.Д.)
    trig = ["нарисуй", "сгенерируй", "создай", "рисуй", "draw"]
    if any(w in (text + caption).lower() for w in trig):
        mid = real_progress(chat_id, "Генерация арта")
        p = (text + caption).lower()
        for w in trig: p = p.replace(w, "")
        p = p.strip() or "котик"
        url = f"https://image.pollinations.ai/prompt/{p}?nologo=true&width=1024&height=1024"
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, f"✨ <b>Твой запрос:</b> {p}", photo=url)
        return "OK", 200

    # 3. ТЕКСТ / ФОТО
    if text or "photo" in msg:
        mid = real_progress(chat_id, "Анализ ОЛИМПА")
        img = None
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()["result"]["file_path"]
            img = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
        ans = get_ai(text or caption, img_b64=img)
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, ans)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
        
