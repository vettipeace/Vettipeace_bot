print("🔥 PRO MAX BOT STARTED 🔥")

import os, json, asyncio, time
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from openai import AsyncOpenAI

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

# ================= ADMIN CHECK =================
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

# ================= ANTI SPAM =================
user_msgs = defaultdict(list)

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        return False

    user_id = update.effective_user.id
    now = time.time()
    user_msgs[user_id] = [t for t in user_msgs[user_id] if now - t < 5]
    user_msgs[user_id].append(now)

    if len(user_msgs[user_id]) > 5:
        try:
            await update.message.delete()
        except:
            pass
        warns = add_warn(str(update.effective_chat.id), user_id)
        m = await update.effective_chat.send_message(
            f"⚠️ Spam detected ({update.effective_user.first_name})\nWarns: {warns}/3"
        )
        asyncio.create_task(auto_delete(m))
        if warns >= 3:
            await update.effective_chat.ban_member(user_id)
        return True
    return False

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
    chat = str(chat)
    user = str(user)
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
    warns = add_warn(chat, user.id)
    kb = [[InlineKeyboardButton("✅ Remove Warn", callback_data=f"removewarn_{user.id}")]]
    msg = await update.message.reply_text(
        f"⚠️ {user.first_name} warned\n"
        f"Reason: against the group rules\n"
        f"Warns: {warns}/3",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    asyncio.create_task(auto_delete(msg))
    if warns >= 3:
        ban_msg = await update.effective_chat.send_message(
            f"🚫 {user.first_name} auto banned (3 warns)"
        )
        await update.effective_chat.ban_member(user.id)
        asyncio.create_task(auto_delete(ban_msg))

# ================= REMOVE WARN =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(update):
        return await query.answer("Admin only!", show_alert=True)
    user_id = query.data.split("_")[1]
    chat = str(update.effective_chat.id)
    if chat in data["warns"] and user_id in data["warns"][chat]:
        data["warns"][chat][user_id] = 0
        save()
    msg = await query.edit_message_text("✅ Warn removed by admin")
    asyncio.create_task(auto_delete(msg))

async def removewarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a user to remove warn")
    user = update.message.reply_to_message.from_user
    chat = str(update.effective_chat.id)
    if chat in data["warns"] and str(user.id) in data["warns"][chat]:
        data["warns"][chat][str(user.id)] = 0
        save()
    msg = await update.message.reply_text(f"✅ Warn removed for {user.first_name}")
    asyncio.create_task(auto_delete(msg))

# ================= BAN / UNBAN =================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    user = update.message.reply_to_message.from_user
    await update.effective_chat.ban_member(user.id)
    msg = await update.message.reply_text("🚫 User banned")
    asyncio.create_task(auto_delete(msg))

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    user = update.message.reply_to_message.from_user
    await update.effective_chat.unban_member(user.id)
    msg = await update.message.reply_text("✅ User unbanned")
    asyncio.create_task(auto_delete(msg))

# ================= BAD WORD FILTER =================
BAD = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox","thevidya","ummbu","gommala","ommala","kotta","badu","pvrt","ummbi","thayali","aatha","otha"
]

async def filter_bad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update):
        return
    if not update.message.text:
        return
    if await anti_spam(update, context):
        return
    msg = update.message.text.lower()
    user = update.effective_user
    chat = str(update.effective_chat.id)
    for w in BAD:
        if w in msg:
            try: await update.message.delete()
            except: pass
            warns = add_warn(chat, user.id)
            m = await update.effective_chat.send_message(
                f"⚠️ {user.first_name}\nReason: against the group rules\nWarns: {warns}/3"
            )
            asyncio.create_task(auto_delete(m))
            if warns >= 3:
                await update.effective_chat.ban_member(user.id)
            return

# ================= AI CHAT =================
async def ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text or update.message.text.startswith("/"):
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
        chat_id = context.job.chat_id
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":"simple MCQ with 4 options and Answer:"}]
        )
        text = res.choices[0].message.content
        answer = text.split("Answer:")[-1].strip().lower()
        data["quiz"][str(chat_id)] = answer
        save()
        await context.bot.send_message(chat_id, "🧠 Quiz:\n" + text)
    except Exception as e:
        print("QUIZ ERROR:", e)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = str(update.effective_chat.id)
    if chat not in data["quiz"]:
        return
    if data["quiz"][chat] in update.message.text.lower():
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
    for u, s in sorted(scores.items(), key=lambda x:x[1], reverse=True):
        try:
            member = await context.bot.get_chat_member(chat, int(u))
            name = member.user.first_name
        except:
            name = u
        text += f"{name}: {s}\n"
    msg = await update.message.reply_text(text)
    asyncio.create_task(auto_delete(msg))

# ================= START QUIZ =================
async def startquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.application.job_queue.run_repeating(
        quiz, interval=QUIZ_INTERVAL, first=0, chat_id=chat_id
    )
    msg = await update.message.reply_text("✅ Quiz started (10 min)")
    asyncio.create_task(auto_delete(msg))

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # COMMANDS
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("removewarn", removewarn))

    app.add_handler(CommandHandler  ("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("startquiz", startquiz))

    # BUTTON HANDLER
    app.add_handler(CallbackQueryHandler(button_handler))

    # WELCOME
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    # MESSAGES
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai))

    print("🚀 PRO MAX BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()