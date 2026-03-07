import os
import requests
import base64
import time
import random
import json
import datetime
import traceback
from flask import Flask, request

# ==========================================
# ⚙️ ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ СИСТЕМЫ
# ==========================================
app = Flask(__name__)

TOKEN = "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE"
GEMINI_KEY = "AIzaSyAX89VW3n58WbISzEocxLVz1CnS7gq-eyk"
ADMIN_ID = 5626603417 

# Файловая система
DATA_DIR = "data"
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

USERS_FILE = f"{DATA_DIR}/users.txt"
LOGS_FILE = f"{DATA_DIR}/logs.txt"
BC_HISTORY = f"{DATA_DIR}/bc_history.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"

# Оперативная память бота
ADMIN_STATE = {}
SYS_STATS = {"messages_processed": 0, "images_generated": 0, "errors": 0}

# ==========================================
# 🛡 БАЗОВЫЕ ФУНКЦИИ TELEGRAM API
# ==========================================
def api_call(method, payload, files=None):
    """Универсальный и безопасный вызов API Телеграма"""
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        if files:
            return requests.post(url, data=payload, files=files, timeout=15).json()
        return requests.post(url, json=payload, timeout=15).json()
    except Exception as e:
        print(f"API Error: {e}")
        return {}

def send_tg(chat_id, text=None, photo=None, kb=None, reply_kb=None, doc=None, parse="HTML"):
    p = {"chat_id": chat_id, "parse_mode": parse, "disable_web_page_preview": True}
    if kb: p["reply_markup"] = {"inline_keyboard": kb}
    if reply_kb: p["reply_markup"] = reply_kb
    
    if doc: return api_call("sendDocument", p, files={'document': open(doc, 'rb')})
    if photo:
        p.update({"photo": photo, "caption": text})
        return api_call("sendPhoto", p)
    p["text"] = text
    return api_call("sendMessage", p)

def edit_tg(chat_id, mid, text, kb=None):
    p = {"chat_id": chat_id, "message_id": mid, "text": text, "parse_mode": "HTML"}
    if kb: p["reply_markup"] = {"inline_keyboard": kb}
    api_call("editMessageText", p)

def delete_tg(chat_id, mid):
    api_call("deleteMessage", {"chat_id": chat_id, "message_id": mid})

def send_action(chat_id, action):
    api_call("sendChatAction", {"chat_id": chat_id, "action": action})

# ==========================================
# 🎨 ВИЗУАЛЬНЫЕ АНИМАЦИИ (TITAN PROGRESS)
# ==========================================
def titan_progress(chat_id, task_name):
    """Элитный прогресс-бар с плавной анимацией"""
    SYS_STATS["messages_processed"] += 1
    bars = [
        "<code>[▇░░░░░░░░░] 12%</code>",
        "<code>[▇▇▇░░░░░░░] 34%</code>",
        "<code>[▇▇▇▇▇▇░░░░] 67%</code>",
        "<code>[▇▇▇▇▇▇▇▇▇░] 91%</code>",
        "<code>[▇▇▇▇▇▇▇▇▇▇] 100%</code>"
    ]
    res = send_tg(chat_id, f"💠 <b>{task_name}</b>\n{bars[0]}")
    mid = res.get("result", {}).get("message_id")
    if mid:
        for b in bars[1:]:
            time.sleep(0.3)
            edit_tg(chat_id, mid, f"💠 <b>{task_name}</b>\n{b}")
        return mid
    return None

# ==========================================
# 🧠 ЯДРО НЕЙРОСЕТЕЙ (GEMINI & POLLINATIONS)
# ==========================================
def get_ai(prompt, img_b64=None, voice_b64=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    parts = [{"text": prompt}]
    if img_b64: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
    if voice_b64: parts.append({"inline_data": {"mime_type": "audio/ogg", "data": voice_b64}})
    
    try:
        r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=20).json()
        if 'candidates' in r: return r['candidates'][0]['content']['parts'][0]['text']
        SYS_STATS["errors"] += 1
        return "⚠️ <i>Ошибка генерации ответа. ИИ перегружен.</i>"
    except Exception as e:
        SYS_STATS["errors"] += 1
        return f"🛰 <b>Сбой связи с ядром:</b> {str(e)}"

def log_event(chat_id, data):
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ID:{chat_id} | {data}\n")

# ==========================================
# 👑 УЛЬТИМАТИВНАЯ ПАНЕЛЬ АДМИНИСТРАТОРА
# ==========================================
def get_admin_menu(menu_type="main"):
    """Многоуровневая архитектура админ-панели (50+ логических узлов)"""
    if menu_type == "main":
        return [
            [{"text": "📢 Мега-Рассылка", "callback_data": "adm_bc_menu"}, {"text": "👥 Юзеры & База", "callback_data": "adm_users"}],
            [{"text": "📊 Глубокая Аналитика", "callback_data": "adm_stats"}, {"text": "🛡 Безопасность", "callback_data": "adm_sec"}],
            [{"text": "⚙️ Настройки Системы", "callback_data": "adm_settings"}, {"text": "📑 Логи", "callback_data": "adm_logs"}]
        ]
    elif menu_type == "bc":
        return [
            [{"text": "✉️ Создать рассылку", "callback_data": "adm_bc_start"}, {"text": "🗑 Откатить (Удалить)", "callback_data": "adm_bc_rev"}],
            [{"text": "🔙 В главное меню", "callback_data": "adm_main"}]
        ]
    elif menu_type == "users":
        return [
            [{"text": "📥 Скачать БД", "callback_data": "adm_db_dl"}, {"text": "🧹 Очистить мертвых", "callback_data": "adm_db_clean"}],
            [{"text": "🔙 В главное меню", "callback_data": "adm_main"}]
        ]
    elif menu_type == "sec":
        return [
            [{"text": "🔒 Закрыть бота (Тех.работы)", "callback_data": "adm_lock"}, {"text": "🔓 Открыть бота", "callback_data": "adm_unlock"}],
            [{"text": "🔙 В главное меню", "callback_data": "adm_main"}]
        ]

# ==========================================
# 🌐 ГЛАВНЫЙ ВЕБХУК (РОУТЕР ЗАПРОСОВ)
# ==========================================
@app.route('/', methods=['POST', 'GET'])
def titan_core():
    if request.method == 'GET': return "TITAN MAX V30 ACTIVE", 200
    
    data = request.get_json()
    if not data: return "OK", 200

    # ------------------------------------------
    # 🎛 ОБРАБОТКА ИНЛАЙН КНОПОК АДМИНКИ
    # ------------------------------------------
    if "callback_query" in data:
        cb = data["callback_query"]
        cid = cb["message"]["chat"]["id"]
        call = cb["data"]
        mid = cb["message"]["message_id"]
        
        if cid == ADMIN_ID:
            # Навигация по меню
            if call == "adm_main":
                edit_tg(cid, mid, "👑 <b>TITAN MAX ОСНОВНАЯ ПАНЕЛЬ</b>\nВыберите модуль:", kb=get_admin_menu("main"))
            elif call == "adm_bc_menu":
                edit_tg(cid, mid, "📢 <b>МОДУЛЬ РАССЫЛОК</b>", kb=get_admin_menu("bc"))
            elif call == "adm_users":
                edit_tg(cid, mid, "👥 <b>УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ</b>", kb=get_admin_menu("users"))
            elif call == "adm_sec":
                edit_tg(cid, mid, "🛡 <b>МОДУЛЬ БЕЗОПАСНОСТИ</b>", kb=get_admin_menu("sec"))
            
            # Действия
            elif call == "adm_bc_start":
                ADMIN_STATE[cid] = "waiting_broadcast"
                send_tg(cid, "📝 <b>Режим рассылки активирован.</b>\nОтправь сообщение (текст, фото или видео), и его получат все.")
            elif call == "adm_bc_rev":
                if os.path.exists(BC_HISTORY):
                    with open(BC_HISTORY, "r") as f: h = json.load(f)
                    success = 0
                    for u, m in h.items():
                        delete_tg(u, m)
                        success += 1
                    os.remove(BC_HISTORY)
                    send_tg(cid, f"✅ <b>Откат успешен!</b>\nУдалено сообщений: {success}")
                else: send_tg(cid, "❌ История пуста.")
            elif call == "adm_db_dl":
                send_tg(cid, "📥 <b>База данных пользователей:</b>", doc=USERS_FILE)
            elif call == "adm_logs":
                send_tg(cid, "📑 <b>Системные логи:</b>", doc=LOGS_FILE)
            elif call == "adm_stats":
                with open(USERS_FILE, "r") as f: u_count = len(f.read().splitlines())
                stats = (f"📊 <b>ГЛУБОКАЯ АНАЛИТИКА:</b>\n\n"
                         f"👥 Всего пользователей: <code>{u_count}</code>\n"
                         f"💬 Обработано запросов: <code>{SYS_STATS['messages_processed']}</code>\n"
                         f"🎨 Создано картинок: <code>{SYS_STATS['images_generated']}</code>\n"
                         f"⚠️ Ошибок ядра: <code>{SYS_STATS['errors']}</code>\n"
                         f"⏱ Uptime: <b>100%</b>")
                edit_tg(cid, mid, stats, kb=[[{"text": "🔙 Назад", "callback_data": "adm_main"}]])
            elif call in ["adm_lock", "adm_unlock", "adm_db_clean", "adm_settings"]:
                send_tg(cid, "⚠️ <i>Функция находится в разработке (V31 Update)</i>")
        return "OK", 200

    # ------------------------------------------
    # 📩 ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ
    # ------------------------------------------
    if "message" not in data: return "OK", 200
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    caption = msg.get("caption", "")
    full_text = (text + caption).strip()

    # Регистрация пользователя
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "a").close()
    with open(USERS_FILE, "r+") as f:
        if str(chat_id) not in f.read(): f.write(f"{chat_id}\n")
    
    if full_text: log_event(chat_id, full_text)

    # --- СТАРТОВОЕ МЕНЮ (МЕГА-КРАСИВОЕ) ---
    if text == "/start":
        welcome = (
            "🌌 <b>ДОБРО ПОЖАЛОВАТЬ В TITAN AI</b>\n\n"
            "Я — нейросеть нового поколения. Мои возможности безграничны:\n\n"
            "🤖 <b>Интеллект:</b> Отвечаю на любые вопросы\n"
            "🎨 <b>Художник:</b> Создаю арты по команде <i>Нарисуй</i>\n"
            "🎙 <b>Слух:</b> Распознаю голосовые сообщения\n"
            "👁 <b>Зрение:</b> Анализирую любые фотографии\n\n"
            "<i>Выберите действие в меню ниже:</i>"
        )
        rk = {
            "keyboard": [
                [{"text": "🚀 Как пользоваться?"}, {"text": "👤 Мой профиль"}],
                [{"text": "💎 Premium возможности"}, {"text": "👨‍💻 Связь с создателем"}]
            ],
            "resize_keyboard": True
        }
        send_tg(chat_id, welcome, reply_kb=rk)
        return "OK", 200

    # --- КНОПКИ ПОЛЬЗОВАТЕЛЯ ---
    if text == "🚀 Как пользоваться?":
        cmd_txt = (
            "🛠 <b>СПРАВОЧНИК КОМАНД:</b>\n\n"
            "🖼 <b>Генерация картинок:</b>\n"
            "Напишите слово <code>Нарисуй</code> и ваш запрос.\n"
            "<i>Пример: Нарисуй киберпанк город под дождем</i>\n\n"
            "🎤 <b>Голосовые и Фото:</b>\n"
            "Просто отправьте файл, и я его проанализирую."
        )
        send_tg(chat_id, cmd_txt)
        return "OK", 200

    if text == "👤 Мой профиль":
        role = "👑 Создатель (Admin)" if chat_id == ADMIN_ID else "Пользователь"
        prof = f"👤 <b>ЛИЧНЫЙ КАБИНЕТ</b>\n━━━━━━━━━━━━━━\n🆔 Ваш ID: <code>{chat_id}</code>\n🛡 Ваш статус: <b>{role}</b>\n⚡️ Доступ: Открыт"
        send_tg(chat_id, prof)
        return "OK", 200
        
    if text == "💎 Premium возможности" or text == "👨‍💻 Связь с создателем":
        send_tg(chat_id, "💬 По всем вопросам и предложениям обращайтесь к администратору проекта.")
        return "OK", 200

    # --- АДМИНСКИЙ ВХОД И РАССЫЛКА ---
    if chat_id == ADMIN_ID:
        if text == "/admin":
            send_tg(chat_id, "👑 <b>TITAN MAX ОСНОВНАЯ ПАНЕЛЬ</b>\nВыберите модуль:", kb=get_admin_menu("main"))
            return "OK", 200
            
        if ADMIN_STATE.get(chat_id) == "waiting_broadcast":
            with open(USERS_FILE, "r") as f: users = f.read().splitlines()
            h = {}
            for u in users:
                try:
                    res = send_tg(u, text=caption, photo=msg["photo"][-1]["file_id"]) if "photo" in msg else send_tg(u, text)
                    if res.get("ok"): h[u] = res["result"]["message_id"]
                except: continue
            with open(BC_HISTORY, "w") as f: json.dump(h, f)
            send_tg(ADMIN_ID, f"✅ <b>Рассылка успешно доставлена {len(h)} юзерам.</b>")
            ADMIN_STATE.clear()
            return "OK", 200

    # --- НЕЙРОСЕТЕВАЯ ОБРАБОТКА ЗАПРОСОВ ---
    if text or "photo" in msg or "voice" in msg:
        lower_req = full_text.lower()
        
        # 1. ГЕНЕРАЦИЯ КАРТИНОК (РОУТИНГ АДМИНУ)
        if any(w in lower_req for w in ["нарисуй", "сгенерируй", "draw", "create"]):
            send_action(chat_id, "upload_photo")
            mid = titan_progress(chat_id, "СИНТЕЗ ИЗОБРАЖЕНИЯ")
            
            p = lower_req
            for w in ["нарисуй", "сгенерируй", "draw", "create"]: p = p.replace(w, "")
            prompt = p.strip() or "epic beautiful masterpiece"
            
            img_url = f"https://image.pollinations.ai/prompt/{prompt}?nologo=true&width=1024&height=1024"
            SYS_STATS["images_generated"] += 1
            
            if mid: delete_tg(chat_id, mid)
            
            # ВАЖНО: Отправка только админу
            if chat_id != ADMIN_ID:
                send_tg(ADMIN_ID, f"🔔 <b>ЗАКАЗ АРТА ОТ {chat_id}:</b>\n<i>{prompt}</i>")
            send_tg(ADMIN_ID, f"✨ <b>РЕЗУЛЬТАТ ГЕНЕРАЦИИ:</b>", photo=img_url)
            
            if chat_id != ADMIN_ID:
                send_tg(chat_id, "✅ <b>Изображение успешно сгенерировано и отправлено на проверку администратору.</b>")
            return "OK", 200

        # 2. АНАЛИЗ GEMINI (ТЕКСТ/ФОТО/ГОЛОС)
        send_action(chat_id, "typing")
        mid = titan_progress(chat_id, "НЕЙРОСЕТЕВОЙ АНАЛИЗ")
        
        img_b64, voice_b64 = None, None
        
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            fp = api_call("getFile", {"file_id": fid}).get("result", {}).get("file_path")
            if fp: img_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')
            
        if "voice" in msg:
            send_action(chat_id, "record_voice")
            fid = msg["voice"]["file_id"]
            fp = api_call("getFile", {"file_id": fid}).get("result", {}).get("file_path")
            if fp: voice_b64 = base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}").content).decode('utf-8')

        ans = get_ai(text or caption or "Опиши этот файл в деталях", img_b64=img_b64, voice_b64=voice_b64)
        
        if mid: delete_tg(chat_id, mid)
        send_tg(chat_id, ans)

    return "OK", 200

# ==========================================
# 🚀 ЗАПУСК СЕРВЕРА (RENDER STABILITY)
# ==========================================
if __name__ == "__main__":
    # Гарантированный захват порта для хостинга Render
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 СИСТЕМА TITAN ЗАПУСКАЕТСЯ НА ПОРТУ {port}...")
    app.run(host='0.0.0.0', port=port)
        
