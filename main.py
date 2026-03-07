import os, sys, json, time, logging, requests
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ МОДУЛЬ 1: КОНФИГУРАЦИЯ (V26.0 PROFILE, ACTIONS & COMMANDS)
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA FINAL"
    BOT_TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
    GEMINI_API_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
    MAIN_ADMIN_ID = 5378010557
    
    ROOT_DIR = "TITAN_DATA_V26"
    FILES = {
        "users": f"{ROOT_DIR}/users.json",
        "admins": f"{ROOT_DIR}/admins.json",
        "stats": f"{ROOT_DIR}/stats.json",
        "log": f"{ROOT_DIR}/titan.log"
    }

# ==============================================================================
# 📝 МОДУЛЬ 2: СУПЕР-БАЗА ДАННЫХ (БЕЗ ОШИБОК 500)
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
            except: return {}

    @staticmethod
    def save(path, data):
        with DB._lock:
            folder = os.path.dirname(path)
            if not os.path.exists(folder): os.makedirs(folder)
            with open(path, 'w', encoding='utf-8') as f: 
                json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 🧠 МОДУЛЬ 3: ЯДРО ИИ (ИСПРАВЛЕННАЯ МОДЕЛЬ GEMINI)
# ==============================================================================
class AI_Engine:
    @staticmethod
    def ask_gemini(prompt):
        # Используем gemini-1.5-flash-latest для максимальной совместимости
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={Config.GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=25).json()
            if 'candidates' in r:
                return r['candidates'][0]['content']['parts'][0]['text']
            # Если модель не найдена, пробуем резервный вариант
            return f"❌ Ошибка ИИ: {r.get('error', {}).get('message', 'Неизвестно')}"
        except Exception as e:
            return f"❌ Критическая ошибка связи: {str(e)}"

# ==============================================================================
# 📡 МОДУЛЬ 4: ТЕЛЕГРАМ API (ОМЕГА-ОТПРАВКА)
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
            p["photo"], p["caption"] = photo, txt
            return TG.call("sendPhoto", p)
        p["text"], p["disable_web_page_preview"] = txt, True
        return TG.call("sendMessage", p)

    @staticmethod
    def edit(cid, mid, txt):
        return TG.call("editMessageText", {"chat_id": cid, "message_id": mid, "text": txt, "parse_mode": "HTML"})

# ==============================================================================
# 🚀 МОДУЛЬ 5: ГЛАВНЫЙ КОНТРОЛЛЕР
# ==============================================================================
app = Flask(__name__)

def set_state(uid, state):
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u: u[str(uid)] = {"name": "User"}
    u[str(uid)]["state"] = state
    DB.save(Config.FILES["users"], u)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "TITAN V26.0 OMEGA ONLINE", 200
    upd = request.get_json()
    if not upd: return "OK", 200

    # CALLBACK (Инлайн кнопки)
    if "callback_query" in upd:
        cb = upd["callback_query"]; uid, cid, data = cb["from"]["id"], cb["message"]["chat"]["id"], cb["data"]
        admins = DB.load(Config.FILES["admins"])
        if uid not in admins: return "OK", 200

        if data == "a_st":
            s, users = DB.load(Config.FILES["stats"]), DB.load(Config.FILES["users"])
            TG.send(cid, f"📊 <b>СТАТИСТИКА</b>\nЮзеры: {len(users)}\nИИ: {s.get('ai_calls',0)}\nАрты: {s.get('arts',0)}")
        elif data == "a_bc":
            set_state(uid, "WAIT_BC")
            TG.send(cid, "📢 <b>РЕЖИМ РАССЫЛКИ</b>\nОтправь текст или фото (можно переслать):", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True})
        elif data == "a_log":
            if os.path.exists(Config.FILES["log"]):
                with open(Config.FILES["log"], 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendDocument", data={"chat_id": cid}, files={"document": ('titan.log', f)})
            else: TG.send(cid, "❌ Лог пуст.")
        return "OK", 200

    if "message" not in upd: return "OK", 200
    m = upd["message"]; cid, uid = m["chat"]["id"], m["from"]["id"]
    txt = m.get("text") or m.get("caption") or ""

    # Авто-регистрация
    u = DB.load(Config.FILES["users"])
    if str(uid) not in u:
        u[str(uid)] = {"name": m["from"].get("first_name", "User"), "state": "IDLE"}
        DB.save(Config.FILES["users"], u)
    
    state = u[str(uid)].get("state", "IDLE")
    is_admin = uid in DB.load(Config.FILES["admins"])

    # Меню
    kb_main = {"keyboard": [[{"text": "🤖 Начать общаться"}, {"text": "🎨 Создать арт"}], 
                            [{"text": "👤 Мой профиль"}, {"text": "🆘 Помощь FAQ"}]], "resize_keyboard": True}
    if is_admin: kb_main["keyboard"].append([{"text": "/admin"}])
    kb_cancel = {"keyboard": [[{"text": "❌ ОТМЕНИТЬ"}]], "resize_keyboard": True}

    if txt == "/start" or txt == "❌ ОТМЕНИТЬ":
        set_state(uid, "IDLE")
        TG.send(cid, f"🌌 <b>TITAN V26.0 OMEGA</b>\nСистема готова к работе!", rkb=kb_main)
        return "OK", 200

    # ⚙️ ЛОГИКА СОСТОЯНИЙ
    if state == "AI_MODE" and txt:
        res = TG.send(cid, "⏳ [▓░░░░░░░░░] 10% (Анализ...)")
        mid = res.get("result", {}).get("message_id")
        
        full_ans = AI_Engine.ask_gemini(txt)
        TG.edit(cid, mid, "⏳ [▓▓▓▓▓▓░░░░] 60% (Печатаю...)")
        
        words = full_ans.split()
        curr = "✨ <b>Ответ ИИ:</b>\n\n"
        for i in range(0, len(words), 5):
            curr += " ".join(words[i:i+5]) + " "
            TG.edit(cid, mid, curr + "▌")
            time.sleep(0.3)
        TG.edit(cid, mid, curr)
        
        s = DB.load(Config.FILES["stats"])
        s["ai_calls"] = s.get("ai_calls", 0) + 1
        DB.save(Config.FILES["stats"], s)

    elif state == "ART_MODE" and txt:
        TG.send(cid, "👨‍🎨 <i>Рисую ваш запрос...</i>")
        img = f"https://image.pollinations.ai/prompt/{txt}?nologo=true&seed={uid}"
        TG.send(cid, f"✅ Готово: {txt}", photo=img)
        s = DB.load(Config.FILES["stats"]); s["arts"] = s.get("arts", 0) + 1; DB.save(Config.FILES["stats"], s)

    elif state == "WAIT_BC" and is_admin:
        photo = m.get("photo")[-1]["file_id"] if "photo" in m else None
        success = 0
        for user_id in u:
            try:
                if TG.send(int(user_id), txt, photo=photo).get("ok"): success += 1
                time.sleep(0.05)
            except: pass
        set_state(uid, "IDLE")
        TG.send(cid, f"✅ Рассылка завершена! Получили: {success}", rkb=kb_main)

    # 🔘 КНОПКИ МЕНЮ
    elif txt == "🤖 Начать общаться":
        set_state(uid, "AI_MODE")
        TG.send(cid, "🧠 <b>Режим ИИ включен.</b> Пиши вопрос:", rkb=kb_cancel)
    elif txt == "🎨 Создать арт":
        set_state(uid, "ART_MODE")
        TG.send(cid, "🎨 <b>Режим Художника.</b> Что рисуем?", rkb=kb_cancel)
    elif txt == "👤 Мой профиль":
        TG.send(cid, f"👤 <b>ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {'Админ' if is_admin else 'Юзер'}")
    elif txt == "/admin" and is_admin:
        kb_adm = [[{"text": "📢 Рассылка", "callback_data": "a_bc"}, {"text": "📊 Стата", "callback_data": "a_st"}],
                  [{"text": "📑 Логи", "callback_data": "a_log"}]]
        TG.send(cid, "👑 <b>ADMIN PANEL</b>", kb=kb_adm)

    return "OK", 200

if __name__ == "__main__":
    DB.init()
    logging.basicConfig(filename=Config.FILES["log"], level=logging.INFO, format='%(asctime)s %(message)s')
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
            
