import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import openai
from langdetect import detect

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN"
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
openai.api_key = OPENAI_API_KEY
BAD_WORDS = [
    "sex","porn","xxx","nude","fuck","ass","bitch","cunt","dick",
    "cock","pussy","slut","whore","rape","masturbate","boobs","penis",
    "pm","dm","private chat","private message","direct chat","direct message",
    "punda","sunni","potta","thevudiya","thayoli","oombu","nudity","inbox",
    "thevidya","ummbu","gommala","ommala","kotta","badu","pvrt","ummbi",
    "thayali","aatha","otha",
]
MAX_WARNS = 3

# ================= DATA HANDLER =================
def load_data():
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= AUTO DELETE =================
async def auto_delete(message, delay=120):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

# ================= WELCOME + RULES =================
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
    user = update.message.from_user
    chat_id = update.effective_chat.id
    text = update.message.text.lower()

    if any(word in text for word in BAD_WORDS):
        if user.id != context.bot.id and not update.message.from_user.id in context.bot_data.get("admins", []):
            # Admin exempt
            data.setdefault("warns", {})
            warns = data["warns"].get(str(user.id), 0) + 1
            data["warns"][str(user.id)] = warns
            save_data(data)
            
            reason = "Bad word"
            await update.message.delete()
            await update.message.reply_text(f"⚠️ {user.first_name}, you used a forbidden word.\nReason: {reason}\nWarn: {warns}/{MAX_WARNS}")
            
            if warns >= MAX_WARNS:
                await context.bot.ban_chat_member(chat_id, user.id)
                await update.message.reply_text(f"🚫 {user.first_name} has been banned due to 3 warns.")
        else:
            await update.message.delete()  # Admin just delete

# ================= WARN COMMANDS =================
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.from_user.id in context.bot_data.get("admins", []):
        return
    user_id = str(context.args[0])
    data.setdefault("warns", {})
    data["warns"][user_id] = data["warns"].get(user_id, 0) + 1
    save_data(data)
    await update.message.reply_text(f"⚠️ Warn added to {user_id}. Total: {data['warns'][user_id]}")

async def removewarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.from_user.id in context.bot_data.get("admins", []):
        return
    user_id = str(context.args[0])
    data.setdefault("warns", {})
    data["warns"][user_id] = max(data["warns"].get(user_id, 0) - 1, 0)
    save_data(data)
    await update.message.reply_text(f"✅ Warn removed from {user_id}. Total: {data['warns'][user_id]}")

# ================= BAN/UNBAN =================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.from_user.id in context.bot_data.get("admins", []):
        return
    user_id = int(context.args[0])
    await context.bot.ban_chat_member(update.effective_chat.id, user_id)
    await update.message.reply_text(f"🚫 User {user_id} banned.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.from_user.id in context.bot_data.get("admins", []):
        return
    user_id = int(context.args[0])
    await context.bot.unban_chat_member(update.effective_chat.id, user_id)
    await update.message.reply_text(f"✅ User {user_id} unbanned.")

# ================= AI CHAT =================
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return
    prompt = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}]
        )
        answer = response['choices'][0]['message']['content']
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text("❌ AI Error!")

# ================= AI QUIZ =================
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data.setdefault("quiz", {})
    data["quiz"][str(update.effective_chat.id)] = {"started": True, "questions": [], "answers": []}
    save_data(data)
    await update.message.reply_text("✅ Quiz started (questions & answers will not delete).")
    
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🏆 Daily Score", callback_data="daily"),
        InlineKeyboardButton("📅 Weekly Score", callback_data="weekly"),
        InlineKeyboardButton("🌐 Overall Score", callback_data="overall")
    ]]
    await update.message.reply_text("🏆 Leaderboard", reply_markup=InlineKeyboardMarkup(keyboard))

async def leaderboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    await query.edit_message_text(f"📊 Showing {choice} leaderboard (placeholder)")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Track admins manually for example
    app.bot_data["admins"] = []  # Add admin user ids here

    # Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad_words))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("removewarn", removewarn))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("quiz", start_quiz))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CallbackQueryHandler(leaderboard_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    print("🔥 PRO MAX BOT STARTED 🔥")
    app.run_polling()

if __name__ == "__main__":
    main()