from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters
)
import asyncio
import os

# ✅ Bot token and webhook URL
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_URL = f"https://deal-bot-255c.onrender.com/{BOT_TOKEN}"

# ✅ Flask app
app = Flask(__name__)
bot = Bot(BOT_TOKEN)

# ✅ Telegram handler with forward check
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        print("✅ Received:", update.message.text)
        if update.message.forward_date:
            # 🔧 Placeholder for scraping logic
            await update.message.reply_text("Forwarded product detected! 🔍")
        else:
            await update.message.reply_text("⚠️ Please forward a product link.")

# ✅ Telegram app setup
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT, handle_text))

# ✅ Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
    return "ok"

# ✅ Health check route
@app.route("/")
def index():
    return "Bot is running with webhook!"

# ✅ Set webhook once
async def set_webhook():
    await bot.set_webhook(WEBHOOK_URL)
    print("🚀 Webhook set!")

# ✅ Start everything
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host="0.0.0.0", port=port)
