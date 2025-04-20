
import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
user_timezones = {}
user_states = {}
user_reminders = {}

def get_timezone_by_city(city: str) -> str:
    try:
        response = requests.get("http://worldtimeapi.org/api/timezone")
        if response.status_code == 200:
            zones = response.json()
            for zone in zones:
                if city.lower() in zone.lower():
                    return zone
    except Exception as e:
        logging.error(f"Ошибка при получении часового пояса: {e}")
    return "Europe/Moscow"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_city"
    await update.message.reply_text(f"Привет, {update.effective_user.first_name}!
Напиши свой город, и я подстроюсь под твой часовой пояс.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_states:
        user_states[user_id] = "waiting_city"
        await update.message.reply_text("Напиши свой город:")
        return

    state = user_states[user_id]

    if state == "waiting_city":
        tz = get_timezone_by_city(text)
        user_timezones[user_id] = tz
        user_states[user_id] = "waiting_time"
        await update.message.reply_text(f"Окей, я настроил твой часовой пояс на: {tz}.
Теперь напиши время напоминания в формате 00:00")
    elif state == "waiting_time":
        try:
            tz = pytz.timezone(user_timezones[user_id])
            now = datetime.now(tz)
            remind_hour, remind_minute = map(int, text.split(":"))
            remind_time = now.replace(hour=remind_hour, minute=remind_minute, second=0, microsecond=0)
            if remind_time < now:
                remind_time += timedelta(days=1)
            user_reminders[user_id] = remind_time
            user_states[user_id] = "waiting_message"
            await update.message.reply_text("Напиши фразу которую нужно прислать:")
        except:
            await update.message.reply_text("Время должно быть в формате 00:00. Попробуй ещё раз.")
    elif state == "waiting_message":
        remind_time = user_reminders.get(user_id)
        if remind_time:
            context.job_queue.run_once(callback=reminder, when=(remind_time - datetime.now(pytz.timezone(user_timezones[user_id]))).total_seconds(), chat_id=update.effective_chat.id, name=str(user_id), data=text)
            await update.message.reply_text(f"Напоминание установлено на {remind_time.strftime('%H:%M')} ({user_timezones[user_id]})")
            user_states.pop(user_id, None)
            user_reminders.pop(user_id, None)
        else:
            await update.message.reply_text("Произошла ошибка. Попробуй начать сначала, введя /start")

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=context.job.chat_id, text=context.job.data)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен")
    app.run_polling()
