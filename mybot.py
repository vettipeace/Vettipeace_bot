import os, json, random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
import openai

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QUIZ_INTERVAL = int(os.getenv("QUIZ_INTERVAL", 600))

openai.api_key = OPENAI_API_KEY

DATA_FILE = "data.json"

# ================= LOAD DATA =================
def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"warns": {}, "points": {}}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load()

# ================= WELCOME =================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        name = user.first_name
        username = f"@{user.username}" if user.username else "No username"
        chat_id = update.effective_chat.id

        text = (
            f"🔮 Welcome to Bun Butter Jam!\n\n"
            f"👤 Name: {name}\n"
            f"💬 Username: {username}\n"
            f"🆔 Group ID: {chat_id}\n\n"
            f"Click below for rules 👇"
        )

        kb = [[InlineKeyboardButton("📜 Rules", callback_data="rules")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ================= RULES =================
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📜 *Group Rules*\n"
        "1️⃣ No 18+ content\n"
        "2️⃣ No spam\n"
        "3️⃣ Respect others\n"
        "4️⃣ No PM/DM for bad things\n"
        "5️⃣ Follow admins",
        parse_mode="Markdown"
    )

# ================= AI CHAT =================
async def ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return

    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": update.message.text}]
        )
        await update.message.reply_text(res.choices[0].message.content)
    except:
        pass

# ================= WARN SYSTEM =================
def add_warn(chat, user):
    data.setdefault("warns", {}).setdefault(chat, {})
    data["warns"][chat][user] = data["warns"][chat].get(user, 0) + 1
    save(data)
    return data["warns"][chat][user]

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to user")

    user = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason"

    chat = str(update.effective_chat.id)
    warns = add_warn(chat, str(user.id))

    await update.message.reply_text(
        f"⚠️ Warned {user.first_name}\nReason: {reason}\nTotal warns: {warns}"
    )

async def removewarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    chat = str(update.effective_chat.id)

    data["warns"][chat][str(user.id)] = 0
    save(data)

    await update.message.reply_text("✅ Warn removed")

# ================= BAN =================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason"

    await update.effective_chat.ban_member(user.id)

    await update.message.reply_text(
        f"🚫 Banned {user.first_name}\nReason: {reason}"
    )

# ================= BAD WORD FILTER =================
BAD = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox","thevidya","ummbu","gommala","ommala","mairu","thayali"
]
async def filter_bad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.lower()
    chat = str(update.effective_chat.id)
    user = update.effective_user

    for w in BAD:
        if w in msg:
            await update.message.delete()

            warns = add_warn(chat, str(user.id))

            await update.message.chat.send_message(
                f"⚠️ {user.first_name} message removed\nReason: Bad word\nWarns: {warns}"
            )
            return

# ================= GAMES =================
games = {}

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games["num"] = random.randint(1, 20)
    await update.message.reply_text("🎯 Guess number (1-20)")

async def check_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "num" in games:
        try:
            if int(update.message.text) == games["num"]:
                add_points(str(update.effective_chat.id), str(update.effective_user.id))
                await update.message.reply_text("🎉 Correct! +10 points")
                del games["num"]
        except:
            pass

words = ["apple","tiger","python","banana"]

async def scramble(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w = random.choice(words)
    games["word"] = w
    sh = "".join(random.sample(w,len(w)))
    await update.message.reply_text(f"🔤 Unscramble: {sh}")

# ================= LEADERBOARD =================
def add_points(chat, user):
    data.setdefault("points", {}).setdefault(chat, {})
    data["points"][chat][user] = data["points"][chat].get(user, 0) + 10
    save(data)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = str(update.effective_chat.id)
    scores = data.get("points", {}).get(chat, {})

    text = "🏆 Leaderboard:\n"
    for u,s in sorted(scores.items(), key=lambda x:x[1], reverse=True):
        text += f"{u}: {s}\n"

    await update.message.reply_text(text)

# ================= AI QUIZ =================
async def quiz(context: ContextTypes.DEFAULT_TYPE):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":"simple MCQ quiz"}]
        )
        await context.bot.send_message(chat_id=context.job.chat_id, text="🧠 Quiz:\n"+res.choices[0].message.content)
    except:
        pass

async def startquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.job_queue.run_repeating(quiz, QUIZ_INTERVAL, chat_id=chat_id)
    await update.message.reply_text("✅ Auto quiz started")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))

    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("removewarn", removewarn))
    app.add_handler(CommandHandler("ban", ban))

    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CommandHandler("scramble", scramble))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("startquiz", startquiz))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_guess))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai))

    print("🤖 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()