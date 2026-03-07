import os, sys, json, time, base64, logging, requests
from datetime import datetime
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ МОДУЛЬ 1: КОНФИГУРАЦИЯ (TITAN V26.0 CORE)
# ==============================================================================

class Config:
    VERSION = "V26.0 PRO-MAX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    OWNER_ID = 5378010557  # Твой ID (Главный Босс)
    
    ROOT_DIR = "TITAN_FILES"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "admins": f"{ROOT_DIR}/admins.json",
        "bans": f"{ROOT_DIR}/bans.json",
        "stats": f"{ROOT_DIR}/stats.json",
        "log": f"{ROOT_DIR}/system.log"
    }

# ==============================================================================
# 📝 МОДУЛЬ 2: СИСТЕМА ДАННЫХ (DATABASE & LOGS)
# ==============================================================================

class DB:
    _lock = Lock()
    
    @staticmethod
    def init():
        if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
        defaults = {Config.FILES["users"]: {}, Config.FILES["admins"]: [Config.OWNER_ID], 
                    Config.FILES["bans"]: [], Config.FILES["stats"]: {"ai_calls": 0, "arts": 0}}
        for f, d in defaults.items():
            if not os.path.exists(f): 
                with open(f, 'w', encoding='utf-8') as file: json.dump(d, file, ensure_ascii=False, indent=4)

    @staticmethod
    def load(path):
        with DB._lock:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    @staticmethod
    def save(path, data):
        with DB._lock:
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 📡 МОДУЛЬ 3: ИНТЕРФЕЙС ТЕЛЕГРАМ (API)
# ==============================================================================

class TG:
    @staticmethod
    def call(m, p=None, f=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{m}"
        try:
            if f: return requests.post(url, data=p, files=f).json()
            return requests.post(url, json=p).json()
        except: return {"ok": False}

    @staticmethod
    def send(cid, txt, kb=None, rkb=None):
        p = {"chat_id": cid, "text": txt, "parse_mode": "HTML"}
        if kb: p["reply_markup"] = {"inline_keyboard": kb}
        if rkb: p["reply_markup"] = rkb
        return TG.call("sendMessage", p)

# ==============================================================================
# ⌨️ МОДУЛЬ 4: КЛАВИАТУРЫ (UI)
# ==============================================================================

class UI:
    @staticmethod
    def main():
        return {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}],
                             [{"text": "👤 Мой профиль"}, {"text": "🆘 Помощь FAQ"}],
                             [{"text": "🔍 Поиск по ID"}]], "resize_keyboard": True}

    @staticmethod
    def cancel():
        return {"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    @staticmethod
    def admin():
        return [[{"text": "📢 Рассылка", "callback_data": "a_bc"}, {"text": "📊 Статистика", "callback_data": "a_st"}],
                [{"text": "👥 Юзеры", "callback_data": "a_ulist"}, {"text": "📑 Логи", "callback_data": "a_log"}],
                [{"text": "🚫 Бан", "callback_data": "a_ban"}, {"text": "🔑 Выдать Админ", "callback_data": "a_add_adm"}],
                [{"text": "🎮 Игровые функции", "callback_data": "a_games"}, {"text": "⚙️ Настройки", "callback_data": "a_set"}]]

# ==============================================================================
# 🧠 МОДУЛЬ 5: ЛОГИКА И СОСТОЯНИЯ (FSM)
# ==============================================================================

app = Flask(__name__)

def handle_admin(cid, uid, data, mid=None):
    if not (uid == Config.OWNER_ID or uid in DB.load(Config.FILES["admins"])): return
    
    if data == "a_st":
        s = DB.load(Config.FILES["stats"])
        u = DB.load(Config.FILES["users"])
        msg = f"📊 <b>TITAN STATS</b>\nЮзеров: {len(u)}\nИИ запросов: {s['ai_calls']}\nАртов: {s['arts']}"
        TG.send(cid, msg)
    
    elif data == "a_log":
        with open(Config.FILES["log"], 'rb') as f:
            TG.call("sendDocument", {"chat_id": cid}, {"document": f})
            
    elif data == "a_ulist":
        u = DB.load(Config.FILES["users"])
        txt = "👥 <b>СПИСОК ЮЗЕРОВ:</b>\n" + "\n".join([f"• {u[i]['name']} ({i})" for i in u])
        TG.send(cid, txt[:4000])

    elif data == "a_bc":
        set_state(uid, "BC")
        TG.send(cid, "📢 Введите текст рассылки:", rkb=UI.cancel())

def set_state(uid, state):
    u = DB.load(Config.FILES["users"])
    if str(uid) in u:
        u[str(uid)]["state"] = state
        DB.save(Config.FILES["users"], u)

@app.route('/', methods=['POST'])
def bot():
    upd = request.get_json()
    
    if "callback_query" in upd:
        cb = upd["callback_query"]
        handle_admin(cb["message"]["chat"]["id"], cb["from"]["id"], cb["data"], cb["message"]["message_id"])
        return "OK"

    if "message" not in upd: return "OK"
    msg = upd["message"]
    cid, uid = msg["chat"]["id"], msg["from"]["id"]
    txt = msg.get("text", "")
    
    # Регистрация
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u:
        u[str(uid)] = {"name": msg["from"].get("first_name", "User"), "state": "IDLE"}
        DB.save(Config.FILES["users"], u)

    state = u[str(uid)].get("state", "IDLE")

    # Команды
    if txt == "/start":
        set_state(uid, "IDLE")
        TG.send(cid, f"🌌 <b>TITAN V26.0</b>\nДобро пожаловать, {u[str(uid)]['name']}!", rkb=UI.main())
        return "OK"

    if txt == "/admin":
        if uid == Config.OWNER_ID or uid in DB.load(Config.FILES["admins"]):
            TG.send(cid, "👑 <b>АДМИН-ПАНЕЛЬ</b>", kb=UI.admin())
        return "OK"

    if txt == "❌ ОТМЕНИТЬ":
        set_state(uid, "IDLE")
        TG.send(cid, "🏠 Главное меню", rkb=UI.main())
        return "OK"

    # Обработка кнопок и состояний
    if state == "IDLE":
        if txt == "🤖 Начать общаться":
            set_state(uid, "AI")
            TG.send(cid, "🧠 Режим ИИ включен. Что спросить?", rkb=UI.cancel())
        elif txt == "🎨 Создать арт":
            set_state(uid, "ART")
            TG.send(cid, "🎨 Опишите арт:", rkb=UI.cancel())
        elif txt == "👤 Мой профиль":
            adm = "Администратор" if (uid == Config.OWNER_ID or uid in DB.load(Config.FILES["admins"])) else "Пользователь"
            TG.send(cid, f"👤 <b>ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {adm}")
        elif txt == "🆘 Помощь FAQ":
            TG.send(cid, "📖 <b>FAQ</b>\n1. Как спросить ИИ? - Нажми 'Начать общаться'.\n2. Как рисовать? - Кнопка 'Создать арт'.")
    
    elif state == "AI":
        # Сюда вставь вызов Gemini (Config.GEMINI_API_KEY)
        TG.send(cid, f"🤖 [ИИ Думает...]\nЗапрос: {txt}")
    
    elif state == "ART":
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
        TG.call("sendPhoto", {"chat_id": cid, "photo": img, "caption": f"🎨 Готово: {txt}"})
        
    elif state == "BC":
        users = DB.load(Config.FILES["users"])
        for user in users:
            TG.send(int(user), f"📢 <b>РАССЫЛКА:</b>\n\n{txt}")
        set_state(uid, "IDLE")
        TG.send(cid, "✅ Рассылка завершена!", rkb=UI.main())

    return "OK"

if __name__ == "__main__":
    DB.init()
    # Логирование в файл
    logging.basicConfig(filename=Config.FILES["log"], level=logging.INFO)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
                      
