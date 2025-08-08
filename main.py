from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import logging
import asyncio
import os
import threading
from flask import Flask

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo'
GROUP_USERNAME = '@hathipandaa'

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running"

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    logger.info(f"Received: {msg}")
    await context.bot.send_message(chat_id=GROUP_USERNAME, text=f"Echo: {msg}")

async def run_bot():
    logger.info("*** Starting Echo Bot ***")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, echo))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == '__main__':
    threading.Thread(target=lambda: asyncio.run(run_bot())).start()
    port = int(os.environ.get("PORT", 5000))
    app_web.run(host='0.0.0.0', port=port)
