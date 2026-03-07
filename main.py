import os, json, time, requests, threading
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (MARCH 2026 UPDATE)
# ==============================================================================
class Config:
    VERSION = "V26.0 STABLE-FIX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    MAIN_ADMIN_ID = 5378010557
    
    ROOT_DIR = "TITAN_VAULT_FINAL"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "stats": f"{ROOT_DIR}/stats.json"
    }
    # 🔥 АКТУАЛЬНЫЕ МОДЕЛИ НА МАРТ 2026:
    MODELS = ["gemini-1.5-flash-8b", "gemini-1.5-flash", "gemini-2.0-flash-exp"]

# ==============================================================================
# 📝 БАЗА ДАННЫХ
# ==============================================================================
db_lock = threading.Lock()

def init_db():
    if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
    for f in Config.FILES.values():
        if not os.path.exists(f):
            with open(f, 'w', encoding='utf-8') as file: 
                json.dump({"ai_calls":0, "arts":0} if "stats" in f else {}, file)

init_db()

def db_op(path, data=None):
    with db_lock:
        if data is None:
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}
        with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 🧠 УМНОЕ ЯДРО ИИ (С ПРОВЕРКОЙ ВЕРСИЙ)
# ==============================================================================
class AI:
    @staticmethod
    def talk(prompt):
        last_err = ""
        # Пробуем по очереди все доступные модели
        for model in Config.MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={Config.GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                r = requests.post(url, json=payload, timeout=15)
                res = r.json()
                if 'candidates' in res:
                    return res['candidates'][0]['content']['parts'][0]['text']
                last_err = res.get('error', {}).get('message', 'Unknown Error')
            except Exception as e:
                last_err = str(e)
                continue
        return f"❌ Ошибка API Google (2026).\nПричина: {last_err}\n\nСовет: Проверь лимиты API ключа в Google AI Studio."

# ==============================================================================
# 📡 TELEGRAM API
# ==============================================================================
def tg(method, params):
    try: return requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{method}", json=params, timeout=20).json()
    except: return {"ok": False}

# ==============================================================================
# 🚀 КОНТРОЛЛЕР
# ==============================================================================
app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return f"TITAN {Config.VERSION} IS LIVE", 200
    
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]; cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text") or m.get("caption") or ""
    
    users = db_op(Config.FILES["users"])
    uid_s = str(uid)
    
    if uid_s not in users:
        users[uid_s] = {"state": "IDLE", "name": m["from"].get("first_name", "User")}
        db_op(Config.FILES["users"], users)

    # Главное меню
    kb_main = {"keyboard": [[{"text": "🤖 Общаться"}, {"text": "🎨 Арт"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        users[uid_s]["state"] = "IDLE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": "🌌 <b>TITAN V26.0 OMEGA</b>\nЯдро перезагружено. Выбери режим:", "parse_mode": "HTML", "reply_markup": kb_main})
        return "OK", 200

    state = users[uid_s].get("state", "IDLE")

    if state == "AI_MODE" and txt:
        tg("sendChatAction", {"chat_id": cid, "action": "typing"})
        ans = AI.talk(txt)
        tg("sendMessage", {"chat_id": cid, "text": f"✨ <b>Ответ:</b>\n\n{ans}", "parse_mode": "HTML"})
        s = db_op(Config.FILES["stats"]); s["ai_calls"] += 1; db_op(Config.FILES["stats"], s)

    elif state == "ART_MODE" and txt:
        tg("sendMessage", {"chat_id": cid, "text": "🎨 <i>Рисую...</i>", "parse_mode": "HTML"})
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
        tg("sendPhoto", {"chat_id": cid, "photo": img, "caption": f"✅ <b>Готово:</b> {txt}", "parse_mode": "HTML"})
        s = db_op(Config.FILES["stats"]); s["arts"] += 1; db_op(Config.FILES["stats"], s)

    elif txt == "🤖 Общаться":
        users[uid_s]["state"] = "AI_MODE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": "🧠 <b>Режим ИИ включен.</b> Пиши любой вопрос:", "parse_mode": "HTML", "reply_markup": {"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True}})

    elif txt == "🎨 Арт":
        users[uid_s]["state"] = "ART_MODE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": "🖼 <b>Режим Художника.</b> Что нарисовать?", "parse_mode": "HTML", "reply_markup": {"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True}})

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
