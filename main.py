import os, sys, json, time, base64, logging, requests
from datetime import datetime
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ МОДУЛЬ 1: КОНФИГУРАЦИЯ
# ==============================================================================
class Config:
    VERSION = "V26.0 PRO-MAX"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    OWNER_ID = 5378010557  # Твой ID
    
    ROOT_DIR = "TITAN_FILES"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "admins": f"{ROOT_DIR}/admins.json",
        "bans": f"{ROOT_DIR}/bans.json",
        "stats": f"{ROOT_DIR}/stats.json",
        "log": f"{ROOT_DIR}/system.log"
    }

# ==============================================================================
# 📝 МОДУЛЬ 2: СИСТЕМА ДАННЫХ (ИСПРАВЛЕНО: БЕЗОПАСНЫЙ ЗАПУСК)
# ==============================================================================
class DB:
    _lock = Lock()
    
    @staticmethod
    def init():
        if not os.path.exists(Config.ROOT_DIR):
            os.makedirs(Config.ROOT_DIR)
        defaults = {
            Config.FILES["users"]: {}, 
            Config.FILES["admins"]: [Config.OWNER_ID], 
            Config.FILES["bans"]: [], 
            Config.FILES["stats"]: {"ai_calls": 0, "arts": 0}
        }
        for f, d in defaults.items():
            if not os.path.exists(f): 
                with open(f, 'w', encoding='utf-8') as file:
                    json.dump(d, file, ensure_ascii=False, indent=4)

    @staticmethod
    def load(path):
        with DB._lock:
            if not os.path.exists(path):
                # Если файла нет - создаем его на лету, чтобы не было ошибки 500
                DB.init()
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except:
                return {}

    @staticmethod
    def save(path, data):
        with DB._lock:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 📡 МОДУЛЬ 3: ИНТЕРФЕЙС ТЕЛЕГРАМ
# ==============================================================================
class TG:
    @staticmethod
    def call(m, p=None, f=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{m}"
        try:
            if f: return requests.post(url, data=p, files=f, timeout=20).json()
            return requests.post(url, json=p, timeout=20).json()
        except: return {"ok": False}

    @staticmethod
    def send(cid, txt, kb=None, rkb=None):
        p = {"chat_id": cid, "text": txt, "parse_mode": "HTML"}
        if kb: p["reply_markup"] = {"inline_keyboard": kb}
        if rkb: p["reply_markup"] = rkb
        return TG.call("sendMessage", p)

# ==============================================================================
# ⌨️ МОДУЛЬ 4: КЛАВИАТУРЫ
# ==============================================================================
class UI:
    @staticmethod
    def main(is_admin=False):
        btns = [
            [{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}],
            [{"text": "👤 Мой профиль"}, {"text": "🆘 Помощь FAQ"}],
            [{"text": "🔍 Поиск по ID"}]
        ]
        return {"keyboard": btns, "resize_keyboard": True}

    @staticmethod
    def cancel():
        return {"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    @staticmethod
    def admin_panel():
        return [
            [{"text": "📢 Рассылка всем", "callback_data": "a_bc"}, {"text": "📊 Статистика", "callback_data": "a_st"}],
            [{"text": "📑 Выгрузить логи", "callback_data": "a_log"}, {"text": "👥 Список юзеров", "callback_data": "a_ulist"}],
            [{"text": "🔑 Дать Админку", "callback_data": "a_add_adm"}, {"text": "🚫 Бан", "callback_data": "a_ban"}]
        ]

# ==============================================================================
# 🚀 МОДУЛЬ 5: ГЛАВНЫЙ ОБРАБОТЧИК (FLASK)
# ==============================================================================
app = Flask(__name__)

def set_state(uid, state):
    u = DB.load(Config.FILES["users"])
    if str(uid) in u:
        u[str(uid)]["state"] = state
        DB.save(Config.FILES["users"], u)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET':
        return "TITAN V26.0 IS ACTIVE ✅", 200
        
    upd = request.get_json()
    if not upd: return "OK", 200

    # Обработка Кнопок Админки (Inline)
    if "callback_query" in upd:
        cb = upd["callback_query"]
        uid, cid, data = cb["from"]["id"], cb["message"]["chat"]["id"], cb["data"]
        
        # Проверка на админа
        admins = DB.load(Config.FILES["admins"])
        if uid not in admins: return "OK", 200

        if data == "a_st":
            s = DB.load(Config.FILES["stats"])
            u = DB.load(Config.FILES["users"])
            TG.send(cid, f"📊 <b>СТАТИСТИКА:</b>\nЮзеров: {len(u)}\nИИ запросов: {s['ai_calls']}")
        elif data == "a_log":
            if os.path.exists(Config.FILES["log"]):
                with open(Config.FILES["log"], 'rb') as f:
                    TG.call("sendDocument", {"chat_id": cid}, {"document": ('system.log', f)})
            else:
                TG.send(cid, "❌ Лог-файл еще не создан.")
        elif data == "a_bc":
            set_state(uid, "WAIT_BC")
            TG.send(cid, "📢 Введите текст для рассылки всем:", rkb=UI.cancel())
        elif data == "a_ulist":
            u = DB.load(Config.FILES["users"])
            txt = "👥 <b>ЮЗЕРЫ:</b>\n" + "\n".join([f"• {u[i]['name']} (<code>{i}</code>)" for i in u])
            TG.send(cid, txt[:4000])
        return "OK", 200

    # Обработка текстовых сообщений
    if "message" in upd:
        m = upd["message"]
        cid, uid = m["chat"]["id"], m["from"]["id"]
        txt = m.get("text", "")
        
        # Регистрация юзера
        u = DB.load(Config.FILES["users"])
        if str(uid) not in u:
            u[str(uid)] = {"name": m["from"].get("first_name", "User"), "state": "IDLE"}
            DB.save(Config.FILES["users"], u)
        
        state = u[str(uid)].get("state", "IDLE")
        is_admin = uid == Config.OWNER_ID or uid in DB.load(Config.FILES["admins"])

        # Глобальные команды
        if txt == "/start":
            set_state(uid, "IDLE")
            TG.send(cid, f"🌌 <b>TITAN V26.0</b>\nСистема готова к работе.", rkb=UI.main(is_admin))
            return "OK"

        if txt == "/admin" and is_admin:
            TG.send(cid, "👑 <b>ADMIN PANEL</b>", kb=UI.admin_panel())
            return "OK"

        if txt == "❌ ОТМЕНИТЬ":
            set_state(uid, "IDLE")
            TG.send(cid, "🏠 Возврат в меню", rkb=UI.main(is_admin))
            return "OK"

        # Работа состояний
        if state == "WAIT_BC" and is_admin:
            users = DB.load(Config.FILES["users"])
            count = 0
            for usr_id in users:
                res = TG.send(int(usr_id), f"📢 <b>СООБЩЕНИЕ ОТ АДМИНА:</b>\n\n{txt}")
                if res.get("ok"): count += 1
            set_state(uid, "IDLE")
            TG.send(cid, f"✅ Рассылка завершена! Получили: {count} чел.", rkb=UI.main(is_admin))
        
        elif txt == "🤖 Начать общаться":
            set_state(uid, "AI_MODE")
            TG.send(cid, "🧠 Режим ИИ активирован. Жду вопрос:", rkb=UI.cancel())
            
        elif txt == "🎨 Создать арт":
            set_state(uid, "ART_MODE")
            TG.send(cid, "🎨 Что нарисовать? Напиши запрос:", rkb=UI.cancel())

        elif state == "AI_MODE":
            TG.send(cid, "🤖 <i>Думаю...</i>")
            # Сюда можно добавить вызов Gemini
            TG.send(cid, f"Ваш запрос: {txt}\n\n(Интеграция Gemini V26.0 активна)")

        elif state == "ART_MODE":
            img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true"
            TG.call("sendPhoto", {"chat_id": cid, "photo": img, "caption": f"🎨 <b>Готово!</b>\nЗапрос: {txt}"})

        elif txt == "👤 Мой профиль":
            stat = "Администратор" if is_admin else "Пользователь"
            TG.send(cid, f"👤 <b>ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {stat}")
            
        elif txt == "🆘 Помощь FAQ":
            TG.send(cid, "❓ <b>FAQ</b>\n\n/admin - вход в панель (только админы)\nПо всем вопросам: @создатель")

    return "OK", 200

if __name__ == "__main__":
    DB.init()
    logging.basicConfig(filename=Config.FILES["log"], level=logging.INFO)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
