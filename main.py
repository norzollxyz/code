import os
import requests
import base64
from flask import Flask, request

app = Flask(__name__)

# ================= НАСТРОЙКИ =================
TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"

def call_gemini_ultra(prompt, img_b64=None):
    """Мощный интеллект для учебы и общения"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    system_instruction = (
        "Ты — ОЛИМП, элитный ИИ-помощник. Твои суперспособности: "
        "1. Решать любые задачи, контрольные и домашку по фото или тексту. "
        "2. Писать сочинения, коды на Python и переводить тексты. "
        "3. Общаться как реальный бро, помогать советами. "
        "Отвечай максимально точно и понятно."
    )

    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nЗапрос: {prompt}"}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    if img_b64:
        payload["contents"][0]["parts"].append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

    try:
        res = requests.post(url, json=payload, timeout=30).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        return "🛰 ОЛИМП: Ошибка связи с ядром. Попробуй еще раз через минуту!"

def send_tg(chat_id, text, photo_url=None):
    url = f"https://api.telegram.org/bot{TOKEN}/"
    if photo_url:
        requests.post(url + "sendPhoto", json={"chat_id": chat_id, "photo": photo_url, "caption": text, "parse_mode": "HTML"})
    else:
        requests.post(url + "sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "ОЛИМП в сети!", 200
    data = request.get_json()
    if not data or "message" not in data: return "OK", 200
    
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    
    # --- РАБОТА С ФОТО (УЧЕБА / КОНТРОЛЬНЫЕ) ---
    if "photo" in msg:
        caption = msg.get("caption", "Реши задачу на фото или объясни, что это.")
        send_tg(chat_id, "📥 <b>ОЛИМП сканирует данные...</b>")
        try:
            file_id = msg["photo"][-1]["file_id"]
            file_res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
            img_data = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_res['result']['file_path']}").content
            img_b64 = base64.b64encode(img_data).decode('utf-8')
            send_tg(chat_id, f"🧠 <b>Готово:</b>\n\n{call_gemini_ultra(caption, img_b64)}")
        except:
            send_tg(chat_id, "⚠️ Ошибка при чтении фото.")
        return "OK", 200

    # --- ТЕКСТ (ОБЩЕНИЕ И РИСОВАНИЕ) ---
    text = msg.get("text", "").strip()
    if not text: return "OK", 200

    if text.lower() == "/start":
        send_tg(chat_id, "🦾 <b>ОЛИМП: УЛЬТРА-РЕЖИМ</b>\nПрисылай фото заданий, проси написать код или просто болтай!")
        return "OK", 200

    if any(word in text.lower() for word in ["нарисуй", "картинка", "фото"]):
        prompt = text.lower().replace("нарисуй", "").strip()
        send_tg(chat_id, f"🎨 Рисую: {prompt}...", photo_url=f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?nologo=true")
    else:
        send_tg(chat_id, call_gemini_ultra(text))
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
