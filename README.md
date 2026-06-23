# Генератор постов для Telegram

Flask-приложение с Gemini AI, которое генерирует продающие посты для сообществ в Telegram.

## Возможности

- Вставка ссылки на товар — нейросеть анализирует страницу и пишет пост
- Настройка тона: дружелюбный, официальный, весёлый, восторженный
- Настройки длины, эмодзи и заголовка — в `voice.md`
- Кнопка «Редактировать» — ручное редактирование перед публикацией
- Публикация в Telegram одноим кнопкой
- Отложенные посты — выбор даты и времени
- Избранное — сохранение постов для повторного использования
- Повторные попытки при ошибках 503/429

## Локальный запуск

```bash
# Установи зависимости
pip install -r requirements.txt

# Создай .env и вставь ключи
GEMINI_API_KEY=AIza...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Запусти
python app.py
```

Откроется на `http://127.0.0.1:5001`

## Деплой на Render

1. Создай репозиторий на GitHub, залей код
2. В Render → New → Web Service → подключи репозиторий
3. В Settings → Environment Variables добавь:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Deploy

## Как узнать Chat ID сообщества

1. Добавь бота в сообщество как админа
2. Отправь любое сообщение в сообщество
3. Открой: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Найди `"chat":{"id": -100...}` — это твой Chat ID

## Настройки генерации (voice.md)

| Параметр | Описание | Варианты |
|----------|----------|----------|
| `ton` | Тон поста | `druzhelyubniy`, `oficialniy`, `veseliy`, `vostorzhenniy` |
| `dlina` | Длина поста | `korotkiy` (50-80 слов), `sredniy` (100-150), `dlinniy` (200-250) |
| `emoji` | Количество эмодзи | `nikakikh`, `malo`, `sredne`, `mnogo` |
| `zagolovok` | Стиль заголовка | `s_voprosom`, `s_vosklicaniem`, `prostoy`, `bez` |
| `dopolnitelno` | Доп. указания | Свободный текст |

## Ограничения Render free tier

- Сервер засыпает после 15 минут бездействия (~30-60 секунд на разбудку)
- Избранное и отложенные посты хранятся в памяти — при перезапуске теряются
- 750 часов/месяц

## Структура проекта

```
PostGenerator-Render/
├── app.py              # Flask-приложение
├── requirements.txt    # Зависимости
├── render.yaml         # Конфигурация Render
├── .python-version     # Версия Python
├── .gitignore
├── voice.md            # Настройки генерации постов
└── templates/
    └── index.html      # Фронтенд
```
