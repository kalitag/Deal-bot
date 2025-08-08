from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask
import requests
from bs4 import BeautifulSoup
import re

TOKEN = '8465346144:AAGuH15YlK0TKQv8yTI-UNUIDBviyV65Co0'
GROUP_USERNAME = '@hathipandaa'

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running"

def unshorten_link(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        return response.url
    except:
        return url

def extract_product_info(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.find('title').text.strip()

        price_tag = soup.find('span', string=re.compile(r'₹\d+'))
        price = price_tag.text.strip() if price_tag else "price"

        sizes = []
        for tag in soup.find_all('span'):
            if tag.text.strip().lower() in ['s', 'm', 'l', 'xl', 'xxl']:
                sizes.append(tag.text.strip().upper())

        return title, price, sizes
    except:
        return None, None, []

def format_deal(message_text):
    urls = re.findall(r'https?://\S+', message_text)
    if not urls:
        return None

    original_url = urls[0]
    full_url = unshorten_link(original_url)
    title, price, sizes = extract_product_info(full_url)

    if not title or not price:
        return None

    size_line = "Available Sizes: " + ", ".join(sizes) if sizes else "Available Sizes: Not listed"

    return f"{title} @{price} rs\n{full_url}\n\n{size_line}\n\n@reviewcheckk"

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg:
        formatted = format_deal(msg)
        if formatted:
            await context.bot.send_message(chat_id=GROUP_USERNAME, text=formatted)

def run_bot():
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, handle_forward))
    bot_app.run_polling()

if __name__ == '__main__':
    import threading
    threading.Thread(target=run_bot).start()
    app_web.run(host='0.0.0.0', port=10000)
