import os
import re
import logging
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from bs4 import BeautifulSoup

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)

# --- Bot Configuration
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
RENDER_URL = "https://deal-bot-4g3a.onrender.com"  # Update to your actual Render URL if different
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# --- Constants for Link Handling and Scraping
SHORTENERS = ["cutt.ly", "spoo.me", "amzn-to.co", "fkrt.cc", "bitli.in", "da.gd", "wishlink.com"]
AFFILIATE_TAGS = ["tag=", "affid=", "utm_", "ref=", "linkCode=", "ascsubtag=", "affsource=", "affExtParam1="]
SIZE_LABELS = ["S", "M", "L", "XL", "XXL"]
GENDER_KEYWORDS = ["men", "women", "kids", "unisex"]
QUANTITY_PATTERNS = [
    r"(pack of \d+)", r"(set of \d+)", r"(\d+\s?pcs)", r"(\d+\s?kg)", r"(\d+\s?ml)", r"(\d+\s?g)", r"(quantity \d+)"
]

# Initialize Flask app and Telegram bot
app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Link Handling Functions
def unshorten_link(url):
    """Resolve shortened URLs to their full product URL."""
    try:
        for shortener in SHORTENERS:
            if shortener in url:
                resp = requests.head(url, allow_redirects=True, timeout=5)
                return resp.url
        return url
    except Exception as e:
        logging.warning(f"Unshorten error: {e}")
        return url

def strip_affiliate(url):
    """Remove affiliate tags from the URL."""
    parts = url.split("?")
    if len(parts) < 2:
        return url
    base, query = parts[0], parts[1]
    clean_query = "&".join(p for p in query.split("&") if not any(tag in p for tag in AFFILIATE_TAGS))
    return f"{base}?{clean_query}" if clean_query else base

# --- Scraping Logic Functions
def extract_title(soup, fallback="No title"):
    """Extract title from <title>, og:title, or fallback."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    return fallback

def clean_title(title):
    """Remove extra words from the title to keep it short and relevant."""
    extra_words = ["buy", "best price", "online", "deal", "discount", "offer", "brand new"]
    for word in extra_words:
        title = re.sub(rf"(?i)\b{word}\b", "", title)
    return re.sub(r"\s+", " ", title).strip()

def detect_gender(title):
    """Detect gender from the title and return as a capitalized prefix."""
    title_lower = title.lower()
    for gender in GENDER_KEYWORDS:
        if gender in title_lower:
            return gender.capitalize()
    return ""

def detect_quantity(title):
    """Detect quantity from the title (e.g., 'pack of 2')."""
    title_lower = title.lower()
    for pattern in QUANTITY_PATTERNS:
        match = re.search(pattern, title_lower)
        if match:
            return match.group(0)
    return ""

def extract_price(page_text):
    """Extract price digits following ₹ or Rs."""
    match = re.search(r"(?:₹|Rs)[\s]?(?P<price>\d{2,7})", page_text)
    return match.group("price") if match else None

def extract_sizes(soup):
    """Extract available sizes from <span> tags."""
    sizes = set()
    for span in soup.find_all("span"):
        txt = span.get_text(strip=True)
        if txt in SIZE_LABELS:
            sizes.add(txt)
    return sorted(list(sizes))

def detect_pin(msg_text, page_text, url):
    """Detect 6-digit pin code for meesho.com links, fallback to 110001."""
    if "meesho.com" not in url:
        return ""
    pin_match = re.search(r"\b(\d{6})\b", msg_text)
    if not pin_match:
        pin_match = re.search(r"\b(\d{6})\b", page_text)
    pin = pin_match.group(1) if pin_match else "110001"
    return f"Pin - {pin}"

# --- Image Handling
def get_title_hint(update: Update):
    """Extract caption from forwarded messages with images."""
    if update.message and update.message.caption:
        return update.message.caption
    return None

# --- Product Info Extraction
def extract_product_info(url, title_hint=None):
    """Scrape product details from the URL."""
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
        sizes = extract_sizes(soup)

        return title, price, sizes, page_text
    except Exception as e:
        logging.error(f"Product info error: {e}")
        return None, None, [], ""

# --- Message Handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with links."""
    msg = update.message
    if not msg:
        return

    try:
        title_hint = get_title_hint(update)
        text_source = msg.text or (title_hint or "")
        urls = re.findall(r"https?://\S+", text_source)
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
            size_line = "Size - All" if len(sizes) == len(SIZE_LABELS) else f"Size - {', '.join(sizes)}"
        pin_line = detect_pin(text_source, page_text, clean_url)

        formatted = f"{gender} {quantity} {title} @{price} rs\n{clean_url}"
        if size_line:
            formatted += f"\n\n{size_line}"
        if pin_line:
            formatted += f"\n{pin_line}"
        formatted += "\n\n@reviewcheckk"

        formatted = re.sub(r"\s+", " ", formatted).strip()
        await msg.reply_text(formatted)
    except Exception as e:
        logging.error(f"Error in handle_text: {e}")
        await msg.reply_text("Sorry, something went wrong.")

# Register the message handler
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_text))

# --- Webhook Endpoint
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    """Handle incoming Telegram updates via webhook."""
    logging.info("Webhook called! Incoming update: %s", request.get_json(force=True))
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        application.process_update(update)  # Synchronous call
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return "OK", 200

# --- Health Endpoint
@app.route("/", methods=["GET"])
def health():
    """Confirm the bot is running."""
    return "Deal-bot is running.", 200

# --- Main Execution
if __name__ == "__main__":
    try:
        bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"Webhook setup failed: {e}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
