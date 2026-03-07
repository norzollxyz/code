import os, sys, json, time, base64, logging, requests, traceback
from datetime import datetime
from threading import Lock
from flask import Flask, request

# ==============================================================================
# ⚙️ MODULE 1: CONFIG
# ==============================================================================
class Config:
    VERSION = "V26.0 OMEGA FIX"
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
# 💾 MODULE 2: DATABASE & LOGS
# ==============================================================================
class DatabaseManager:
    _lock = Lock()

    @classmethod
    def init(cls):
        if not os.path.exists(Config.ROOT_DIR): os.makedirs(Config.ROOT_DIR)
        defaults = {Config.FILES["users"]: {}, Config.FILES["admins"]: [Config.MAIN_ADMIN_ID], Config.FILES["stats"]: {"ai_requests": 0, "images_generated": 0}}
        for path, data in defaults.items():
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

    @classmethod
    def read(cls, path):
        with cls._lock:
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: return {}

    @classmethod
    def write(cls, path, data):
        with cls._lock:
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 🧠 MODULE 3: AI CORE (GEMINI FIX)
# ==============================================================================
class GeminiController:
    @staticmethod
    def process_request(prompt, image_b64=None):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        parts = [{"text": prompt}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
        
        payload = {"contents": [{"parts": parts}]}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            res = r.json()
            if 'candidates' in res:
                return res['candidates'][0]['content']['parts'][0]['text']
            return f"❌ <b>Ошибка ИИ:</b> {res.get('error', {}).get('message', 'Неизвестная ошибка')}"
        except Exception as e:
            return f"🛰 <b>Ошибка связи:</b> {str(e)}"

# ==============================================================================
# 📡 MODULE 4: TELEGRAM INTERFACE
# ==============================================================================
class TG:
    @staticmethod
    def call(method, payload=None):
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/{method}"
        try: return requests.post(url, json=payload, timeout=30).json()
        except: return {"ok": False}

    @staticmethod
    def send(cid, txt, kb=None, rkb=None, photo=None):
        if photo:
            p = {"chat_id": cid, "photo": photo, "caption": txt, "parse_mode": "HTML"}
            if kb: p["reply_markup"] = {"inline_keyboard": kb}
            if rkb: p["reply_markup"] = rkb
            return TG.call("sendPhoto", p)
        p = {"chat_id": cid, "text": txt, "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb: p["reply_markup"] = {"inline_keyboard": kb}
        if rkb: p["reply_markup"] = rkb
        return TG.call("sendMessage", p)

# ==============================================================================
# 🚀 MODULE 5: BROADCAST ENGINE (PHOTO FIX)
# ==============================================================================
def execute_broadcast(admin_id, msg):
    users = DatabaseManager.read(Config.FILES["users"])
    text = msg.get("text") or msg.get("caption") or ""
    photo = msg.get("photo")[-1]["file_id"] if "photo" in msg else None
    
    success, failed = 0, 0
    status_msg = TG.send(admin_id, "🚀 <b>Рассылка запущена...</b>")
    mid = status_msg.get("result", {}).get("message_id")

    for uid in users:
        try:
            res = TG.send(uid, text, photo=photo)
            if res.get("ok"): success += 1
            else: failed += 1
            time.sleep(0.05)
        except: failed += 1

    report = f"✅ <b>Рассылка завершена!</b>\n\n📈 Успешно: {success}\n📉 Ошибок: {failed}"
    if mid: TG.call("editMessageText", {"chat_id": admin_id, "message_id": mid, "text": report, "parse_mode": "HTML"})
    else: TG.send(admin_id, report)

# ==============================================================================
# 🎮 MODULE 6: MAIN LOGIC
# ==============================================================================
app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def gateway():
    if request.method == 'GET': return "SYSTEM ACTIVE", 200
    
    upd = request.get_json()
    if not upd: return "OK", 200

    # Обработка кнопок админки
    if "callback_query" in upd:
        cb = upd["callback_query"]; uid = cb["from"]["id"]; cid = cb["message"]["chat"]["id"]; data = cb["data"]
        if uid != Config.MAIN_ADMIN_ID: return "OK", 200
        
        if data == "adm_broadcast":
            set_user_state(uid, "WAIT_BC")
            TG.send(cid, "📢 <b>РЕЖИМ РАССЫЛКИ</b>\nОтправьте или перешлите текст/фото:", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ ДЕЙСТВИЕ"}]], "resize_keyboard": True})
        elif data == "adm_stats":
            st = DatabaseManager.read(Config.FILES["stats"])
            TG.send(cid, f"📊 <b>СТАТИСТИКА:</b>\nИИ: {st.get('ai_requests',0)}\nАрты: {st.get('images_generated',0)}")
        return "OK", 200

    if "message" not in upd: return "OK", 200
    msg = upd["message"]; cid = msg["chat"]["id"]; uid = msg["from"]["id"]; text = msg.get("text", "")

    # Регистрация
    users = DatabaseManager.read(Config.FILES["users"])
    if str(uid) not in users:
        users[str(uid)] = {"name": msg["from"].get("first_name"), "state": "IDLE"}
        DatabaseManager.write(Config.FILES["users"], users)

    state = users.get(str(uid), {}).get("state", "IDLE")
    is_admin = uid == Config.MAIN_ADMIN_ID

    # Кнопки
    kb_main = {"keyboard": [[{"text": "🤖 Нейросеть Gemini"}, {"text": "🎨 Создать Арт"}], [{"text": "👤 Мой Профиль"}, {"text": "🛠 Помощь"}]], "resize_keyboard": True}
    if is_admin: kb_main["keyboard"].append([{"text": "👑 Панель Управления"}])

    if text == "/start" or text == "❌ ОТМЕНИТЬ ДЕЙСТВИЕ":
        set_user_state(uid, "IDLE")
        TG.send(cid, "🌌 <b>TITAN SYSTEM V26.0</b>\nВыберите действие:", rkb=kb_main)
        return "OK", 200

    # Состояния FSM
    if state == "WAIT_BC" and is_admin:
        execute_broadcast(uid, msg)
        set_user_state(uid, "IDLE")
        TG.send(cid, "🏠 Возврат в меню", rkb=kb_main)
    
    elif state == "AI_WAIT":
        TG.send(cid, "🤖 <i>ТИТАН думает...</i>")
        ans = GeminiController.process_request(text or msg.get("caption", "Опиши это"))
        TG.send(cid, ans, rkb=kb_main)
        set_user_state(uid, "IDLE")

    elif state == "ART_WAIT":
        TG.send(cid, "🎨 <i>Синтезирую арт...</i>")
        img_url = f"https://image.pollinations.ai/prompt/{text}?nologo=true&width=1024&height=1024"
        TG.send(cid, f"✅ <b>Готово!</b>\nЗапрос: {text}", photo=img_url, rkb=kb_main)
        set_user_state(uid, "IDLE")

    # Команды меню
    elif text == "🤖 Нейросеть Gemini":
        set_user_state(uid, "AI_WAIT")
        TG.send(cid, "🧠 Введите ваш запрос:", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ ДЕЙСТВИЕ"}]], "resize_keyboard": True})
    elif text == "🎨 Создать Арт":
        set_user_state(uid, "ART_WAIT")
        TG.send(cid, "🎨 Что нарисовать?", rkb={"keyboard": [[{"text": "❌ ОТМЕНИТЬ ДЕЙСТВИЕ"}]], "resize_keyboard": True})
    elif text == "👑 Панель Управления" and is_admin:
        kb_adm = [[{"text": "📢 Рассылка", "callback_data": "adm_broadcast"}, {"text": "📊 Статистика", "callback_data": "adm_stats"}]]
        TG.send(cid, "👑 <b>ADMIN PANEL</b>", kb=kb_adm)
    elif text == "👤 Мой Профиль":
        TG.send(cid, f"👤 <b>ПРОФИЛЬ</b>\n🆔 ID: <code>{uid}</code>\n🛡 Статус: {'Админ' if is_admin else 'Юзер'}")

    return "OK", 200

def set_user_state(uid, state):
    u = DatabaseManager.read(Config.FILES["users"])
    if str(uid) in u:
        u[str(uid)]["state"] = state
        DatabaseManager.write(Config.FILES["users"], u)

if __name__ == "__main__":
    DatabaseManager.init()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
        
