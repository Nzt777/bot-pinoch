# Бот-Пинок (Telegram Motivator Bot)

## Описание
Telegram-бот, который напоминает тебе о задачах в одном из трёх стилей: токсичный, добрый или мемный. Он пинает тебя ежедневно в указанное время.

## Установка и запуск

1. Установи зависимости:
```
pip install -r requirements.txt
```

2. Добавь переменную окружения:
```
TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather
```

3. Запусти бота:
```
python main.py
```

## Деплой на Render.com

1. Создай репозиторий на GitHub и загрузи файлы.
2. Зарегистрируйся на https://render.com
3. Создай новый Web Service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - В переменных окружения добавь `TELEGRAM_BOT_TOKEN`
   - Выбери Python 3.10+

Бот готов к работе!
