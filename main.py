import os, requests, base64, time, random, json, datetime
from flask import Flask, request

app = Flask(__name__)

# --- ДАННЫЕ (ПРОВЕРЬ ИХ!) ---
TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
ADMIN_ID = 5626603417 

# Файлы
USERS_FILE = "users.txt"
LOGS_FILE = "logs.txt"
BC_HISTORY = "bc_history.json"
ADMIN_STATE = {}

def send_action(chat_id, action):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": action})

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

def get_ai(prompt, img=None, voice=None):
    # Прямой запрос к Gemini без лишних оберток
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img}})
    if voice: parts.append({"inline_data": {"mime_type": "audio/ogg", "data": voice}})
    
    try:
        r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=15).json()
        if 'candidates' in r and r['candidates'][0].get('content'):
            return r['candidates'][0]['content']['parts'][0]['text']
        return "🛰 ИИ временно недоступен. Попробуй позже."
    except:
        return "📡 Ошибка сети. Проверь API ключ в коде."

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "V27_WORKING", 200
    data = request.get_json()
    if not data or "message" not in data: return "OK", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    caption = msg.get("caption", "")

    # СТАРТ И МЕНЮ (Убрал 'Олимп' и прочий мусор)
    if text == "/start":
        welcome = "🚀 <b>Gemini Chat TG V27</b>\n\nЯ готов. Пиши текст, кидай фото или голос.\nЧтобы рисовать, пиши: <i>Нарисуй [запрос]</i>"
        reply_kb = {
            "keyboard": [[{"text": "🚀 Команды"}, {"text": "👤 Мой профиль"}]],
            "resize_keyboard": True
        }
        send_tg(chat_id, welcome, reply_kb=reply_kb)
        return "OK", 200

    if text == "👤 Мой профиль":
        send_tg(chat_id, f"<b>Ваш профиль:</b>\n🆔 ID: <code>{chat_id}</code>\nСтатус: Пользователь")
        return "OK", 200

    # ГЕНЕРАЦИЯ (Исправлено)
    full_q = (text + caption).lower()
    if any(w in full_q for w in ["нарисуй", "сгенерируй", "draw"]):
        send_action(chat_id, "upload_photo")
        p = full_q.replace("нарисуй", "").replace("сгенерируй", "").strip() or "art"
        img_url = f"https://image.pollinations.ai/prompt/{p}?nologo=true"
        send_tg(ADMIN_ID, f"🔔 Запрос от {chat_id}: {p}", photo=img_url)
        send_tg(chat_id, "✅ Запрос обработан. Результат у админа.")
        return "OK", 200

    # ОБЫЧНЫЙ ЧАТ
    if text or "photo" in msg or "voice" in msg:
        send_action(chat_id, "typing")
        img, voice = None, None
        if "photo" in msg:
            fp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={msg['photo'][-1]['file_id']}").json()["result"]["file_path"]
            img = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
        
        ans = get_ai(text or caption or "Опиши файл", img=img)
        send_tg(chat_id, ans)

    return "OK", 200

if __name__ == "__main__":
    # ВАЖНО ДЛЯ RENDER: Слушаем порт из переменной окружения
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
        
