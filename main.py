from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
import requests
from bs4 import BeautifulSoup
import re
import logging
import asyncio
import os
import threading

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Correct bot token
   TOKEN = '8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo'
GROUP_USERNAME = '@hathipandaa'

# Flask app
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running"

# Unshorten link
def unshorten_link(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        return response.url
    except Exception as e:
        logger.error(f"Unshorten error: {e}")
        return url

# Scrape product info
def extract_product_info(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title').text.strip()
        price_tag = soup.find('span', string=re.compile(r'₹\d+'))
        price = price_tag.text.strip() if price_tag else "price"
        sizes = [tag.text.strip().upper() for tag in soup.find_all('span') if tag.text.strip().lower() in ['s', 'm', 'l', 'xl', 'xxl']]
        return title, price, sizes
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return None, None, []

# Format message
def format_deal(message_text):
    urls = re.findall(r'https?://\S+', message_text)
    if not urls:
        return None
    full_url = unshorten_link(urls[0])
    title, price, sizes = extract_product_info(full_url)
    if not title or not price:
        return None
    size_line = "Available Sizes: " + ", ".join(sizes) if sizes else "Available Sizes: Not listed"
    return f"{title} @{price} rs\n{full_url}\n\n{size_line}\n\n@reviewcheckk"

# Handle messages
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    logger.info(f"Received message from {update.effective_user.username}: {msg}")
    if msg:
        formatted = format_deal(msg)
        if formatted:
            await context.bot.send_message(chat_id=GROUP_USERNAME, text=formatted)

# Run bot
async def run_bot():
    logger.info("*** Starting Telegram bot ***")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_forward))  # ✅ Accept all text messages
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# Entry point
if __name__ == '__main__':
    threading.Thread(target=lambda: asyncio.run(run_bot())).start()
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)
