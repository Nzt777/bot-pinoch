import os
import logging
from datetime import datetime, timedelta
import pytz
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

user_states = {}
user_timezones = {}
user_reminders = {}
user_payments = {}

AD_TEXT = "\n\n📣 *Реклама*: Подпишись за 100₽/мес и получай напоминания на любые дни без рекламы. Напиши /subscribe"
AD_IMAGE_URL = None

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

def user_has_subscription(user_id: int) -> bool:
    expiry = user_payments.get(user_id)
    return expiry and expiry > datetime.utcnow()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_city"
    welcome = f"Привет, {update.effective_user.first_name}!\nНапиши свой город, и я подстроюсь под твой часовой пояс."
    if not user_has_subscription(user_id):
        welcome += AD_TEXT
    await update.message.reply_text(welcome)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💎 *Подписка*: 100₽ в месяц\n"
        "• Напоминания на любые дни\n"
        "• Без рекламы\n\n"
        "🔐 Оплата временно вручную. Переведите 100₽ через СБП (Сбербанк/Тинькофф) на номер +7-999-123-45-67 и пришлите чек в поддержку.\n"
        "После этого напишите команду:\n"
        "`/activate {your_user_id}` (для теста)."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 123456789:
        await update.message.reply_text("⛔ Только админ может активировать подписку.")
        return
    try:
        target_id = int(context.args[0])
        user_payments[target_id] = datetime.utcnow() + timedelta(days=30)
        await update.message.reply_text(f"✅ Подписка для {target_id} активирована на 30 дней.")
    except:
        await update.message.reply_text("Неверная команда. Используй: /activate user_id")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_states:
        user_states[user_id] = "waiting_city"
        reply = "Напиши свой город:"
        if not user_has_subscription(user_id):
            reply += AD_TEXT
        await update.message.reply_text(reply)
        return

    state = user_states[user_id]

    if state == "waiting_city":
        tz = get_timezone_by_city(text)
        user_timezones[user_id] = tz
        user_states[user_id] = "waiting_time"
        reply = f"Окей, я настроил твой часовой пояс на: {tz}.\nТеперь напиши время напоминания в формате 00:00"
        if not user_has_subscription(user_id):
            reply += AD_TEXT
        await update.message.reply_text(reply)

    elif state == "waiting_time":
        try:
            tz = pytz.timezone(user_timezones[user_id])
            now = datetime.now(tz)
            remind_hour, remind_minute = map(int, text.split(":"))
            remind_time = now.replace(hour=remind_hour, minute=remind_minute, second=0, microsecond=0)
            if remind_time < now:
                remind_time += timedelta(days=1)
            if not user_has_subscription(user_id) and remind_time.date() > now.date():
                await update.message.reply_text("⛔ В бесплатной версии можно ставить напоминания только на сегодня.\nНапиши /subscribe, чтобы получить доступ к напоминаниям на любой день.")
                return
            user_reminders[user_id] = remind_time
            user_states[user_id] = "waiting_message"
            reply = "Напиши фразу которую нужно прислать:"
            if not user_has_subscription(user_id):
                reply += AD_TEXT
            await update.message.reply_text(reply)
        except:
            await update.message.reply_text("⛔ Время должно быть в формате 00:00. Попробуй ещё раз.")

    elif state == "waiting_message":
        remind_time = user_reminders.get(user_id)
        if remind_time:
            context.job_queue.run_once(callback=reminder, when=(remind_time - datetime.now(pytz.timezone(user_timezones[user_id]))).total_seconds(), chat_id=update.effective_chat.id, name=str(user_id), data=text)
            reply = f"✅ Напоминание установлено на {remind_time.strftime('%H:%M')} ({user_timezones[user_id]})"
            if not user_has_subscription(user_id):
                reply += AD_TEXT
            await update.message.reply_text(reply)
            user_states.pop(user_id, None)
            user_reminders.pop(user_id, None)

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    text = context.job.data
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id=chat_id, text=f"⏰ Напоминание:\n{text}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("activate", activate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен")
    app.run_polling()