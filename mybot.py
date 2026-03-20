print("🔥 GOD LEVEL BOT STARTED 🔥")

import os, json, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from openai import AsyncOpenAI

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QUIZ_INTERVAL = 600

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"

# ================= DATA =================
def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {"warns": {}, "points": {}, "quiz": {}}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load()

# ================= ADMIN =================
async def is_admin(update):
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ["administrator", "creator"]

# ================= AUTO DELETE =================
async def auto_delete(msg):
    await asyncio.sleep(120)
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

# ================= WARN =================
def add_warn(chat, user):
    data["warns"].setdefault(chat, {})
    data["warns"][chat][user] = data["warns"][chat].get(user, 0) + 1
    save()
    return data["warns"][chat][user]

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user
    chat = str(update.effective_chat.id)

    warns = add_warn(chat, str(user.id))

    # BUTTON
    kb = [[InlineKeyboardButton("✅ Remove Warn", callback_data=f"removewarn_{user.id}")]]

    msg = await update.message.reply_text(
        f"⚠️ {user.first_name} warned\n"
        f"Reason: against the group rules\n"
        f"Warns: {warns}/3",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    asyncio.create_task(auto_delete(msg))

    if warns >= 3:
        await update.effective_chat.ban_member(user.id)
        await update.message.reply_text(f"🚫 {user.first_name} auto banned (3 warns)")

# ================= BUTTON REMOVE WARN =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_admin(update):
        return await query.answer("Admin only!", show_alert=True)

    data_id = query.data.split("_")[1]
    chat = str(update.effective_chat.id)

    data["warns"][chat][data_id] = 0
    save()

    await query.edit_message_text("✅ Warn removed by admin")

# ================= BAN =================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return

    user = update.message.reply_to_message.from_user
    await update.effective_chat.ban_member(user.id)
    await update.message.reply_text("🚫 User banned")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return

    user = update.message.reply_to_message.from_user
    await update.effective_chat.unban_member(user.id)
    await update.message.reply_text("✅ User unbanned")

# ================= BAD WORD + AI SPAM =================
BAD = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox","thevidya","ummbu","gommala","mairu","pvrt","thaniya","ommala","thayali","badu","ummbi"
]

async def filter_bad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        return

    msg = update.message.text.lower()
    user = update.effective_user
    chat = str(update.effective_chat.id)

    # NORMAL BAD WORD
    for w in BAD:
        if w in msg:
            await update.message.delete()
            warns = add_warn(chat, str(user.id))
            m = await update.message.chat.send_message(
                f"⚠️ {user.first_name}\nReason: against the group rules\nWarns: {warns}/3"
            )
            asyncio.create_task(auto_delete(m))
            return

    # AI SPAM DETECTION
    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":f"Is this spam or toxic? Answer yes or no:\n{msg}"}]
        )
        if "yes" in res.choices[0].message.content.lower():
            await update.message.delete()
            warns = add_warn(chat, str(user.id))
            await update.message.chat.send_message(
                f"⚠️ Spam detected ({user.first_name})\nWarns: {warns}/3"
            )
    except:
        pass

# ================= AI CHAT =================
async def ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return

    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":update.message.text}]
        )
        await update.message.reply_text(res.choices[0].message.content)
    except Exception as e:
        print("AI ERROR:", e)

# ================= QUIZ =================
async def quiz(context: ContextTypes.DEFAULT_TYPE):
    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":"simple MCQ with answer"}]
        )

        text = res.choices[0].message.content
        chat_id = context.job.chat_id

        data["quiz"][str(chat_id)] = text.split("Answer:")[-1].strip().lower()
        save()

        await context.bot.send_message(chat_id, "🧠 Quiz:\n"+text)
    except:
        pass

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = str(update.effective_chat.id)

    if chat not in data["quiz"]:
        return

    if update.message.text.lower() in data["quiz"][chat]:
        user = str(update.effective_user.id)
        data["points"].setdefault(chat, {})
        data["points"][chat][user] = data["points"][chat].get(user, 0) + 5
        save()

        await update.message.reply_text("🎉 Correct! +5 points")
        del data["quiz"][chat]

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = str(update.effective_chat.id)
    scores = data["points"].get(chat, {})

    text = "🏆 Leaderboard\n"
    for u,s in sorted(scores.items(), key=lambda x:x[1], reverse=True):
        text += f"{u}: {s}\n"

    await update.message.reply_text(text)

# ================= START =================
async def startquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_repeating(quiz, QUIZ_INTERVAL, chat_id=update.effective_chat.id)
    await update.message.reply_text("✅ Quiz started (10 min)")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("startquiz", startquiz))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai))

    print("🚀 GOD BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()