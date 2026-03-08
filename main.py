import os
import requests
import json
import logging
import threading
import time
import datetime
import random
from flask import Flask, request

# ==============================================================================
# ⚙️ КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    VERSION = "V26.1 OMEGA"
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8609459746:AAFF24zuVaODexXtAq7G_1ayB-s71watLeE")
    GROQ_KEY = os.environ.get("GROQ_KEY", "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")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "5378010557"))
    PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

USERS_DB = set()
USER_STATES = {}  # {'chat_id': 'waiting_for_broadcast'}
USER_CONTEXT = {}  # История диалогов
ADMIN_STATS = {
    'total_messages': 0,
    'total_images': 0,
    'start_time': datetime.datetime.now()
}
db_lock = threading.Lock()

# ==============================================================================
# 🧠 ЕДИНЫЙ МОЗГ - GROQ AI (ВСЕ ФУНКЦИИ ЧЕРЕЗ НЕГО)
# ==============================================================================
def ask_groq(prompt, system_prompt="Ты полезный ассистент TITAN. Отвечай кратко и по делу.", temp=0.7):
    """Универсальная функция для всех запросов к ИИ"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": 500
    }
    
    try:
        logger.info(f"GROQ Request: {prompt[:50]}...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"GROQ Error: {e}")
        return f"⚠️ Ошибка связи с ИИ: {str(e)[:50]}"

# ==============================================================================
# 🎨 КОНКРЕТНЫЕ ФУНКЦИИ (КАЖДАЯ ЧЕРЕЗ GROQ)
# ==============================================================================
def get_ai_quote():
    """ИИ генерирует цитату дня"""
    prompt = "Сгенерируй вдохновляющую цитату на сегодня. Короткую, мудрую, со смыслом. На русском языке. Добавь в конце имя автора (вымышленное или реальное)."
    system = "Ты генератор цитат. Создавай глубокие, запоминающиеся фразы."
    return ask_groq(prompt, system, temp=0.9)

def get_ai_wisdom():
    """ИИ генерирует мудрость дня"""
    prompt = "Напиши короткую житейскую мудрость или урок на сегодня. Что-то про жизнь, счастье, успех. На русском, 1-2 предложения."
    system = "Ты философ, делящийся мудростью простыми словами."
    return ask_groq(prompt, system, temp=0.8)

def get_ai_fact():
    """ИИ генерирует случайный факт"""
    prompt = "Расскажи интересный, малоизвестный факт о мире, науке или технологиях. На русском языке. Факт должен быть правдивым."
    system = "Ты энциклопедия. Знаешь всё и делишься интересными фактами."
    return ask_groq(prompt, system, temp=0.7)

def get_ai_joke():
    """ИИ генерирует шутку"""
    prompt = "Напиши короткую смешную шутку или анекдот на русском. Не пошло, просто с юмором."
    system = "Ты стендап-комик. Твои шутки смешные и уместные."
    return ask_groq(prompt, system, temp=0.9)

def get_ai_advice():
    """ИИ дает совет на сегодня"""
    prompt = "Дай короткий полезный совет на сегодня. Про продуктивность, отдых, отношения или саморазвитие. 1 предложение."
    system = "Ты жизненный коуч. Даешь короткие, но ценные советы."
    return ask_groq(prompt, system, temp=0.8)

def get_ai_news():
    """ИИ придумывает новость дня (шутливую)"""
    prompt = "Придумай смешную или абсурдную новость дня в стиле 'Панорама'. Коротко, с юмором. На русском."
    system = "Ты редактор сатирического новостного агентства."
    return ask_groq(prompt, system, temp=0.95)

def get_ai_poem():
    """ИИ пишет короткое стихотворение"""
    prompt = "Напиши короткое четверостишие на русском. Про жизнь, природу или технологии. Рифма обязательна."
    system = "Ты поэт. Пишешь красиво и с душой."
    return ask_groq(prompt, system, temp=0.9)

def get_ai_weather():
    """ИИ придумывает 'погоду'"""
    prompt = "Придумай забавный прогноз погоды на сегодня. Например: 'Сегодня облачно, возможны осадки в виде печенья'. Креативно!"
    system = "Ты синоптик с отличным чувством юмора."
    return ask_groq(prompt, system, temp=0.9)

def get_ai_horoscope():
    """ИИ генерирует гороскоп"""
    signs = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
    sign = random.choice(signs)
    prompt = f"Напиши короткий смешной гороскоп для знака {sign} на сегодня. С юмором, но с добрым посылом."
    system = "Ты астролог, но не серьезный, а прикольный."
    return f"🔮 <b>{sign}:</b>\n{ask_groq(prompt, system, temp=0.9)}"

def get_ai_motivation():
    """Мотивация от ИИ"""
    prompt = "Напиши короткую мотивационную фразу на сегодня. Чтобы захотелось встать и что-то сделать!"
    system = "Ты мотивационный спикер. Заряжаешь энергией."
    return ask_groq(prompt, system, temp=0.8)

# ==============================================================================
# 🎨 ГЛАВНОЕ МЕНЮ (ДЛЯ ВСЕХ)
# ==============================================================================
def get_main_keyboard():
    """Простое и понятное главное меню"""
    keyboard = [
        ["👤 Личный кабинет", "❓ Помощь"],
        ["💬 Связаться с ИИ", "🎨 Сгенерировать"],
        ["📢 Связь с админом"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# 👑 АДМИН-МЕНЮ (ВСЕ ФУНКЦИИ ЧЕРЕЗ ИИ)
# ==============================================================================
def get_admin_keyboard():
    """Каждая кнопка генерирует что-то через ИИ"""
    keyboard = [
        # Рассылка и статистика
        ["📢 РАССЫЛКА", "📊 СТАТИСТИКА"],
        
        # ВСЁ ГЕНЕРИРУЕТ ИИ (10+ функций)
        ["🎯 Цитата дня (ИИ)", "🧠 Мудрость дня (ИИ)"],
        ["📰 Факт дня (ИИ)", "😄 Шутка (ИИ)"],
        ["💡 Совет дня (ИИ)", "📢 Новость (ИИ)"],
        ["📝 Стих (ИИ)", "🔮 Гороскоп (ИИ)"],
        ["⚡ Мотивация (ИИ)", "🌤 Погода (ИИ)"],
        
        # Технические функции
        ["💰 Курс валют", "🌍 Мой IP"],
        ["👥 Все юзеры", "📤 Экспорт"],
        ["🔙 Назад в меню"]
    ]
    return {"keyboard": keyboard, "resize_keyboard": True}

# ==============================================================================
# 📤 ФУНКЦИИ TELEGRAM
# ==============================================================================
def send_msg(chat_id, text, kb=None, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if kb:
        payload["reply_markup"] = kb
    try:
        return requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def send_typing(chat_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": "typing"})

def edit_msg(chat_id, msg_id, text, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode}
    try:
        return requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return None

def delete_msg(chat_id, msg_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "message_id": msg_id})
    except:
        pass

def copy_msg(to_chat, from_chat, msg_id):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/copyMessage"
    try:
        response = requests.post(url, json={"chat_id": to_chat, "from_chat_id": from_chat, "message_id": msg_id}, timeout=15)
        return response.status_code == 200
    except:
        return False

def get_currency():
    """Курс валют (реальный)"""
    try:
        r = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=5)
        data = r.json()
        usd = data['Valute']['USD']['Value']
        eur = data['Valute']['EUR']['Value']
        cny = data['Valute']['CNY']['Value']
        return f"💰 <b>Курс ЦБ:</b>\nUSD: {usd:.2f}₽\nEUR: {eur:.2f}₽\nCNY: {cny:.2f}₽"
    except:
        return "💰 Курс временно недоступен"

def get_ip():
    """Внешний IP"""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return f"🌍 <b>Внешний IP:</b> {r.json()['ip']}"
    except:
        return "🌍 IP не определен"

def generate_image(prompt):
    """Генерация изображения"""
    encoded = requests.utils.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

# ==============================================================================
# 📡 ОБРАБОТЧИК СООБЩЕНИЙ
# ==============================================================================
@app.route('/', methods=['POST', 'GET', 'HEAD'])
def webhook():
    if request.method == 'HEAD':
        return '', 200
    if request.method == 'GET':
        return "TITAN CORE ACTIVE", 200

    if request.method == 'POST':
        update = request.get_json(silent=True)
        if update and "message" in update:
            thread = threading.Thread(target=process_message, args=(update,))
            thread.daemon = True
            thread.start()
        return "OK", 200

def process_with_progress(cid, action_text, ai_function, *args, **kwargs):
    """Универсальная функция с прогресс-баром"""
    # Отправляем статус
    status = send_msg(cid, f"{action_text}: [░░░░░░░░░░] 0%")
    if not status:
        return
    
    msg_id = status.json()['result']['message_id']
    
    # Прогресс-бар
    steps = ["██░░░░░░░░ 20%", "████░░░░░░ 40%", "██████░░░░ 60%", "████████░░ 80%", "██████████ 100%"]
    for step in steps:
        send_typing(cid)
        edit_msg(cid, msg_id, f"{action_text}: [{step}]")
        time.sleep(0.3)
    
    # Получаем результат от ИИ
    result = ai_function(*args, **kwargs)
    
    # Заменяем статус на результат
    edit_msg(cid, msg_id, result)
    return result

def process_message(update):
    try:
        msg = update["message"]
        cid = msg["chat"]["id"]
        text = msg.get("text", "")
        user_name = msg["from"].get("first_name", "User")
        
        # Регистрация пользователя
        with db_lock:
            if cid not in USERS_DB:
                USERS_DB.add(cid)
        
        # Проверка состояния рассылки
        with db_lock:
            is_broadcast = USER_STATES.get(cid) == 'broadcast'
        
        # РАССЫЛКА (админ)
        if cid == Config.ADMIN_ID and is_broadcast:
            with db_lock:
                USER_STATES.pop(cid, None)
            
            success = 0
            users_copy = list(USERS_DB)
            status = send_msg(cid, f"📢 Рассылка: 0/{len(users_copy)}")
            
            for i, uid in enumerate(users_copy):
                if copy_msg(uid, cid, msg["message_id"]):
                    success += 1
                if i % 5 == 0:  # Обновляем статус каждые 5 сообщений
                    edit_msg(cid, status.json()['result']['message_id'], f"📢 Рассылка: {i+1}/{len(users_copy)}")
                time.sleep(0.05)
            
            send_msg(cid, f"✅ Рассылка завершена!\nДоставлено: {success}/{len(users_copy)}", get_admin_keyboard())
            return
        
        # ОБРАБОТКА КОМАНД
        if text == "/start":
            welcome = f"<b>⚡ TITAN {Config.VERSION}</b>\n\nПривет, {user_name}! Я бот с искусственным интеллектом. Задавай вопросы, генерируй изображения, получай цитаты и мудрости от ИИ."
            send_msg(cid, welcome, get_main_keyboard())
        
        # ГЛАВНОЕ МЕНЮ
        elif text == "👤 Личный кабинет":
            role = "👑 АДМИН" if cid == Config.ADMIN_ID else "👤 ПОЛЬЗОВАТЕЛЬ"
            msg_count = ADMIN_STATS.get('total_messages', 0)
            profile = f"""
<b>👤 ЛИЧНЫЙ КАБИНЕТ</b>
────────────────
🔰 Имя: {user_name}
🆔 ID: <code>{cid}</code>
👑 Роль: {role}
📊 Пользователей в системе: {len(USERS_DB)}
────────────────"""
            send_msg(cid, profile)
        
        elif text == "❓ Помощь":
            help_text = """
<b>❓ ПОМОЩЬ</b>

<b>🤖 Основные команды:</b>
💬 Связаться с ИИ - просто напиши вопрос
🎨 Сгенерировать - создай изображение по тексту

<b>👑 Для админа:</b>
📢 Рассылка - массовая отправка
ИИ-функции - цитаты, мудрости, факты и многое другое

<b>⚡ Версия:</b> TITAN V26.1 OMEGA"""
            send_msg(cid, help_text)
        
        elif text == "💬 Связаться с ИИ":
            send_msg(cid, "🧠 Напиши свой вопрос, и я отвечу через нейросеть.")
            with db_lock:
                USER_STATES[cid] = 'ai_chat'
        
        elif text == "🎨 Сгенерировать":
            send_msg(cid, "🖼 Напиши, что сгенерировать. Например: <i>киберпанк город</i> или <i>кот в космосе</i>")
            with db_lock:
                USER_STATES[cid] = 'generate_image'
        
        elif text == "📢 Связь с админом":
            send_msg(cid, "📝 Напиши сообщение, и оно уйдет админу.")
            with db_lock:
                USER_STATES[cid] = 'message_admin'
        
        # АДМИНСКИЕ ФУНКЦИИ
        elif cid == Config.ADMIN_ID and text == "📢 РАССЫЛКА":
            with db_lock:
                USER_STATES[cid] = 'broadcast'
            send_msg(cid, "📥 Отправь пост для рассылки (текст, фото или перешли сообщение):", get_admin_keyboard())
        
        elif cid == Config.ADMIN_ID and text == "📊 СТАТИСТИКА":
            uptime = datetime.datetime.now() - ADMIN_STATS['start_time']
            stats = f"""
<b>📊 СТАТИСТИКА</b>
────────────────
👥 Пользователей: {len(USERS_DB)}
📨 Сообщений: {ADMIN_STATS['total_messages']}
🖼 Изображений: {ADMIN_STATS['total_images']}
⏱ Аптайм: {str(uptime).split('.')[0]}
────────────────"""
            send_msg(cid, stats)
        
        # ВСЕ ИИ-ФУНКЦИИ ДЛЯ АДМИНА
        elif cid == Config.ADMIN_ID and text == "🎯 Цитата дня (ИИ)":
            process_with_progress(cid, "🎯 Генерация цитаты", get_ai_quote)
        
        elif cid == Config.ADMIN_ID and text == "🧠 Мудрость дня (ИИ)":
            process_with_progress(cid, "🧠 Генерация мудрости", get_ai_wisdom)
        
        elif cid == Config.ADMIN_ID and text == "📰 Факт дня (ИИ)":
            process_with_progress(cid, "📰 Генерация факта", get_ai_fact)
        
        elif cid == Config.ADMIN_ID and text == "😄 Шутка (ИИ)":
            process_with_progress(cid, "😄 Генерация шутки", get_ai_joke)
        
        elif cid == Config.ADMIN_ID and text == "💡 Совет дня (ИИ)":
            process_with_progress(cid, "💡 Генерация совета", get_ai_advice)
        
        elif cid == Config.ADMIN_ID and text == "📢 Новость (ИИ)":
            process_with_progress(cid, "📢 Генерация новости", get_ai_news)
        
        elif cid == Config.ADMIN_ID and text == "📝 Стих (ИИ)":
            process_with_progress(cid, "📝 Генерация стиха", get_ai_poem)
        
        elif cid == Config.ADMIN_ID and text == "🔮 Гороскоп (ИИ)":
            process_with_progress(cid, "🔮 Генерация гороскопа", get_ai_horoscope)
        
        elif cid == Config.ADMIN_ID and text == "⚡ Мотивация (ИИ)":
            process_with_progress(cid, "⚡ Генерация мотивации", get_ai_motivation)
        
        elif cid == Config.ADMIN_ID and text == "🌤 Погода (ИИ)":
            process_with_progress(cid, "🌤 Генерация погоды", get_ai_weather)
        
        elif cid == Config.ADMIN_ID and text == "💰 Курс валют":
            send_msg(cid, get_currency())
        
        elif cid == Config.ADMIN_ID and text == "🌍 Мой IP":
            send_msg(cid, get_ip())
        
        elif cid == Config.ADMIN_ID and text == "👥 Все юзеры":
            users_list = "\n".join([f"<code>{uid}</code>" for uid in list(USERS_DB)[:50]])
            if len(USERS_DB) > 50:
                users_list += f"\n... и еще {len(USERS_DB)-50}"
            send_msg(cid, f"<b>👥 Пользователи ({len(USERS_DB)}):</b>\n{users_list}")
        
        elif cid == Config.ADMIN_ID and text == "🔙 Назад в меню":
            send_msg(cid, "Главное меню:", get_main_keyboard())
        
        # ОБРАБОТКА СОСТОЯНИЙ
        elif USER_STATES.get(cid) == 'ai_chat' and text:
            process_with_progress(cid, "🧠 Обработка запроса", ask_groq, text)
            ADMIN_STATS['total_messages'] += 1
            with db_lock:
                USER_STATES.pop(cid, None)
        
        elif USER_STATES.get(cid) == 'generate_image' and text:
            # Генерация изображения
            status = send_msg(cid, "🖼 Генерация: [░░░░░░░░░░] 0%")
            if status:
                msg_id = status.json()['result']['message_id']
                
                steps = ["██░░░░░░░░ 20%", "████░░░░░░ 40%", "██████░░░░ 60%", "████████░░ 80%", "██████████ 100%"]
                for step in steps:
                    edit_msg(cid, msg_id, f"🖼 Генерация: [{step}]")
                    time.sleep(0.3)
                
                img_url = generate_image(text)
                delete_msg(cid, msg_id)
                send_photo(cid, img_url, f"🖼 <b>Запрос:</b> {text}")
                ADMIN_STATS['total_images'] += 1
            with db_lock:
                USER_STATES.pop(cid, None)
        
        elif USER_STATES.get(cid) == 'message_admin' and text:
            send_msg(Config.ADMIN_ID, f"📨 <b>Сообщение от {user_name} (ID: {cid}):</b>\n\n{text}")
            send_msg(cid, "✅ Сообщение отправлено админу!")
            with db_lock:
                USER_STATES.pop(cid, None)
        
        # ОБЫЧНЫЙ ТЕКСТ (тоже через ИИ)
        elif text and not text.startswith("/"):
            process_with_progress(cid, "🧠 Обработка", ask_groq, text)
            ADMIN_STATS['total_messages'] += 1
    
    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            send_msg(cid, "⚠️ Произошла ошибка. Попробуй еще раз.")
        except:
            pass

# ==============================================================================
# 🚀 ЗАПУСК
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"Starting TITAN {Config.VERSION} on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, threaded=True)
