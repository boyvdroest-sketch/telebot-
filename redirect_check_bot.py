from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

# --- Replace with your actual Bot Token from BotFather ---
BOT_TOKEN = "8327048029:AAH_hpFmCfjM5xxilIF_tdQMScIeUGF9f4k"

# --- Replace with your actual channel username ---
CHANNEL_USERNAME = "@spidys_vouches"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                "✅ You are already a member of our main channel! Welcome!"
            )
        else:
            raise BadRequest("Not joined")

    except BadRequest:
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Our Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ I Joined", callback_data="joined")]
        ])
        await update.message.reply_text(
            "⚠️ Please join our main channel first to continue.",
            reply_markup=join_button
        )

async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await query.edit_message_text("✅ Thanks for joining! Welcome to our community!")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
    except BadRequest:
        await query.answer("❌ Error checking membership!", show_alert=True)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))

print("🤖 Bot is running...")
app.run_polling()
