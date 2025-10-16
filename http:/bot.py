
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ---------- Load ENV ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_CHANNELS = [ch.strip() for ch in os.getenv("FORCE_CHANNELS", "").split(",") if ch.strip()]
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split(",") if i.strip().isdigit()]
PORT = int(os.getenv("PORT", 8080))

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)

# ---------- Flask (for uptime) ----------
app = Flask("ForceSubBot")

@app.route('/')
def home():
    return "✅ Force Subscribe Bot Running!"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

# ---------- Bot ----------
bot = Client("ForceSubBot", bot_token=BOT_TOKEN)


# ---------- Utils ----------
def join_keyboard(channels):
    buttons = []
    for ch in channels:
        if ch.startswith("http") or "t.me" in ch:
            url = ch
        else:
            url = f"https://t.me/{ch.lstrip('@')}"
        buttons.append([InlineKeyboardButton(f"Join {ch}", url=url)])
    buttons.append([InlineKeyboardButton("🔁 Recheck", callback_data="recheck")])
    return InlineKeyboardMarkup(buttons)


async def check_membership(user_id):
    missing = []
    for ch in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing


# ---------- Handlers ----------
@bot.on_message(filters.all & ~filters.user(ADMINS))
async def check_join(client, message):
    if not FORCE_CHANNELS:
        return

    user_id = message.from_user.id
    missing = await check_membership(user_id)

    if missing:
        await message.reply_text(
            "🚫 Aapko bot use karne ke liye ye channel join karna hoga 👇",
            reply_markup=join_keyboard(missing),
            quote=True
        )
        if message.chat.type in ["supergroup", "group"]:
            try:
                await message.delete()
            except:
                pass


@bot.on_callback_query(filters.regex("recheck"))
async def recheck_join(client, callback):
    user_id = callback.from_user.id
    missing = await check_membership(user_id)
    if not missing:
        await callback.answer("✅ Verified! You have joined all required channels.", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
    else:
        await callback.answer("🚫 Abhi bhi join nahi kiya!", show_alert=True)
        await callback.message.edit_reply_markup(join_keyboard(missing))


# ---------- Admin Commands ----------
@bot.on_message(filters.command("addchannel") & filters.user(ADMINS))
async def add_channel(_, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: /addchannel @ChannelUsername")
    ch = msg.command[1]
    if ch not in FORCE_CHANNELS:
        FORCE_CHANNELS.append(ch)
        await msg.reply_text(f"✅ Added {ch} to required channels.")
    else:
        await msg.reply_text(f"{ch} already added.")


@bot.on_message(filters.command("listchannels") & filters.user(ADMINS))
async def list_channels(_, msg):
    if not FORCE_CHANNELS:
        await msg.reply_text("No required channels set.")
    else:
        await msg.reply_text("Required Channels:\n" + "\n".join(FORCE_CHANNELS))


# ---------- Run ----------
if name == "main":
    Thread(target=run_web).start()
    logging.info("Bot started...")
    bot.run()
