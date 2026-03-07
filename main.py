import os, sys, json, time, logging, requests, threading
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 NEBULA"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    MAIN_ADMIN_ID = 5378010557
    ROOT_DIR = "TITAN_STORAGE"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "admins": f"{ROOT_DIR}/admins.json",
        "stats": f"{ROOT_DIR}/stats.json"
    }

# ==============================================================================
# 📝 БАЗА ДАННЫХ (ВЫНЕСЕНА В ТОП ДЛЯ GUNICORN)
# ==============================================================================
db_lock = threading.Lock()

def init_db():
    if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
    defaults = {
        Config.FILES["users"]: {},
        Config.FILES["admins"]: [Config.MAIN_ADMIN_ID],
        Config.FILES["stats"]: {"ai_calls": 0, "arts": 0}
    }
    for path, data in defaults.items():
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

init_db() # Запуск сразу!

def load_db(path):
    with db_lock:
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}

def save_db(path, data):
    with db_lock:
        with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 🧠 ЯДРО ИИ (ИСПРАВЛЕННЫЙ GEMINI)
# ==============================================================================
class AI:
    @staticmethod
    def talk(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, timeout=25)
            res = r.json()
            if 'candidates' in res:
                return res['candidates'][0]['content']['parts'][0]['text']
            return f"❌ Ошибка API: {res.get('error', {}).get('message', 'Неизвестно')}"
        except Exception as e:
            return f"❌ Тайм-аут связи с ядром ИИ. Попробуй еще раз."

# ==============================================================================
# 📡 TELEGRAM API
# ==============================================================================
def tg_send(cid, text, kb=None, photo=None):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/"
    p = {"chat_id": cid, "parse_mode": "HTML"}
    if kb: p["reply_markup"] = kb
    if photo:
        p["photo"], p["caption"] = photo, text
        return requests.post(url + "sendPhoto", json=p).json()
    p["text"] = text
    return requests.post(url + "sendMessage", json=p).json()

# ==============================================================================
# 🚀 КОНТРОЛЛЕР
# ==============================================================================
app = Flask(__name__)

@app.route('/health') # Хелсчек для Render
def health(): return "OK", 200

@app.route('/', methods=['POST', 'GET'])
def main_handler():
    if request.method == 'GET': return "TITAN NEBULA ONLINE", 200
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]; cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text") or m.get("caption") or ""

    # Состояние юзера
    users = load_db(Config.FILES["users"])
    if str(uid) not in users:
        users[str(uid)] = {"name": m["from"].get("first_name", "User"), "state": "IDLE"}
    
    state = users[str(uid)].get("state", "IDLE")
    is_adm = uid == Config.MAIN_ADMIN_ID

    # Обработка команд
    kb_main = {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}]], "resize_keyboard": True}
    
    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        users[str(uid)]["state"] = "IDLE"
        save_db(Config.FILES["users"], users)
        tg_send(cid, f"🌌 <b>TITAN {Config.VERSION}</b>\nСистема стабилизирована, {users[str(uid)]['name']}!", kb=kb_main)
        return "OK", 200

    if state == "AI_MODE" and txt:
        ans = AI.talk(txt)
        tg_send(cid, f"✨ <b>Ответ:</b>\n\n{ans}")
        s = load_db(Config.FILES["stats"]); s["ai_calls"] += 1; save_db(Config.FILES["stats"], s)

    elif state == "ART_MODE" and txt:
        tg_send(cid, "👨‍🎨 <i>Генерация нейро-холста...</i>")
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
        tg_send(cid, f"✅ Готово: {txt}", photo=img)
        s = load_db(Config.FILES["stats"]); s["arts"] += 1; save_db(Config.FILES["stats"], s)

    elif txt == "🤖 Начать общаться":
        users[str(uid)]["state"] = "AI_MODE"
        save_db(Config.FILES["users"], users)
        tg_send(cid, "🧠 <b>Режим ИИ активен.</b> Задавай вопрос:", kb={"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True})
    
    elif txt == "🎨 Создать арт":
        users[str(uid)]["state"] = "ART_MODE"
        save_db(Config.FILES["users"], users)
        tg_send(cid, "🎨 <b>Режим Художника.</b> Опиши картину:", kb={"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True})

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
            
