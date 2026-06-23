"""
Генератор постов для товара — Flask-приложение с Gemini AI.

Деплой на Render:
    - Ключи задаются в Environment Variables дашборда Render
    - Файлы favorites.json и scheduled.json хранятся в памяти (при перезапуске теряются)
    - Порт берётся из переменной $PORT

Запуск локально:
    python app.py
"""

import os
import json
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv
from google import genai
import requests
from flask import Flask, render_template, request, jsonify

load_dotenv()

app = Flask(__name__)

# ─────────────────────────────────────────────
# Хранение в памяти (для Render)
# ─────────────────────────────────────────────
favorites_db = {}   # {id: {id, text, link, created_at}}
scheduled_db = {}   # {id: {id, text, publish_at, created_at}}


# ─────────────────────────────────────────────
# Проверка отложенных постов (при каждом запросе)
# ─────────────────────────────────────────────
@app.before_request
def check_scheduled_posts():
    """Проверяет отложенные посты и публикует те, время которых наступило."""
    now = datetime.now()
    to_delete = []
    for post_id, item in scheduled_db.items():
        try:
            publish_at = datetime.fromisoformat(item["publish_at"])
            if now >= publish_at:
                send_to_telegram(item["text"])
                to_delete.append(post_id)
        except (ValueError, KeyError):
            to_delete.append(post_id)
    for post_id in to_delete:
        scheduled_db.pop(post_id, None)


# ─────────────────────────────────────────────
# Настройка Gemini API
# ─────────────────────────────────────────────
def get_gemini_client():
    """Создаёт клиент Gemini по API-ключу."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


# ─────────────────────────────────────────────
# Telegram API
# ─────────────────────────────────────────────
def send_to_telegram(text: str) -> dict:
    """Отправляет текст в Telegram-сообщество."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN не задан в Environment Variables"}
    if not chat_id:
        return {"ok": False, "error": "TELEGRAM_CHAT_ID не задан в Environment Variables"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return {"ok": True}
        else:
            return {"ok": False, "error": data.get("description", "Неизвестная ошибка")}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────
# Чтение настроек из voice.md
# ─────────────────────────────────────────────
def load_voice_settings() -> dict:
    """Читает voice.md и возвращает словарь с настройками."""
    settings = {}
    try:
        with open("voice.md", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    key, value = line.split(":", 1)
                    settings[key.strip()] = value.strip()
    except FileNotFoundError:
        settings = {"ton": "druzhelyubniy", "dlina": "sredniy", "emoji": "sredne", "zagolovok": "s_voprosom", "dopolnitelno": ""}
    return settings


# ─────────────────────────────────────────────
# Словари для перевода настроек
# ─────────────────────────────────────────────
TON_NAMES = {
    "druzhelyubniy": "дружелюбный, тёплый, разговорный",
    "oficialniy": "официальный, деловой, строгий",
    "veseliy": "весёлый, игривый, с юмором",
    "vostorzhenniy": "восторженный, энергичный, эмоциональный",
}

DLINA_NAMES = {
    "korotkiy": "короткий, 50-80 слов",
    "sredniy": "средний, 100-150 слов",
    "dlinniy": "длинный, 200-250 слов",
}

EMOJI_NAMES = {
    "nikakikh": "без эмодзи вообще",
    "malo": "3-5 эмодзи на весь пост",
    "sredne": "6-10 эмодзи на весь пост",
    "mnogo": "11-15 эмодзи на весь пост",
}

ZAGOLOVOK_NAMES = {
    "s_voprosom": "заголовок-вопрос",
    "s_vosklicaniem": "восклицательный заголовок",
    "prostoy": "простое описание",
    "bez": "без заголовка",
}


# ─────────────────────────────────────────────
# Генерация промпта для Gemini
# ─────────────────────────────────────────────
def build_prompt(name, description, price, link, mood) -> str:
    """Собирает промпт для нейросети."""
    settings = load_voice_settings()
    ton = mood if mood else settings.get("ton", "druzhelyubniy")

    prompt = f"""Ты — опытный копирайтер. Напиши продающий пост для соцсетей о товаре.

ССЫЛКА НА ТОВАР (основной источник информации): {link}

ОБЯЗАТЕЛЬНО добавь ссылку {link} в самом конце поста. Просто вставь ссылку на новой строке в конце текста, без слов «ссылка на товар» и без квадратных скобок."""

    if name and name != "Товар":
        prompt += f"\n- Уточнённое название: {name}"
    if description:
        prompt += f"\n- Доп. описание от пользователя: {description}"
    if price:
        prompt += f"\n- Цена / выгода: {price}"

    prompt += f"""

ТРЕБОВАНИЯ К ПОСТУ:
- Тон: {TON_NAMES.get(ton, TON_NAMES['druzhelyubniy'])}
- Длина: {DLINA_NAMES.get(settings.get('dlina', 'sredniy'), DLINA_NAMES['sredniy'])}
- Эмодзи: {EMOJI_NAMES.get(settings.get('emoji', 'sredne'), EMOJI_NAMES['sredne'])}
- Заголовок: {ZAGOLOVOK_NAMES.get(settings.get('zagolovok', 's_voprosom'), ZAGOLOVOK_NAMES['s_voprosom'])}"""

    dopolnitelno = settings.get("dopolnitelno", "")
    if dopolnitelno:
        prompt += f"\n- Дополнительно: {dopolnitelno}"

    prompt += """

ВАЖНЫЕ ПРАВИЛА:
- Пост должен быть оригинальным и интересным
- Не используй шаблонные фразы вроде «представляем вашему вниманию»
- Пиши так, чтобы человек захотел купить товар
- Используй эмоции, образы, метафоры
- Сделай текст живым и цепляющим
- Не пиши «рекламный текст» — пиши как реальный человек делятся находкой
- Не используй markdown-разметку, только текст
- Не кавычки в начале и конце поста"""

    return prompt


# ─────────────────────────────────────────────
# Генерация поста через Gemini
# ─────────────────────────────────────────────
def generate_post_with_gemini(name, description, price, link, mood) -> str:
    """Генерирует пост через Gemini API с повторными попытками."""
    client = get_gemini_client()
    if client is None:
        return "⚠️ API-ключ Gemini не настроен! Добавь GEMINI_API_KEY в Environment Variables."

    prompt = build_prompt(name, description, price, link, mood)

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(model="gemini-flash-lite-latest", contents=prompt)
            post = response.text
            post = post.replace("[ссылка на товар]", link)
            post = post.replace("[ссылка]", link)
            post = post.replace("[Ссылка на товар]", link)
            post = post.replace("[Ссылка]", link)
            post = post.replace(f"[{link}]", link)
            return post
        except Exception as e:
            error_str = str(e)
            is_retryable = any(x in error_str for x in ["503", "429", "RESOURCE_EXHAUSTED", "UNAVAILABLE"])
            if is_retryable and attempt < 3:
                time.sleep(attempt * 5)
                continue
            return f"⚠️ Ошибка при обращении к Gemini: {e}"

    return "⚠️ Не удалось сгенерировать пост после 3 попыток."


# ─────────────────────────────────────────────
# Маршруты Flask
# ─────────────────────────────────────────────

@app.route("/")
def index():
    favorites = list(favorites_db.values())
    favorites.reverse()
    return render_template("index.html", favorites=favorites)


@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    link = request.form.get("link", "").strip()
    mood = request.form.get("mood", "").strip()

    if not link:
        return jsonify({"error": "Вставьте ссылку на товар!"}), 400
    if not name:
        name = "Товар"

    post = generate_post_with_gemini(name, description, price, link, mood)
    return jsonify({"post": post})


@app.route("/publish", methods=["POST"])
def publish():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Нет текста для публикации"}), 400

    result = send_to_telegram(text)
    if result["ok"]:
        return jsonify({"ok": True, "message": "Пост опубликован в Telegram!"})
    else:
        return jsonify({"ok": False, "error": result["error"]}), 500


@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.get_json()
    text = data.get("text", "").strip()
    publish_at = data.get("publish_at", "")

    if not text:
        return jsonify({"error": "Нет текста для публикации"}), 400
    if not publish_at:
        return jsonify({"error": "Укажите дату и время публикации"}), 400

    try:
        publish_dt = datetime.fromisoformat(publish_at)
        if publish_dt <= datetime.now():
            return jsonify({"error": "Время публикации должно быть в будущем"}), 400
    except ValueError:
        return jsonify({"error": "Неверный формат даты/времени"}), 400

    post_id = str(uuid.uuid4())
    scheduled_db[post_id] = {
        "id": post_id,
        "text": text,
        "publish_at": publish_at,
        "created_at": datetime.now().isoformat(),
    }

    return jsonify({"ok": True, "message": f"Пост запланирован на {publish_dt.strftime('%d.%m.%Y %H:%M')}"})


@app.route("/favorites/add", methods=["POST"])
def favorites_add():
    data = request.get_json()
    text = data.get("text", "").strip()
    link = data.get("link", "")

    if not text:
        return jsonify({"error": "Нет текста"}), 400

    # Проверяем дубликаты
    for item in favorites_db.values():
        if item["text"] == text:
            return jsonify({"ok": True, "message": "Уже в избранном"})

    post_id = str(uuid.uuid4())
    favorites_db[post_id] = {
        "id": post_id,
        "text": text,
        "link": link,
        "created_at": datetime.now().isoformat(),
    }
    return jsonify({"ok": True, "message": "Добавлено в избранное"})


@app.route("/favorites/remove", methods=["POST"])
def favorites_remove():
    data = request.get_json()
    post_id = data.get("id", "")
    if not post_id:
        return jsonify({"error": "Нет id поста"}), 400

    favorites_db.pop(post_id, None)
    return jsonify({"ok": True, "message": "Удалено из избранного"})


@app.route("/favorites")
def favorites_list():
    return jsonify(list(favorites_db.values()))


# ─────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
