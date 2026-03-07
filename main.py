import os
import requests
import base64
from flask import Flask, request

app = Flask(__name__)

# ================= НАСТРОЙКИ (НЕ ТРОГАЙ) =================
TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
# =========================================================

def ask_ai_unlimited(prompt, img_b64=None):
    """Умная функция: пробует Gemini, если не выходит — идет через резерв"""
    # 1. Пробуем Gemini (Основной интеллект)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    sys_msg = "Ты ОЛИМП. Помогай с учебой, решай задачи по фото, пиши код. Отвечай кратко и четко."
    
    payload = {"contents": [{"parts": [{"text": f"{sys_msg}\n\nЗапрос: {prompt}"}]}]}
    if img_b64:
        payload["contents"][0]["parts"].append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
    
    try:
        res = requests.post(url, json=payload, timeout=15).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        # 2. РЕЗЕРВНЫЙ КАНАЛ (Если Google заблочен)
        try:
            backup_url = f"https://text.pollinations.ai/{prompt} (отвечай на русском)"
            return requests.get(backup_url, timeout=15).text
        except:
            return "🛰 ОЛИМП: Все системы перегружены. Попробуй через 2 минуты."

def send_tg(chat_id, text, photo=None):
    url = f"https://api.telegram.org/bot{TOKEN}/"
    if photo:
        requests.post(url + "sendPhoto", json={"chat_id": chat_id, "photo": photo, "caption": text, "parse_mode": "HTML"})
    else:
        requests.post(url + "sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "ОЛИМП В СЕТИ", 200
    data = request.get_json()
    if not data or "message" not in data: return "OK", 200
    
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    
    # ФОТО (Задачи, контрольные)
    if "photo" in msg:
        send_tg(chat_id, "📥 <b>Сканирую...</b>")
        try:
            file_id = msg["photo"][-1]["file_id"]
            f_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
            img_url = f"https://api.telegram.org/file/bot{TOKEN}/{f_info['result']['file_path']}"
            img_b64 = base64.b64encode(requests.get(img_url).content).decode('utf-8')
            send_tg(chat_id, f"🧠 <b>ОЛИМП выдал решение:</b>\n\n{ask_ai_unlimited(msg.get('caption', 'Реши это'), img_b64)}")
        except:
            send_tg(chat_id, "⚠️ Ошибка фото. Пришли еще раз.")
        return "OK", 200

    # ТЕКСТ / КОМАНДЫ
    text = msg.get("text", "").strip()
    if not text: return "OK", 200

    if text.lower() == "/start":
        send_tg(chat_id, "🦾 <b>ОЛИМП: УЛЬТРА-РЕЖИМ АКТИВИРОВАН</b>\nПрисылай фото заданий или просто пиши вопрос.")
    elif any(word in text.lower() for word in ["нарисуй", "картинка"]):
        p = text.lower().replace("нарисуй", "").strip()
        send_tg(chat_id, f"🎨 Рисую: {p}", photo=f"https://image.pollinations.ai/prompt/{p}?nologo=true")
    else:
        send_tg(chat_id, ask_ai_unlimited(text))
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
