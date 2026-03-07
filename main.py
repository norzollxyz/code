import os, sys, json, time, logging, requests
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ МОДУЛЬ 1: КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 ULTIMATE"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    OWNER_ID = 5378010557  # Твой ID (Главный Босс)
    
    ROOT_DIR = "TITAN_FILES"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "admins": f"{ROOT_DIR}/admins.json",
        "stats": f"{ROOT_DIR}/stats.json",
        "log": f"{ROOT_DIR}/system.log"
    }

# ==============================================================================
# 📝 МОДУЛЬ 2: СУПЕР-БАЗА ДАННЫХ
# ==============================================================================
class DB:
    _lock = Lock()
    
    @staticmethod
    def init():
        if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
        defaults = {
            Config.FILES["users"]: {}, 
            Config.FILES["admins"]: [Config.OWNER_ID], 
            Config.FILES["stats"]: {"ai_calls": 0, "arts": 0}
        }
        for f, d in defaults.items():
            if not os.path.exists(f): 
                with open(f, 'w', encoding='utf-8') as file: json.dump(d, file, indent=4)

    @staticmethod
    def load(path):
        with DB._lock:
            if not os.path.exists(path): DB.init()
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}

    @staticmethod
    def save(path, data):
        with DB._lock:
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 🧠 МОДУЛЬ 3: ИИ И ВИЗУАЛ
# ==============================================================================
class AI_Engine:
    @staticmethod
    def ask_gemini(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, timeout=20).json()
            return r['candidates'][0]['content']['parts'][0]['text']
        except: return "❌ Ошибка связи с ядром ИИ."

# ==============================================================================
# 📡 МОДУЛЬ 4: ТЕЛЕГРАМ API
# ==============================================================================
class TG:
    @staticmethod
    def call(m, p=None, f=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{m}"
        try:
            if f: return requests.post(url, data=p, files=f, timeout=25).json()
            return requests.post(url, json=p, timeout=25).json()
        except: return {"ok": False}

    @staticmethod
    def send(cid, txt, kb=None, rkb=None):
        p = {"chat_id": cid, "text": txt, "parse_mode": "HTML"}
        if kb: p["reply_markup"] = {"inline_keyboard": kb}
        if rkb: p["reply_markup"] = rkb
        return TG.call("sendMessage", p)

    @staticmethod
    def edit(cid, mid, txt):
        return TG.call("editMessageText", {"chat_id": cid, "message_id": mid, "text": txt, "parse_mode": "HTML"})

# ==============================================================================
# 🚀 МОДУЛЬ 5: ЛОГИКА И ИНТЕРФЕЙС
# ==============================================================================
app = Flask(__name__)

def set_state(uid, state):
    u = DB.load(Config.FILES["users"])
    if str(uid) in u:
        u[str(uid)]["state"] = state
        DB.save(Config.FILES["users"], u)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "TITAN V26.0 ULTIMATE ONLINE", 200
    upd = request.get_json()
    if not upd: return "OK", 200

    # ОБРАБОТКА КЛАВИАТУР АДМИНКИ (CALLBACK)
    if "callback_query" in upd:
        cb = upd["callback_query"]
        uid, cid, data = cb["from"]["id"], cb["message"]["chat"]["id"], cb["data"]
        admins = DB.load(Config.FILES["admins"])
        if uid not in admins: return "OK", 200

        if data == "a_st":
            s = DB.load(Config.FILES["stats"])
            u = DB.load(Config.FILES["users"])
            TG.send(cid, f"📊 <b>СТАТИСТИКА</b>\nЮзеров: {len(u)}\nЗапросов ИИ: {s['ai_calls']}\nАртов: {s['arts']}")
        elif data == "a_log":
            if os.path.exists(Config.FILES["log"]):
                with open(Config.FILES["log"], 'rb') as f:
                    TG.call("sendDocument", {"chat_id": cid}, {"document": ('titan.log', f)})
            else: TG.send(cid, "❌ Лог пуст.")
        elif data == "a_bc":
            set_state(uid, "WAIT_BC")
            TG.send(cid, "📢 Введи текст рассылки:", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True})
        elif data == "a_ulist":
            u = DB.load(Config.FILES["users"])
            txt = "👥 <b>СПИСОК:</b>\n" + "\n".join([f"• {u[i]['name']} (<code>{i}</code>)" for i in u])
            TG.send(cid, txt[:4000])
        elif data == "a_add_adm":
            set_state(uid, "WAIT_ADD_ADM")
            TG.send(cid, "🔑 Введи ID юзера, чтобы сделать его админом:")
        return "OK", 200

    # ОБРАБОТКА СООБЩЕНИЙ
    if "message" not in upd: return "OK", 200
    m = upd["message"]
    cid, uid, txt = m["chat"]["id"], m["from"]["id"], m.get("text", "")

    # База юзеров
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u:
        u[str(uid)] = {"name": m["from"].get("first_name", "User"), "state": "IDLE"}
        DB.save(Config.FILES["users"], u)
    
    state = u[str(uid)].get("state", "IDLE")
    admins = DB.load(Config.FILES["admins"])
    is_admin = uid in admins

    # ГЛАВНОЕ МЕНЮ
    kb_main = {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}], 
                            [{"text": "👤 Мой профиль"}, {"text": "🆘 Помощь FAQ"}],
                            [{"text": "🔍 Поиск по ID"}]], "resize_keyboard": True}
    kb_cancel = {"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        set_state(uid, "IDLE")
        TG.send(cid, f"🌌 <b>TITAN V26.0 ULTIMATE</b>\nСистема готова, {u[str(uid)]['name']}!", rkb=kb_main)
        return "OK"

    if txt == "/admin" and is_admin:
        kb_adm = [[{"text": "📢 Рассылка", "callback_data": "a_bc"}, {"text": "📊 Стата", "callback_data": "a_st"}],
                  [{"text": "📑 Логи", "callback_data": "a_log"}, {"text": "👥 Юзеры", "callback_data": "a_ulist"}],
                  [{"text": "🔑 +Админ", "callback_data": "a_add_adm"}]]
        TG.send(cid, "👑 <b>АДМИН-ПАНЕЛЬ</b>", kb=kb_adm)
        return "OK"

    # РАБОТА СОСТОЯНИЙ
    if state == "AI_MODE":
        res = TG.send(cid, "⏳ [░░░░░░░░░░] 10% (Коннект...)")
        mid = res.get("result", {}).get("message_id")
        
        answer = AI_Engine.ask_gemini(txt)
        TG.edit(cid, mid, "⏳ [▓▓▓▓▓▓░░░░] 60% (Печатаю...)")
        
        words = answer.split()
        out = "✨ <b>Ответ:</b>\n\n"
        for i in range(0, len(words), 4):
            out += " ".join(words[i:i+4]) + " "
            TG.edit(cid, mid, out + "▌")
            time.sleep(0.4)
        TG.edit(cid, mid, out)
        
        # Обновляем статику
        s = DB.load(Config.FILES["stats"])
        s["ai_calls"] += 1
        DB.save(Config.FILES["stats"], s)

    elif state == "ART_MODE":
        TG.send(cid, "👨‍🎨 <i>Рисую ваш шедевр...</i>")
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
        TG.call("sendPhoto", {"chat_id": cid, "photo": img, "caption": f"✅ Готово: {txt}"})
        s = DB.load(Config.FILES["stats"])
        s["arts"] += 1
        DB.save(Config.FILES["stats"], s)

    elif state == "WAIT_BC" and is_admin:
        for user_id in u:
            TG.send(int(user_id), f"📢 <b>ОБЪЯВЛЕНИЕ:</b>\n\n{txt}")
        set_state(uid, "IDLE")
        TG.send(cid, "✅ Рассылка завершена!", rkb=kb_main)

    elif state == "WAIT_ADD_ADM" and uid == Config.OWNER_ID:
        try:
            new_admin = int(txt)
            admins.append(new_admin)
            DB.save(Config.FILES["admins"], list(set(admins)))
            TG.send(cid, f"✅ Юзер <code>{new_admin}</code> теперь админ!", rkb=kb_main)
            set_state(uid, "IDLE")
        except: TG.send(cid, "❌ Введи корректный числовой ID")

    # ОБРАБОТКА КНОПОК МЕНЮ
    elif txt == "🤖 Начать общаться":
        set_state(uid, "AI_MODE")
        TG.send(cid, "🧠 <b>Режим ИИ.</b> Задавай вопрос:", rkb=kb_cancel)
    elif txt == "🎨 Создать арт":
        set_state(uid, "ART_MODE")
        TG.send(cid, "🎨 <b>Художник.</b> Опиши картину:", rkb=kb_cancel)
    elif txt == "👤 Мой профиль":
        TG.send(cid, f"👤 <b>ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {'Админ' if is_admin else 'Юзер'}")
    elif txt == "🆘 Помощь FAQ":
        TG.send(cid, "🆘 <b>ПОМОЩЬ</b>\nПиши боту вопросы или проси нарисовать. /admin для управления.")
    elif txt == "🔍 Поиск по ID":
        TG.send(cid, "🔍 Введите ID пользователя для поиска (функция в разработке V26.1)")

    return "OK", 200

if __name__ == "__main__":
    DB.init()
    logging.basicConfig(filename=Config.FILES["log"], level=logging.INFO, format='%(asctime)s %(message)s')
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
