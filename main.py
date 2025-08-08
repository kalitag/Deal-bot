import os
import re
import logging
import requests
from flask import Flask, request
from telegram import Update, Bot, Message
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters
)
from bs4 import BeautifulSoup

# --- Logging setup
logging.basicConfig(level=logging.INFO)

# --- Bot configuration: Update RENDER_URL to your actual Render service!
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
RENDER_URL = "https://deal-bot-4g3a.onrender.com"  # <--- Confirm this matches your Render dashboard!
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Helper functions (customize as needed)
SHORTENERS = [
    "cutt.ly", "spoo.me", "amzn-to.co", "fkrt.cc", "bitli.in", "da.gd", "wishlink.com"
]
AFFILIATE_TAGS = [
    "tag=", "affid=", "utm_", "ref=", "linkCode=", "ascsubtag=", "affsource=", "affExtParam1="
]
SIZE_LABELS = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

def unshorten_link(url):
    try:
        for s in SHORTENERS:
            if s in url:
                resp = requests.head(url, allow_redirects=True, timeout=5)
                return resp.url
        return url
    except Exception as e:
        logging.warning(f"Unshorten error: {e}")
        return url

def strip_affiliate(url):
    parts = url.split("?")
    if len(parts) < 2:
        return url
    base, query = parts[0], parts[1]
    clean_query = "&".join(
        p for p in query.split("&") if not any(tag in p for tag in AFFILIATE_TAGS)
    )
    return f"{base}?{clean_query}" if clean_query else base

def extract_title(soup, fallback="No title"):
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    return fallback

def clean_title(title):
    title = re.sub(r"(?i)\b(buy|best price|online|deal|discount|offer|brand new)\b", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()

def extract_price(page_text):
    match = re.search(r"(?:₹|Rs)[\s]?(?P<price>\d{2,7})", page_text)
    return match.group("price") if match else None

def extract_sizes(soup, page_text):
    sizes = set()
    for span in soup.find_all("span"):
        txt = span.get_text(strip=True)
        if txt in SIZE_LABELS:
            sizes.add(txt)
    for label in SIZE_LABELS:
        if re.search(fr"\b{label}\b", page_text):
            sizes.add(label)
    return sorted(list(sizes))

def detect_gender(title):
    title_lower = title.lower()
    if "men" in title_lower:
        return "Men"
    if "women" in title_lower:
        return "Women"
    if "kids" in title_lower:
        return "Kids"
    if "unisex" in title_lower:
        return "Unisex"
    return ""

def detect_quantity(title):
    pattern = r"(pack of|set of|\d+\s?pcs|\d+\s?kg|\d+\s?ml|\d+\s?g|\bquantity\b)"
    return "Qty" if re.search(pattern, title, re.I) else ""

def detect_pin(msg_text, page_text, url):
    if "meesho.com" not in url:
        return ""
    pin_match = re.search(r"\b(\d{6})\b", msg_text)
    if not pin_match:
        pin_match = re.search(r"\b(\d{6})\b", page_text)
    pin = pin_match.group(1) if pin_match else "110001"
    return f"Pin - {pin}"

def get_caption_or_alt(update: Update):
    msg: Message = update.message
    if msg and msg.caption:
        return msg.caption
    return None

def extract_product_info(url, title_hint=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        page_text = page.text

        title = extract_title(soup)
        if not title or title == "No title":
            title = title_hint if title_hint else "No title"
        title = clean_title(title)

        price = extract_price(page_text)
        sizes = extract_sizes(soup, page_text)

        return title, price, sizes, page_text
    except Exception as e:
        logging.error(f"Product info error: {e}")
        return None, None, [], ""

# --- Telegram handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    try:
        title_hint = get_caption_or_alt(update)
        urls = re.findall(r'https?://\S+', msg.text or (title_hint or ""))
        if not urls:
            await msg.reply_text("⚠️ No product link detected.")
            return

        raw_url = urls[0]
        unshort = unshorten_link(raw_url)
        clean_url = strip_affiliate(unshort)

        title, price, sizes, page_text = extract_product_info(clean_url, title_hint=title_hint)

        if not title or not price:
            if title_hint:
                await msg.reply_text(f"🖼️ {title_hint}\n❌ Unable to extract product info.")
            else:
                await msg.reply_text("❌ Unable to extract product info.")
            return

        gender = detect_gender(title)
        quantity = detect_quantity(title)
        size_line = ""
        if sizes:
            size_line = "Size - All" if len(sizes) >= 4 else "Size - " + ", ".join(sizes)
        pin_line = detect_pin(msg.text, page_text, clean_url)

        formatted = f"{gender} {quantity} {title} @{price} rs\n{clean_url}"
        if size_line:
            formatted += f"\n\n{size_line}"
        if pin_line:
            formatted += f"\n{pin_line}"
        formatted += "\n\n@reviewcheckk"

        formatted = re.sub(r"\s+", " ", formatted)
        formatted = formatted.replace("₹", "").replace("Rs", "")
        formatted = formatted.replace(" @ rs", "")
        await msg.reply_text(formatted)
    except Exception as e:
        logging.error(f"Error in handle_text: {e}")
        await msg.reply_text("Sorry, something went wrong.")

application.add_handler(MessageHandler(filters.TEXT, handle_text))

# --- Webhook endpoint
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    logging.info("Webhook called! Incoming update: %s", request.get_json(force=True))
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        application.process_update(update)  # Synchronous call
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return "OK", 200

# --- Health endpoint
@app.route("/", methods=["GET"])
def health():
    return "Deal-bot is running.", 200

if __name__ == "__main__":
    try:
        bot.set_webhook(WEBHOOK_URL)  # Synchronous call
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook setup failed: {e}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
