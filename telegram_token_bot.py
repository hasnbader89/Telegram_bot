
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# --- Settings ---

TELEGRAM_TOKEN = "8045271874:AAGaTThRco-5ZnNIEmvEsLpf79hOzieVGZc"

PUMPFUN_API = "https://api.pump.fun/v1/tokens"
RUGCHECK_API = "https://api.rugcheck.xyz/api/check/"
GMGN_API = "https://api.gmgn.xyz/token/"

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- API Functions ---

def get_new_tokens():
    try:
        response = requests.get(PUMPFUN_API)
        data = response.json()
        return data.get("tokens", [])
    except Exception as e:
        logging.error(f"Error fetching PumpFun tokens: {e}")
        return []

def check_rug(token_address):
    try:
        url = RUGCHECK_API + token_address
        response = requests.get(url)
        result = response.json()
        return result.get("status") == "GOOD"
    except Exception as e:
        logging.error(f"Error checking rug: {e}")
        return False

def analyze_token(token_address):
    try:
        url = GMGN_API + token_address
        response = requests.get(url)
        data = response.json()
        analysis = {
            "liquidity": data.get("liquidity"),
            "owners": data.get("holders"),
            "market_cap": data.get("market_cap"),
            "age": data.get("age"),
            "trend": data.get("trend"),
            "price": data.get("price"),
        }
        return analysis
    except Exception as e:
        logging.error(f"Error analyzing token: {e}")
        return {}

# --- Telegram Communication ---

async def send_token_report(update: Update, context: ContextTypes.DEFAULT_TYPE, token):
    address = token.get("address")
    name = token.get("name")
    image_url = token.get("image", None)

    if not check_rug(address):
        logging.info(f"Token {name} failed Rugcheck.")
        return

    analysis = analyze_token(address)
    if not analysis:
        logging.info(f"Token {name} analysis failed.")
        return

    message = f"""
🚀 New Token: *{name}*
🆔 Address: `{address}`

✅ RugCheck: GOOD
📊 Liquidity: {analysis.get('liquidity', 'N/A')}$
👥 Holders: {analysis.get('owners', 'Unknown')}
📈 Market Cap: {analysis.get('market_cap', 'N/A')}$
💰 Price: {analysis.get('price', 'N/A')} SOL
⏳ Contract Age: {analysis.get('age', 'Unknown')}
📉 Trend: {analysis.get('trend', 'Unknown')}

🔗 [Token Link](https://pump.fun/token/{address})
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy", callback_data=f"buy_{address}"),
         InlineKeyboardButton("❌ Ignore", callback_data=f"ignore_{address}")]
    ])

    if image_url:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_url,
            caption=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

# --- Monitor New Tokens ---

async def monitor_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent_tokens = set()
    while True:
        tokens = get_new_tokens()
        for token in tokens:
            address = token.get("address")
            if address not in sent_tokens:
                await send_token_report(update, context, token)
                sent_tokens.add(address)
        await asyncio.sleep(30)

# --- Telegram Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 Bot started. You'll receive token alerts.")
    context.application.create_task(monitor_tokens(update, context))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    token_id = query.data.split("_", 1)[1]
    await query.edit_message_reply_markup(reply_markup=None)
    if query.data.startswith("buy_"):
        await query.message.reply_text(f"✅ Buy token:
`{token_id}`", parse_mode=ParseMode.MARKDOWN)
    elif query.data.startswith("ignore_"):
        await query.message.reply_text(f"🚫 Ignored token:
`{token_id}`", parse_mode=ParseMode.MARKDOWN)

# --- Main Entry ---

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
