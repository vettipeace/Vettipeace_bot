import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
import openai

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QUIZ_INTERVAL = int(os.getenv("QUIZ_INTERVAL", 600))

openai.api_key = OPENAI_API_KEY

DATA_FILE = "data.json"

# ================= DATA =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"warns": {}, "leaderboard": {}, "groups": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= BAD WORDS =================
BAD_WORDS = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox","thevidya","ummbu","gommala","ommala","mairu","thayali"
]

# ================= WELCOME =================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        name = user.first_name
        username = f"@{user.username}" if user.username else "No Username"
        chat_id = update.effective_chat.id

        text = (
            f"🔮 Welcome to Bun Butter Jam!\n"
            f"👤 Name: {name}\n"
            f"💬 Username: {username}\n"
            f"🆔 Group ID: {chat_id}\n\n"
            f"📜 Click below for rules 👇"
        )

        keyboard = [[InlineKeyboardButton("📜 Rules", callback_data="rules")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= RULE BUTTON =================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "rules":
        rules = (
            "📜 *Group Rules*\n"
            "1️⃣ No 18+ content\n"
            "2️⃣ No spam\n"
            "3️⃣ Respect others\n"
            "4️⃣ No bad words\n"
            "5️⃣ Follow admins"
        )
        await query.edit_message_text(rules, parse_mode="Markdown")

# ================= BAD WORD FILTER =================
async def filter_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.lower()
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    for word in BAD_WORDS:
        if word in msg:
            await update.message.delete()

            data.setdefault("warns", {}).setdefault(chat_id, {})
            data["warns"][chat_id][user_id] = data["warns"][chat_id].get(user_id, 0) + 1
            save_data(data)

            await update.message.chat.send_message(
                f"⚠️ {update.effective_user.first_name} warned for bad words!"
            )
            return

# ================= AI CHAT =================
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": update.message.text}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except:
        await update.message.reply_text("⚠️ AI error!")

# ================= QUIZ =================
async def auto_quiz(app):
    await asyncio.sleep(10)

    while True:
        for chat_id in data.get("groups", []):
            try:
                q = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Give simple quiz question with answer"}]
                )

                question = q.choices[0].message.content

                await app.bot.send_message(chat_id=chat_id, text=f"🧠 Quiz:\n{question}")
            except:
                pass

        await asyncio.sleep(QUIZ_INTERVAL)

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    scores = data.get("leaderboard", {}).get(chat_id, {})

    if not scores:
        await update.message.reply_text("No scores yet!")
        return

    text = "🏆 Leaderboard:\n"
    for user, score in scores.items():
        text += f"{user}: {score}\n"

    await update.message.reply_text(text)

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

# Handlers
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad_words))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
app.add_handler(CommandHandler("leaderboard", leaderboard))

# Start quiz loop
app.job_queue.run_once(lambda ctx: asyncio.create_task(auto_quiz(app)), 5)

print("🤖 Bun Butter Jam Bot Running...")

app.run_polling()