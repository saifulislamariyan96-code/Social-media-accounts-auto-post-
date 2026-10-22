import logging
import os
import threading
from flask import Flask
import requests
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Mini Web Server for Render
web_app = Flask(__name__)


@web_app.route("/")
def home():
  return "AutoPost Bot is running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  web_app.run(host="0.0.0.0", port=port)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")

# Default selected target
USER_TARGETS = {}

# Persistent Keyboard Buttons
KEYBOARD_LAYOUT = [
    [KeyboardButton("📱 Account 1"), KeyboardButton("📱 Account 2")],
    [KeyboardButton("📱 Account 3"), KeyboardButton("🚀 Post to All Accounts")],
]
REPLY_KEYBOARD = ReplyKeyboardMarkup(
    KEYBOARD_LAYOUT, resize_keyboard=True, is_persistent=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  USER_TARGETS[user_id] = "🚀 Post to All Accounts"

  auth_url = (
      f"https://www.tiktok.com/v2/auth/authorize/"
      f"?client_key={TIKTOK_CLIENT_KEY}"
      f"&scope=user.info.basic,video.upload"
      f"&response_type=code"
      f"&redirect_uri=https://google.com"
  )

  inline_kb = [
      [InlineKeyboardButton("🔗 Connect TikTok Account", url=auth_url)]
  ]

  text = (
      "স্বাগতম! 🚀\n\n"
      "🔹 **বর্তমান টার্গেট:** `🚀 Post to All Accounts`\n\n"
      "নিচের বাটন চেপে টার্গেট অ্যাকাউন্ট বদলাতে পারো।\n"
      "এরপর যেকোনো ভিডিও, ছবি বা ফাইল ক্যাপশনসহ পাঠিয়ে দিলেই স্বয়ংক্রিয়ভাবে আপলোড হবে!"
  )

  await update.message.reply_text(
      text,
      parse_mode="Markdown",
      reply_markup=REPLY_KEYBOARD,
  )
  await update.message.reply_text(
      "অ্যাকাউন্ট কানেক্ট করতে নিচের বাটনে ট্যাপ করো:",
      reply_markup=InlineKeyboardMarkup(inline_kb),
  )


async def handle_button_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  text = update.message.text
  user_id = update.effective_user.id

  if text in [
      "📱 Account 1",
      "📱 Account 2",
      "📱 Account 3",
      "🚀 Post to All Accounts",
  ]:
    USER_TARGETS[user_id] = text
    await update.message.reply_text(
        f"✅ টার্গেট পরিবর্তন করা হয়েছে!\n\nবর্তমানে সিলেক্টেড: **{text}**\nএখন মিডিয়া পাঠালে এই টার্গেটে পোস্ট হবে।",
        parse_mode="Markdown",
        reply_markup=REPLY_KEYBOARD,
    )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  caption = message.caption or "Uploaded via AutoPost Bot"

  status_msg = await message.reply_text(
      f"📥 মিডিয়া গ্রহণ করা হয়েছে!\n🎯 টার্গেট: **{target}**\nডাউনলোডিং...",
      parse_mode="Markdown",
  )

  if message.video:
    media_file = await message.video.get_file()
    file_name = f"downloads_{message.video.file_id}.mp4"
    file_size = message.video.file_size
    media_type = "Video"
  elif message.document:
    media_file = await message.document.get_file()
    ext = (
        os.path.splitext(message.document.file_name)[1]
        if message.document.file_name
        else ".mp4"
    )
    file_name = f"downloads_{message.document.file_id}{ext}"
    file_size = message.document.file_size
    media_type = "File / Document"
  elif message.photo:
    media_file = await message.photo[-1].get_file()
    file_name = f"downloads_{message.photo[-1].file_id}.jpg"
    file_size = message.photo[-1].file_size
    media_type = "Photo"
  else:
    await status_msg.edit_text("⚠️ আনসাপোর্টেড ফরম্যাট!")
    return

  await media_file.download_to_drive(file_name)
  file_size_mb = (file_size / (1024 * 1024)) if file_size else 0

  await status_msg.edit_text(
      f"⚙️ প্রসেসিং সফল!\n\n"
      f"📦 টাইপ: {media_type}\n"
      f"📊 সাইজ: {file_size_mb:.2f} MB\n"
      f"🎯 পাঠানো হচ্ছে: **{target}**\n"
      f"📝 ক্যাপশন: {caption}",
      parse_mode="Markdown",
  )

  if os.path.exists(file_name):
    os.remove(file_name)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    exit(1)

  threading.Thread(target=run_web, daemon=True).start()

  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(
      MessageHandler(
          filters.Regex(
              "^(📱 Account 1|📱 Account 2|📱 Account 3|🚀 Post to All Accounts)$"
          ),
          handle_button_click,
      )
  )
  app.add_handler(
      MessageHandler(
          filters.VIDEO | filters.PHOTO | filters.Document.ALL, handle_media
      )
  )

  app.run_polling()
