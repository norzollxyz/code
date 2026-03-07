
import os
import requests
import base64
import time
from flask import Flask, request

app = Flask(__name__)

# ================= НАСТРОЙКИ =================
TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
ADMIN_ID = 5626603417 # ЗАМЕНИ НА СВОЙ ID (узнай у @userinfobot)
USERS_FILE = "users.txt" # Тут будем копить ID для рассылки
# ==============================================

def save_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

def send_tg(chat_id, text, photo=None, kb=None, action=None):
    url = f"https://api.telegram.org/bot{TOKEN}/"
    
    # Имитация печатания
    if action:
        requests.post(url + "sendChatAction", json={"chat_id": chat_id, "action": action})
        time.sleep(1) # Небольшая пауза для реализма

    payload = {"chat_id": chat_id, "parse_mode": "HTML"}
    
    if kb: payload["reply_markup"] = kb
    
    if photo:
        payload.update({"photo": photo, "caption": text})
        return requests.post(url + "sendPhoto", json=payload)
    else:
        payload.update({"text": text})
        return requests.post(url + "sendMessage", json=payload)

def get_ai(prompt, img=None):
    # Основной Gemini с обходом очереди
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    p_load = {"contents": [{"parts": [{"text": f"Ты ОЛИМП. Отвечай кратко. Запрос: {prompt}"}]}]}
    if img: p_load["contents"][0]["parts"].append({"inline_data": {"mime_type": "image/jpeg", "data": img}})
    
    try:
        r = requests.post(url, json=p_load, timeout=10).json()
        return r['candidates'][0]['content']['parts'][0]['text']
    except:
        # Резерв без очередей
        return requests.get(f"https://text.pollinations.ai/{prompt}?model=openai&system=Ты-ОЛИМП").text

# ГЛАВНОЕ МЕНЮ (КНОПКИ)
def main_kb():
    return {
        "inline_keyboard": [
            [{"text": "📸 ИИ Фотошоп", "callback_data": "ai_photo"}, {"text": "🎨 Создать арт", "callback_data": "gen_img"}],
            [{"text": "📐 Изменить размер", "callback_data": "resize"}, {"text": "💳 Баланс", "callback_data": "bal"}],
            [{"text": "❓ Помощь", "callback_data": "help"}]
        ]
    }

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "ONLINE", 200
    data = request.get_json()
    if not data: return "OK", 200

    # Обработка кнопок
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        call_data = cb["data"]
        
        if call_data == "ai_photo":
            send_tg(chat_id, "✨ Пришли фото и напиши в описании, что изменить!")
        elif call_data == "gen_img":
            send_tg(chat_id, "📝 Напиши 'Нарисуй [твой запрос]'")
        elif call_data == "bal":
            send_tg(chat_id, "💰 Ваш баланс: <b>Безлимитный (VIP)</b>")
        return "OK", 200

    if "message" not in data: return "OK", 200
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    save_user(chat_id)

    text = msg.get("text", "")

    # АДМИН ПАНЕЛЬ
    if text == "/admin" and chat_id == ADMIN_ID:
        with open(USERS_FILE, "r") as f: count = len(f.read().splitlines())
        send_tg(chat_id, f"👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nЮзеров в базе: {count}\n\nЧтобы сделать рассылку, напиши:\n<code>рассылка Текст сообщения</code>")
        return "OK", 200

    if text.startswith("рассылка ") and chat_id == ADMIN_ID:
        mail_text = text.replace("рассылка ", "")
        with open(USERS_FILE, "r") as f:
            for u_id in f.read().splitlines():
                send_tg(u_id, f"📢 <b>Объявление:</b>\n\n{mail_text}")
        send_tg(chat_id, "✅ Рассылка завершена!")
        return "OK", 200

    # СТАРТ
    if text == "/start":
        welcome_img = "https://i.ibb.co/LzNfXwz/image.jpg" # Можешь сменить на свою картинку
        send_tg(chat_id, "Привет! Я твой <b>ОЛИМП ИИ</b>. Вот что я умею:", photo=welcome_img, kb=main_kb(), action="typing")
        return "OK", 200

    # ОБРАБОТКА ФОТО
    if "photo" in msg:
        send_tg(chat_id, "🤖 Анализирую...", action="upload_photo")
        file_id = msg["photo"][-1]["file_id"]
        f_path = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()["result"]["file_path"]
        img_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{f_path}").content).decode('utf-8')
        ans = get_ai(msg.get("caption", "Что на фото?"), img_b64)
        send_tg(chat_id, f"🧠 <b>Готово:</b>\n{ans}")
        return "OK", 200

    # ОБЫЧНЫЙ ЧАТ
    if text:
        if text.lower().startswith("нарисуй"):
            prompt = text.lower().replace("нарисуй", "").strip()
            send_tg(chat_id, "🎨 Рисую твой шедевр...", action="upload_photo")
            send_tg(chat_id, "✨ Готово!", photo=f"https://image.pollinations.ai/prompt/{prompt}?nologo=true")
        else:
            send_tg(chat_id, "🔍 Думаю...", action="typing")
            ans = get_ai(text)
            send_tg(chat_id, ans)

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
