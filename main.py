from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters
)
import asyncio
import os
import re
import requests
from bs4 import BeautifulSoup

# ✅ Bot token and webhook URL
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_URL = f"https://deal-bot-255c.onrender.com/{BOT_TOKEN}"

# ✅ Flask app
app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ✅ Unshorten link
def unshorten_link(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

# ✅ Scrape product info
def extract_product_info(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")

        title = soup.title.string.strip() if soup.title else "No title"
        price_match = re.search(r'(?:₹|Rs)?\s?(\d{2,6})', page.text)
        price = price_match.group(1) if price_match else "N/A"

        sizes = re.findall(r'\b(?:XS|S|M|L|XL|XXL|XXXL)\b', page.text)
        sizes = list(set(sizes))
        return title, price, sizes
    except:
        return None, None, []

# ✅ Telegram message handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        msg = update.message.text
        print("✅ Received:", msg)

        urls = re.findall(r'https?://\S+', msg)
        if not urls:
            await update.message.reply_text("⚠️ No product link detected.")
            return

        full_url = unshorten_link(urls[0])
        title, price, sizes = extract_product_info(full_url)

        if not title or not price:
            await update.message.reply_text("❌ Unable to extract product info.")
            return

        # Gender + quantity detection
        gender = ""
        quantity = ""
        if re.search(r'\bmen\b', title, re.I): gender = "Men"
        elif re.search(r'\bwomen\b', title, re.I): gender = "Women"
        elif re.search(r'\bkids\b', title, re.I): gender = "Kids"
        elif re.search(r'\bunisex\b', title, re.I): gender = "Unisex"

        if re.search(r'pack of|set of|\d+\s?pcs|\d+\s?kg|\d+\s?ml|\d+\s?g|\bquantity\b', title, re.I):
            quantity = "Qty"

        # Size line
        size_line = ""
        if sizes:
            size_line = "Size - All" if len(sizes) >= 4 else "Size - " + ", ".join(sizes)

        # Pin logic (only for meesho)
        pin_line = ""
        if "meesho.com" in full_url:
            pin_match = re.search(r'\b\d{6}\b', msg)
            pin = pin_match.group(0) if pin_match else "110001"
            pin_line = f"Pin - {pin}"

        # Final message
        formatted = f"{gender} {quantity} {title} @{price} rs\n{full_url}"
        if size_line: formatted += f"\n\n{size_line}"
        if pin_line: formatted += f"\n{pin_line}"
        formatted += "\n\n@reviewcheckk"

        await update.message.reply_text(formatted)

application.add_handler(MessageHandler(filters.TEXT, handle_text))

# ✅ Webhook route
