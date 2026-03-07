import os, json, time, requests, threading
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ (NEW KEY VERSION)
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA-RELIANCE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    # Твой новый ключ уже здесь:
    GEMINI_API_KEY = "AIzaSyBx67MYTv6YgGSLfeR5Vld93XwAHHHYQFE"
    MAIN_ADMIN_ID = 5378010557
    
    ROOT_DIR = "TITAN_ULTIMATE_VAULT"
    FILES = {"users": f"{ROOT_DIR}/users.json", "stats": f"{ROOT_DIR}/stats.json"}

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
# 🧠 УМНОЕ ЯДРО ИИ (AUTO-MODEL DISCOVERY)
# ==============================================================================
class AI:
    _working_model = None

    @staticmethod
    def find_best_model():
        """Автоматически находит доступную модель для твоего ключа"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={Config.GEMINI_API_KEY}"
        try:
            r = requests.get(url, timeout=10).json()
            if 'models' in r:
                # Приоритет 2026: 2.0 Flash -> 1.5 Flash -> 1.5 Flash-8b
                available = [m['name'].split('/')[-1] for m in r['models'] if "generateContent" in m['supportedGenerationMethods']]
                print(f"DEBUG: Доступные модели: {available}")
                
                for target in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]:
                    if target in available: return target
            return "gemini-1.5-flash" 
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            return "gemini-1.5-flash"

    @staticmethod
    def talk(prompt):
        if not AI._working_model:
            AI._working_model = AI.find_best_model()
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{AI._working_model}:generateContent?key={Config.GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, timeout=20).json()
            if 'candidates' in r:
                return r['candidates'][0]['content']['parts'][0]['text']
            err = r.get('error', {}).get('message', 'Неизвестная ошибка API')
            # Если модель сдохла, сбрасываем кэш модели для следующей попытки
            AI._working_model = None 
            return f"❌ Ошибка Google ({AI._working_model if AI._working_model else 'N/A'}): {err}"
        except Exception as e:
            return f"❌ Ошибка связи: {str(e)}"

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
    if request.method == 'GET': return f"TITAN {Config.VERSION} ONLINE", 200
    
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200
    
    m = upd["message"]; cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text") or m.get("caption") or ""
    
    users = db_op(Config.FILES["users"])
    uid_s = str(uid)
    
    if uid_s not in users:
        users[uid_s] = {"state": "IDLE", "name": m["from"].get("first_name", "User")}
        db_op(Config.FILES["users"], users)

    kb_main = {"keyboard": [[{"text": "🤖 Общаться"}, {"text": "🎨 Арт"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        users[uid_s]["state"] = "IDLE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": f"🌌 <b>TITAN {Config.VERSION}</b>\nНовый ключ активирован. Я готов!", "parse_mode": "HTML", "reply_markup": kb_main})
        return "OK", 200

    state = users[uid_s].get("state", "IDLE")

    if state == "AI_MODE" and txt:
        tg("sendChatAction", {"chat_id": cid, "action": "typing"})
        ans = AI.talk(txt)
        tg("sendMessage", {"chat_id": cid, "text": f"✨ <b>Ответ ({AI._working_model}):</b>\n\n{ans}", "parse_mode": "HTML"})
        s = db_op(Config.FILES["stats"]); s["ai_calls"] += 1; db_op(Config.FILES["stats"], s)

    elif state == "ART_MODE" and txt:
        tg("sendMessage", {"chat_id": cid, "text": "🎨 <i>Генерация...</i>", "parse_mode": "HTML"})
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true&seed={uid}"
        tg("sendPhoto", {"chat_id": cid, "photo": img, "caption": f"✅ <b>Арт:</b> {txt}", "parse_mode": "HTML"})
        s = db_op(Config.FILES["stats"]); s["arts"] += 1; db_op(Config.FILES["stats"], s)

    elif txt == "🤖 Общаться":
        users[uid_s]["state"] = "AI_MODE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": "🧠 <b>Интеллект включен.</b> Пиши вопрос:", "parse_mode": "HTML", "reply_markup": {"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True}})

    elif txt == "🎨 Арт":
        users[uid_s]["state"] = "ART_MODE"
        db_op(Config.FILES["users"], users)
        tg("sendMessage", {"chat_id": cid, "text": "🖼 <b>Режим Художника.</b> Опиши картину:", "parse_mode": "HTML", "reply_markup": {"keyboard":[[{"text":"❌ ОТМЕНИТЬ"}]], "resize_keyboard":True}})

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
