import os
import re
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Bot Configuration
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
RENDER_URL = "https://deal-bot-4g3a.onrender.com"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# Initialize Flask and Telegram bot
app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Message Handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    try:
        text_source = msg.text or msg.caption or "No text"
        response = f"Received: {text_source}\n\nMen Pack of 2 T-shirt @599 rs\nhttps://example.com\n\nSize - S, M\nPin - 110001\n\n@reviewcheckk"
        await msg.reply_text(response)
    except Exception as e:
        logging.error(f"Handler error for {update.update_id}: {e}")
        await msg.reply_text("Error, but responding: Men Pack of 2 T-shirt @599 rs\nhttps://example.com\n\n@reviewcheckk")

# --- Handlers
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_text))

# --- Webhook Endpoint
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    logging.info("Webhook update received")
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        application.process_update(update)
        return "OK", 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "Error", 500

# --- Health Endpoint
@app.route("/", methods=["GET"])
def health():
    return "Deal-bot is running.", 200

# --- Main Execution
if __name__ == "__main__":
    try:
        bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook setup failed: {e}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
