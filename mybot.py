import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode
import openai

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN"
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
DATA_FILE = "data.json"
BAD_WORDS = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox","thevidya",
    "ummbu","gommala","ommala","kotta","badu","pvrt","ummbi","thayali","aatha","otha","kuthi"
]

openai.api_key = OPENAI_API_KEY

# ================= DATA HANDLER =================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"warns": {}, "points": {}, "quiz": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= AUTO DELETE =================
async def auto_delete(msg, delay=120):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

# ================= WELCOME =================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        name = user.first_name
        username = f"@{user.username}" if user.username else "No username"
        chat_id = update.effective_chat.id
        text = (
            f"🔮 Welcome to Bun Butter Jam!\n"
            f"👤 Name: {name}\n"
            f"💬 Username: {username}\n"
            f"🆔 Group ID: {chat_id}\n\n"
            f"📜 Rules:\n"
            f"📩 Don't PM/DM others\n"
            f"🚫 Avoid bad words\n"
            f"⚠️ Follow admin instructions\n"
            "If you have any issues, contact admin."
        )
        msg = await update.message.reply_text(text)
        asyncio.create_task(auto_delete(msg))

# ================= BAD WORD FILTER =================
async def filter_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    data = load_data()
    user_id = str(update.message.from_user.id)
    chat = update.effective_chat
    if any(word in text for word in BAD_WORDS):
        # Increment warn
        warns = data["warns"].get(user_id, 0) + 1
        data["warns"][user_id] = warns
        save_data(data)
        # Delete message
        try:
            await update.message.delete()
        except:
            pass
        # Warn msg
        warn_msg = await chat.send_message(f"⚠️ {update.message.from_user.first_name} warned! ({warns}/3)")
        asyncio.create_task(auto_delete(warn_msg))
        # Auto-ban if 3 warns
        if warns >= 3:
            ban_msg = await chat.send_message(f"🚫 {update.message.from_user.first_name} banned automatically (3 warns)")
            await chat.ban_member(update.message.from_user.id)
            asyncio.create_task(auto_delete(ban_msg))
        return

# ================= WARN / REMOVE WARN =================
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
        return
    if not context.args:
        await update.message.reply_text("Usage: /warn @username")
        return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not user:
        await update.message.reply_text("Reply to a user to warn")
        return
    data = load_data()
    user_id = str(user.id)
    warns = data["warns"].get(user_id, 0) + 1
    data["warns"][user_id] = warns
    save_data(data)
    await update.message.reply_text(f"⚠️ {user.first_name} warned! ({warns}/3)")
    if warns >= 3:
        await update.effective_chat.ban_member(user.id)
        await update.message.reply_text(f"🚫 {user.first_name} banned automatically (3 warns)")

async def remove_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in [admin.user.id for admin in await update.effective_chat.get_administrators()]:
        return
    user = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not user:
        await update.message.reply_text("Reply to a user to remove warn")
        return
    data = load_data()
    user_id = str(user.id)
    if user_id in data["warns"]:
        data["warns"][user_id] = max(0, data["warns"][user_id] - 1)
        save_data(data)
        await update.message.reply_text(f"✅ 1 warn removed from {user.first_name}")
    else:
        await update.message.reply_text(f"{user.first_name} has no warns")

# ================= BAN / UNBAN =================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user
    await update.effective_chat.ban_member(user.id)
    await update.message.reply_text(f"🚫 {user.first_name} banned!")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.reply_to_message.from_user
    await update.effective_chat.unban_member(user.id)
    await update.message.reply_text(f"✅ {user.first_name} unbanned!")

# ================= AI CHAT =================
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content": msg}],
        max_tokens=200
    )
    answer = response.choices[0].message.content
    await update.message.reply_text(answer)

# ================= QUIZ =================
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Quiz started (10 min)")
    # quiz logic placeholder, questions & answers stored in data.json
    # Messages never deleted

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏆 Daily Score", callback_data="daily")],
        [InlineKeyboardButton("📅 Weekly Score", callback_data="weekly")],
        [InlineKeyboardButton("🌐 Overall Score", callback_data="overall")]
    ]
    await update.message.reply_text("🏆 Leaderboard", reply_markup=InlineKeyboardMarkup(keyboard))

async def leaderboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Showing {query.data} leaderboard")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), filter_bad_words))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("removewarn", remove_warn))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("ai", ai_chat))
    app.add_handler(CommandHandler("quiz", start_quiz))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CallbackQueryHandler(leaderboard_button))

    print("🔥 PRO MAX BOT STARTED 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()