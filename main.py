import os
import re
import requests
from flask import Flask, request
from telegram import Update, Bot, Message
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters
)
from bs4 import BeautifulSoup
import asyncio

# === Configuration ===
BOT_TOKEN = "8465346144:AAGSHC77UkXVZZTUscbYItvJxgQbBxmFcWo"
WEBHOOK_URL = f"https://deal-bot-255c.onrender.com/{BOT_TOKEN}"
SHORTENERS = [
    "cutt.ly", "spoo.me", "amzn-to.co", "fkrt.cc", "bitli.in", "da.gd", "wishlink.com"
]
AFFILIATE_TAGS = [
    "tag=", "affid=", "utm_", "ref=", "linkCode=", "ascsubtag=", "affsource=", "affExtParam1="
]
SIZE_LABELS = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

app = Flask(__name__)
bot = Bot(BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

def unshorten_link(url):
    """Unshorten supported links."""
    try:
        for s in SHORTENERS:
            if s in url:
                resp = requests.head(url, allow_redirects=True, timeout=5)
                return resp.url
        return url
    except Exception:
        return url

def strip_affiliate(url):
    """Remove common affiliate tags from URLs."""
    parts = url.split("?")
    if len(parts) < 2:
        return url
    base, query = parts[0], parts[1]
    clean_query = "&".join(
        p for p in query.split("&") if not any(tag in p for tag in AFFILIATE_TAGS)
    )
    return f"{base}?{clean_query}" if clean_query else base

def extract_title(soup, fallback="No title"):
    # Try <title>
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Try og:title
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    return fallback

def clean_title(title):
    # Remove extra words, keep short and relevant
    title = re.sub(r"(?i)\b(buy|best price|online|deal|discount|offer|brand new)\b", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()

def extract_price(page_text):
    match = re.search(r"(?:₹|Rs)[\s]?(?P<price>\d{2,7})", page_text)
    return match.group("price") if match else None

def extract_sizes(soup, page_text):
    sizes = set()
    # From <span>
    for span in soup.find_all("span"):
        txt = span.get_text(strip=True)
        if txt in SIZE_LABELS:
            sizes.add(txt)
    # Fallback: regex in text
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
    # Only for meesho.com
    if "meesho.com" not in url:
        return ""
    pin_match = re.search(r"\b(\d{6})\b", msg_text)
    if not pin_match:
        pin_match = re.search(r"\b(\d{6})\b", page_text)
    pin = pin_match.group(1) if pin_match else "110001"
    return f"Pin - {pin}"

def get_caption_or_alt(update: Update):
    """Try to extract image caption or alt text if available."""
    msg: Message = update.message
    if msg and msg.caption:
        return msg.caption
    # Fallback: no caption
    return None

def extract_product_info(url, title_hint=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        page_text = page.text

        # Title
        title = extract_title(soup)
        if not title or title == "No title":
            title = title_hint if title_hint else "No title"
        title = clean_title(title)

        # Price
        price = extract_price(page_text)

        # Sizes
        sizes = extract_sizes(soup, page_text)

        return title, price, sizes, page_text
    except Exception:
        return None, None, [], ""

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # Forwarded image/caption handling
    title_hint = get_caption_or_alt(update)

    # Link detection
    urls = re.findall(r'https?://\S+', msg.text or (title_hint or ""))
    if not urls:
        await msg.reply_text("⚠️ No product link detected.")
        return

    raw_url = urls[0]
    unshort = unshorten_link(raw_url)
    clean_url = strip_affiliate(unshort)

    title, price, sizes, page_text = extract_product_info(clean_url, title_hint=title_hint)

    if not title or not price:
        # Try to extract from image if possible
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

    # Output format
    formatted = f"{gender} {quantity} {title} @{price} rs\n{clean_url}"
    if size_line:
        formatted += f"\n\n{size_line}"
    if pin_line:
        formatted += f"\n{pin_line}"
    formatted += "\n\n@reviewcheckk"

    # Final clean-up
    formatted = re.sub(r"\s+", " ", formatted)  # Remove double spaces
    formatted = formatted.replace("₹", "").replace("Rs", "")  # Remove ₹ or Rs if any
    formatted = formatted.replace(" @ rs", "")  # Edge case
    await msg.reply_text(formatted)

application.add_handler(MessageHandler(filters.TEXT, handle_text))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "Deal-bot is running.", 200

if __name__ == "__main__":
    # Set webhook on start (idempotent)
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) flask import Flask, request
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
