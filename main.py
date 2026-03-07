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

def send_action(chat_id, action):
    """Показывает статус 'печатает' или 'отправляет фото'"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": action})

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

def edit_tg(chat_id, mid, text, kb=None):
    payload = {"chat_id": chat_id, "message_id": mid, "text": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = {"inline_keyboard": kb}
    requests.post(f"https://api.telegram.org/bot{TOKEN}/editMessageText", json=payload)

def delete_tg(chat_id, mid):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": mid})

def real_progress(chat_id, task):
    res = send_tg(chat_id, f"📡 <b>{task}</b>\n└ ⏳ <code>1%</code>")
    mid = res.get("result", {}).get("message_id")
    if mid:
        curr = 1
        for _ in range(3):
            curr += random.randint(25, 30)
            time.sleep(0.4)
            edit_tg(chat_id, mid, f"📡 <b>{task}</b>\n└ ⏳ <code>{curr}%</code>")
        return mid
    return None

def get_ai(prompt, img=None, voice=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img}})
    if voice: parts.append({"inline_data": {"mime_type": "audio/ogg", "data": voice}})
    try:
        r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=12).json()
        if 'candidates' in r: return r['candidates'][0]['content']['parts'][0]['text']
        return "⚠️ Ошибка Gemini."
    except: return "🛰 Ошибка связи."

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "SYSTEM_V26_ACTIVE", 200
    data = request.get_json()
    if not data: return "OK", 200

    if "callback_query" in data:
        cb = data["callback_query"]
        cid, call, mid = cb["message"]["chat"]["id"], cb["data"], cb["message"]["message_id"]
        if cid == ADMIN_ID:
            if call == "adm_main":
                kb = [[{"text": "📢 Рассылка", "callback_data": "adm_bc"}, {"text": "🗑 Откат", "callback_data": "adm_rev"}],
                      [{"text": "📊 Стата", "callback_data": "adm_stat"}, {"text": "📑 Логи", "callback_data": "adm_logs"}]]
                edit_tg(cid, mid, "👑 <b>АДМИН-ПАНЕЛЬ</b>", kb=kb)
            elif call == "adm_bc":
                ADMIN_STATE[cid] = "waiting_bc"
                send_tg(cid, "📝 Отправь текст или фото для рассылки:")
        return "OK", 200

    if "message" not in data: return "OK", 200
    msg = data["message"]
    chat_id, text = msg["chat"]["id"], msg.get("text", "")
    caption = msg.get("caption", "")

    # Регистрация
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "a").close()
    with open(USERS_FILE, "r+") as f:
        if str(chat_id) not in f.read(): f.write(f"{chat_id}\n")

    # --- НОВОЕ МЕНЮ И КНОПКИ ---
    if text == "/start":
        welcome = (
            "👋 <b>Добро пожаловать в интеллектуальный чат!</b>\n\n"
            "Я работаю на базе Gemini 1.5. Могу общаться, понимать фото и генерировать изображения по твоим запросам.\n\n"
            "📌 <b>Основные возможности:</b>\n"
            "└ ✍️ Ответы на любые вопросы\n"
            "└ 🎨 Генерация артов (кнопка ниже)\n"
            "└ 🎙 Распознавание голоса"
        )
        reply_kb = {
            "keyboard": [
                [{"text": "🚀 Команды"}, {"text": "👤 Мой профиль"}],
                [{"text": "🆘 Написать админу"}]
            ],
            "resize_keyboard": True
        }
        send_tg(chat_id, welcome, reply_kb=reply_kb)
        return "OK", 200

    if text == "🚀 Команды":
        cmd_text = (
            "🖼 <b>Как генерировать изображения?</b>\n\n"
            "Просто напиши фразу «Нарисуй» и свой запрос. Примеры:\n"
            "• <code>Нарисуй плюшевого мишку в космосе</code>\n"
            "• <code>Нарисуй машину будущего в стиле киберпанк</code>\n"
            "• <code>Нарисуй заброшенный замок</code>\n\n"
            "Все арты уходят на проверку администратору."
        )
        send_tg(chat_id, cmd_text)
        return "OK", 200

    if text == "👤 Мой профиль":
        send_tg(chat_id, f"<b>Твой аккаунт:</b>\n\n🆔 ID: <code>{chat_id}</code>\n💎 Статус: <b>User</b>\n📅 Дата: {datetime.date.today()}")
        return "OK", 200

    if text == "🆘 Написать админу":
        send_tg(chat_id, "💬 Чтобы связаться с админом, пиши напрямую: @твоё_имя_тут")
        return "OK", 200

    # АДМИНКА
    if chat_id == ADMIN_ID:
        if text == "/admin":
            kb = [[{"text": "📢 Рассылка", "callback_data": "adm_bc"}, {"text": "🗑 Откат", "callback_data": "adm_rev"}],
                  [{"text": "📊 Стата", "callback_data": "adm_stat"}, {"text": "📑 Логи", "callback_data": "adm_logs"}]]
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
            send_tg(ADMIN_ID, "✅ Рассылка завершена.")
            ADMIN_STATE.clear()
            return "OK", 200

    # ЛОГИКА ОБРАБОТКИ
    if text or "photo" in msg or "voice" in msg:
        full_q = (text + caption).lower()
        if any(w in full_q for w in ["нарисуй", "сгенерируй", "draw", "создай"]):
            send_action(chat_id, "upload_photo") # Статус в ТГ
            mid = real_progress(chat_id, "Генерация")
            p = full_q.replace("нарисуй", "").replace("сгенерируй", "").strip() or "cool art"
            img_url = f"https://image.pollinations.ai/prompt/{p}?nologo=true"
            if mid: delete_tg(chat_id, mid)
            send_tg(ADMIN_ID, f"🔔 Заказ от {chat_id}: {p}", photo=img_url)
            if chat_id != ADMIN_ID: send_tg(chat_id, "✅ Запрос принят. Результат отправлен админу.")
            return "OK", 200

        send_action(chat_id, "typing") # Статус в ТГ 'печатает...'
        mid = real_progress(chat_id, "Анализ")
        img, voice = None, None
        if "photo" in msg:
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={msg['photo'][-1]['file_id']}").json()["result"]["file_path"]
            img = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
        if "voice" in msg:
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={msg['voice']['file_id']}").json()["result"]["file_path"]
            voice = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')

        ans = get_ai(text or caption or "Опиши", img=img, voice=voice)
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, ans)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
