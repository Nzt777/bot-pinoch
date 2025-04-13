
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from apscheduler.schedulers.background import BackgroundScheduler
import json, datetime

# Простая "база данных" в файле
USER_DATA_FILE = 'user_data.json'

STYLES = {
    "токсичный": [
        "Ты опять прокрастинируешь? Соберись, тряпка!",
        "Будешь ждать идеального момента — дождёшься пенсии.",
        "Ты либо делаешь дело, либо листаешь мемы. Выбирай."
    ],
    "добрый": [
        "Ты можешь больше, чем сам думаешь. Вперёд!",
        "Я рядом. Давай сегодня победим лень вместе.",
        "Ты не один. Я верю в тебя — начни с малого."
    ],
    "мемный": [
        "Сделай это. Иначе я станцую в твоём шкафу.",
        "Где результат? Бобры в лесу продуктивнее!",
        "Сегодня день, когда ты либо герой, либо носок. Кто ты?"
    ]
}

users = {}

try:
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
except:
    pass

CHOOSE_STYLE, ASK_TASK, ASK_TIME = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["токсичный", "добрый", "мемный"]]
    await update.message.reply_text(
        "Привет! Я Бот-пинок. Выбери стиль мотивации:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return CHOOSE_STYLE

async def set_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    users[chat_id] = {"style": update.message.text}
    await update.message.reply_text("Отлично! Теперь скажи, о чём тебе напоминать?")
    return ASK_TASK

async def set_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    users[chat_id]["task"] = update.message.text
    await update.message.reply_text("Во сколько тебе напоминать каждый день? (в формате ЧЧ:ММ, например 09:00)")
    return ASK_TIME

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    time = update.message.text
    try:
        hour, minute = map(int, time.split(":"))
        users[chat_id]["time"] = time
        save_users()
        schedule_reminder(chat_id, hour, minute)
        await update.message.reply_text("Готово! Жди пинка в " + time)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Неверный формат времени. Попробуй снова, например 09:00")
        return ASK_TIME

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    user = users.get(str(chat_id))
    if user:
        style = user.get("style")
        task = user.get("task")
        message = f"{task}: {random_phrase(style)}"
        await context.bot.send_message(chat_id=chat_id, text=message)

def schedule_reminder(chat_id, hour, minute):
    scheduler.add_job(
        send_reminder,
        'cron',
        hour=hour,
        minute=minute,
        args=[],
        kwargs={"context": type('Context', (object,), {"job": type('Job', (object,), {"chat_id": int(chat_id)})()})()}
    )

def save_users():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f)

def random_phrase(style):
    import random
    return random.choice(STYLES.get(style, ["Сделай это!"]))

if __name__ == '__main__':
    import os
    import asyncio

    scheduler = BackgroundScheduler()
    scheduler.start()

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Задай токен как переменную среды
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_style)],
            ASK_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_task)],
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_time)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    print("Бот запущен")
    asyncio.run(app.run_polling())
