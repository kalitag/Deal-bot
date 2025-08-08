from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = '8465346144:AAGuH15YlK0TKQv8yTI-UNUIDBviyV65Co0'
GROUP_USERNAME = '@hathipandaa'

def format_deal(message_text):
    if "meesho.com" in message_text:
        return f"Women Fit Top @ 49 rs\n{message_text}\nSize - S\nPin - 110001\n@reviewcheckk"
    elif "myntra.com" in message_text:
        return f"\nSet of 6 GOODHOMES Glass Tumblers @ 321 rs\n{message_text}\nSize - 280ml\n@reviewcheckk"
    else:
        return f"\nDeal @ price rs\n{message_text}\n@reviewcheckk"

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg and "http" in msg:
        formatted = format_deal(msg)
        await context.bot.send_message(chat_id=GROUP_USERNAME, text=formatted)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, handle_forward))
app.run_polling()
