import os, sys, json, time, logging, requests
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ МОДУЛЬ 1: КОНФИГУРАЦИЯ (V26.0 PROFILE, ACTIONS & COMMANDS)
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA (FULL)"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    MAIN_ADMIN_ID = 5378010557
    
    ROOT_DIR = "V26_DATA_VAULT"
    FILES = {
        "users": f"{ROOT_DIR}/users_db.json",
        "admins": f"{ROOT_DIR}/admins_db.json",
        "stats": f"{ROOT_DIR}/system_stats.json",
        "log": f"{ROOT_DIR}/titan_v26.log"
    }

# ==============================================================================
# 📝 МОДУЛЬ 2: БАЗА ДАННЫХ (С ЗАЩИТОЙ ОТ ОШИБОК)
# ==============================================================================
class DB:
    _lock = Lock()
    
    @staticmethod
    def init():
        if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
        defaults = {
            Config.FILES["users"]: {}, 
            Config.FILES["admins"]: [Config.MAIN_ADMIN_ID], 
            Config.FILES["stats"]: {"ai_calls": 0, "arts": 0}
        }
        for path, data in defaults.items():
            if not os.path.exists(path): 
                with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

    @staticmethod
    def load(path):
        with DB._lock:
            if not os.path.exists(path): DB.init()
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: 
                if "admins" in path: return [Config.MAIN_ADMIN_ID]
                if "stats" in path: return {"ai_calls": 0, "arts": 0}
                return {}

    @staticmethod
    def save(path, data):
        with DB._lock:
            # Двойная защита от FileNotFoundError
            folder = os.path.dirname(path)
            if folder and not os.path.exists(folder): os.makedirs(folder)
            with open(path, 'w', encoding='utf-8') as f: 
                json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 🧠 МОДУЛЬ 3: ЯДРО ИИ (GEMINI + ART)
# ==============================================================================
class AI_Engine:
    @staticmethod
    def ask_gemini(prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=25).json()
            if 'candidates' in r:
                return r['candidates'][0]['content']['parts'][0]['text']
            return f"❌ Ошибка ответа: {r.get('error', {}).get('message', 'Неизвестно')}"
        except Exception as e:
            return f"❌ Ошибка связи с ядром ИИ: {str(e)}"

# ==============================================================================
# 📡 МОДУЛЬ 4: ТЕЛЕГРАМ API
# ==============================================================================
class TG:
    @staticmethod
    def call(m, p=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{m}"
        try: return requests.post(url, json=p, timeout=25).json()
        except: return {"ok": False}

    @staticmethod
    def send(cid, txt, kb=None, rkb=None, photo=None):
        p = {"chat_id": cid, "parse_mode": "HTML"}
        if kb: p["reply_markup"] = {"inline_keyboard": kb}
        if rkb: p["reply_markup"] = rkb
        
        if photo:
            p["photo"] = photo
            p["caption"] = txt
            return TG.call("sendPhoto", p)
        else:
            p["text"] = txt
            p["disable_web_page_preview"] = True
            return TG.call("sendMessage", p)

    @staticmethod
    def edit(cid, mid, txt):
        return TG.call("editMessageText", {"chat_id": cid, "message_id": mid, "text": txt, "parse_mode": "HTML"})

# ==============================================================================
# 🚀 МОДУЛЬ 5: ГЛАВНЫЙ КОНТРОЛЛЕР И ЛОГИКА
# ==============================================================================
app = Flask(__name__)

def set_state(uid, state):
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u: u[str(uid)] = {"name": "User", "state": "IDLE"}
    u[str(uid)]["state"] = state
    DB.save(Config.FILES["users"], u)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "TITAN V26.0 OMEGA IS LIVE", 200
    upd = request.get_json()
    if not upd: return "OK", 200

    # --------------------------------------------------------------------------
    # 👑 ОБРАБОТКА ИНЛАЙН-КНОПОК (АДМИНКА)
    # --------------------------------------------------------------------------
    if "callback_query" in upd:
        cb = upd["callback_query"]; uid = cb["from"]["id"]; cid = cb["message"]["chat"]["id"]; data = cb["data"]
        admins = DB.load(Config.FILES["admins"])
        if uid not in admins: return "OK", 200

        if data == "a_st":
            s = DB.load(Config.FILES["stats"])
            u = DB.load(Config.FILES["users"])
            TG.send(cid, f"📊 <b>СТАТИСТИКА СИСТЕМЫ</b>\n👥 Юзеров: {len(u)}\n🧠 Запросов ИИ: {s.get('ai_calls',0)}\n🎨 Артов: {s.get('arts',0)}")
        elif data == "a_log":
            if os.path.exists(Config.FILES["log"]):
                with open(Config.FILES["log"], 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendDocument", data={"chat_id": cid}, files={"document": ('titan_v26.log', f)})
            else: TG.send(cid, "❌ Лог файл пуст.")
        elif data == "a_bc":
            set_state(uid, "WAIT_BC")
            TG.send(cid, "📢 <b>РЕЖИМ РАССЫЛКИ</b>\nОтправьте или перешлите текст/фото:", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True})
        elif data == "a_ulist":
            u = DB.load(Config.FILES["users"])
            txt = "👥 <b>ЮЗЕРЫ:</b>\n" + "\n".join([f"• {u[i]['name']} (<code>{i}</code>)" for i in u])
            TG.send(cid, txt[:4000])
        elif data == "a_add_adm":
            set_state(uid, "WAIT_ADD_ADM")
            TG.send(cid, "🔑 Введите ID нового администратора:")
        return "OK", 200

    # --------------------------------------------------------------------------
    # 💬 ОБРАБОТКА СООБЩЕНИЙ
    # --------------------------------------------------------------------------
    if "message" not in upd: return "OK", 200
    m = upd["message"]; cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text") or m.get("caption") or ""

    # Регистрация юзера
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u:
        u[str(uid)] = {"name": m["from"].get("first_name", "User"), "state": "IDLE"}
        DB.save(Config.FILES["users"], u)
    
    state = u[str(uid)].get("state", "IDLE")
    admins = DB.load(Config.FILES["admins"])
    is_admin = uid in admins

    # КЛАВИАТУРЫ
    kb_main = {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}], 
                            [{"text": "👤 Мой профиль"}, {"text": "🆘 Помощь FAQ"}],
                            [{"text": "🔍 Поиск по ID"}]], "resize_keyboard": True}
    kb_cancel = {"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        set_state(uid, "IDLE")
        TG.send(cid, f"🌌 <b>TITAN V26.0 OMEGA</b>\nДобро пожаловать в систему!", rkb=kb_main)
        return "OK", 200

    if txt == "/admin" and is_admin:
        kb_adm = [[{"text": "📢 Рассылка", "callback_data": "a_bc"}, {"text": "📊 Стата", "callback_data": "a_st"}],
                  [{"text": "📑 Логи", "callback_data": "a_log"}, {"text": "👥 Юзеры", "callback_data": "a_ulist"}],
                  [{"text": "🔑 +Админ", "callback_data": "a_add_adm"}]]
        TG.send(cid, "👑 <b>АДМИН ПАНЕЛЬ</b>", kb=kb_adm)
        return "OK", 200

    # --------------------------------------------------------------------------
    # ⚙️ ОБРАБОТКА СОСТОЯНИЙ (FSM)
    # --------------------------------------------------------------------------
    if state == "AI_MODE" and txt:
        # Прогресс бар
        res = TG.send(cid, "⏳ [░░░░░░░░░░] 10% (Анализ...)")
        mid = res.get("result", {}).get("message_id")
        
        # Запрос к Gemini
        answer = AI_Engine.ask_gemini(txt)
        TG.edit(cid, mid, "⏳ [▓▓▓▓▓▓░░░░] 60% (Генерация...)")
        
        # Эффект плавного печатания
        words = answer.split()
        out = "✨ <b>Ответ ИИ:</b>\n\n"
        for i in range(0, len(words), 5):
            out += " ".join(words[i:i+5]) + " "
            TG.edit(cid, mid, out + "▌")
            time.sleep(0.3)
        TG.edit(cid, mid, out)
        
        # Обновление статистики
        s = DB.load(Config.FILES["stats"])
        s["ai_calls"] = s.get("ai_calls", 0) + 1
        DB.save(Config.FILES["stats"], s)

    elif state == "ART_MODE" and txt:
        TG.send(cid, "👨‍🎨 <i>Синтезирую нейро-арт... (5-10 сек)</i>")
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true&seed={uid}"
        TG.send(cid, f"✅ <b>Арт готов!</b>\nЗапрос: {txt}", photo=img)
        
        s = DB.load(Config.FILES["stats"])
        s["arts"] = s.get("arts", 0) + 1
        DB.save(Config.FILES["stats"], s)

    elif state == "WAIT_BC" and is_admin:
        photo_id = m.get("photo")[-1]["file_id"] if "photo" in m else None
        success = 0
        TG.send(cid, "🚀 <i>Рассылка пошла...</i>")
        for user_id in u:
            try:
                res = TG.send(int(user_id), txt, photo=photo_id)
                if res.get("ok"): success += 1
                time.sleep(0.05)
            except: pass
        set_state(uid, "IDLE")
        TG.send(cid, f"✅ Рассылка завершена!\nПолучили: {success} юзеров.", rkb=kb_main)

    elif state == "WAIT_ADD_ADM" and uid == Config.MAIN_ADMIN_ID:
        try:
            new_admin = int(txt)
            if new_admin not in admins:
                admins.append(new_admin)
                DB.save(Config.FILES["admins"], admins)
            TG.send(cid, f"✅ Пользователь <code>{new_admin}</code> назначен админом!", rkb=kb_main)
            set_state(uid, "IDLE")
        except: TG.send(cid, "❌ Ошибка. Нужно ввести числовой ID.")

    # --------------------------------------------------------------------------
    # 🔘 ОБРАБОТКА МЕНЮ
    # --------------------------------------------------------------------------
    elif txt == "🤖 Начать общаться":
        set_state(uid, "AI_MODE")
        TG.send(cid, "🧠 <b>Режим ИИ активирован.</b>\nЗадавай любые вопросы:", rkb=kb_cancel)
    elif txt == "🎨 Создать арт":
        set_state(uid, "ART_MODE")
        TG.send(cid, "🎨 <b>Режим Художника.</b>\nЧто нужно нарисовать?", rkb=kb_cancel)
    elif txt == "👤 Мой профиль":
        TG.send(cid, f"👤 <b>ВАШ ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {'Администратор' if is_admin else 'Пользователь'}")
    elif txt == "🆘 Помощь FAQ":
        TG.send(cid, "🆘 <b>СПРАВКА</b>\nБот умеет отвечать на вопросы и рисовать арты.\nИспользуйте кнопки меню.")
    elif txt == "🔍 Поиск по ID":
        TG.send(cid, "🔍 <i>Эта функция будет доступна в следующем обновлении (V26.1)</i>")

    return "OK", 200

if __name__ == "__main__":
    DB.init()
    logging.basicConfig(filename=Config.FILES["log"], level=logging.INFO, format='%(asctime)s %(message)s')
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
            
