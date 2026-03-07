import os, sys, json, time, logging, requests
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 LIVE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    OWNER_ID = 5378010557
    
    ROOT_DIR = "TITAN_FILES"
    FILES = {"users": f"{ROOT_DIR}/users.json", "admins": f"{ROOT_DIR}/admins.json"}

# ==============================================================================
# 🧠 МОЗГИ ИИ С ЭФФЕКТОМ ПЕЧАТАНИЯ
# ==============================================================================
class AI_Engine:
    @staticmethod
    def ask_gemini(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, timeout=20).json()
            return r['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            return f"❌ Ошибка ИИ: {str(e)}"

# ==============================================================================
# 📡 ТЕЛЕГРАМ API (С ФУНКЦИЕЙ РЕДАКТИРОВАНИЯ)
# ==============================================================================
class TG:
    @staticmethod
    def call(m, p=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{m}"
        try: return requests.post(url, json=p, timeout=20).json()
        except: return {"ok": False}

    @staticmethod
    def edit(cid, mid, txt):
        return TG.call("editMessageText", {"chat_id": cid, "message_id": mid, "text": txt, "parse_mode": "HTML"})

# ==============================================================================
# 🚀 ГЛАВНЫЙ КОНТРОЛЛЕР
# ==============================================================================
app = Flask(__name__)

def set_state(uid, state):
    if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
    path = Config.FILES["users"]
    data = {}
    if os.path.exists(path):
        with open(path, 'r') as f: data = json.load(f)
    if str(uid) not in data: data[str(uid)] = {"name": "User"}
    data[str(uid)]["state"] = state
    with open(path, 'w') as f: json.dump(data, f)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "TITAN LIVE ACTIVE", 200
    upd = request.get_json()
    if not upd or "message" not in upd: return "OK", 200

    m = upd["message"]
    cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text", "")

    # Простая инициализация юзера
    path = Config.FILES["users"]
    if not os.path.exists(path): set_state(uid, "IDLE")
    with open(path, 'r') as f: users = json.load(f)
    state = users.get(str(uid), {}).get("state", "IDLE")

    # Клавиатуры
    main_kb = {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}], [{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        set_state(uid, "IDLE")
        TG.call("sendMessage", {"chat_id": cid, "text": "🌌 <b>ТИТАН V26.0</b> на связи. Выбери режим:", "reply_markup": main_kb, "parse_mode": "HTML"})
        return "OK"

    # ЛОГИКА ИИ С ПРОЦЕНТАМИ И ПЛАВНЫМ ВЫВОДОМ
    if state == "AI_MODE":
        # 1. Начальный статус
        res = TG.call("sendMessage", {"chat_id": cid, "text": "⏳ [░░░░░░░░░░] 0% (Подключение...)", "parse_mode": "HTML"})
        mid = res.get("result", {}).get("message_id")
        
        # 2. Имитируем процесс «подготовки» (для красоты)
        time.sleep(0.5)
        TG.edit(cid, mid, "⏳ [▓▓▓░░░░░░░] 30% (Анализ вопроса...)")
        
        # 3. Получаем полный ответ от Gemini
        full_answer = AI_Engine.ask_gemini(txt)
        
        TG.edit(cid, mid, "⏳ [▓▓▓▓▓▓▓░░░] 70% (Формирование ответа...)")
        time.sleep(0.5)
        
        # 4. ПЛАВНЫЙ ВЫВОД (Эффект печатания по словам)
        words = full_answer.split()
        display_text = "✨ <b>Ответ:</b>\n\n"
        
        # Чтобы не спамить Телеграм, выводим группами по 3 слова
        chunk_size = 3 
        for i in range(0, len(words), chunk_size):
            display_text += " ".join(words[i:i+chunk_size]) + " "
            TG.edit(cid, mid, display_text + " ▌") # Символ каретки (печатания)
            time.sleep(0.4) # Задержка для плавности
            
        # Финальный вариант без каретки
        TG.edit(cid, mid, display_text)

    elif txt == "🤖 Начать общаться":
        set_state(uid, "AI_MODE")
        TG.call("sendMessage", {"chat_id": cid, "text": "🧠 <b>Режим ИИ включен.</b> Пиши свой вопрос:", "parse_mode": "HTML"})

    elif txt == "🎨 Создать арт":
        set_state(uid, "ART_MODE")
        TG.call("sendMessage", {"chat_id": cid, "text": "🎨 <b>Режим Художника.</b> Что нарисовать?", "parse_mode": "HTML"})

    elif state == "ART_MODE":
        TG.call("sendMessage", {"chat_id": cid, "text": "👨‍🎨 <i>ТИТАН берет кисти...</i>", "parse_mode": "HTML"})
        img_url = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
        TG.call("sendPhoto", {"chat_id": cid, "photo": img_url, "caption": f"✅ <b>Готово!</b>\nЗапрос: {txt}", "parse_mode": "HTML"})

    return "OK", 200

if __name__ == "__main__":
    if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
        
