import logging
import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Tokens from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "স্বাগতম! 🚀\nআমাকে একটি ভিডিও এবং সাথে ক্যাপশন পাঠিয়ে দাও, আমি স্বয়ংক্রিয়ভাবে প্রসেস করব।"
  )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  caption = message.caption or "Uploaded via AutoPost Bot"

  status_msg = await message.reply_text("📥 ভিডিও গ্রহণ করা হয়েছে! প্রসেস হচ্ছে...")

  # Get the video file
  video_file = await message.video.get_file()
  file_path = f"downloads/{message.video.file_id}.mp4"
  os.makedirs("downloads", exist_ok=True)

  await video_file.download_to_drive(file_path)
  await status_msg.edit_text("⚙️ টিকটক স্যান্ডবক্সে ভিডিও পাঠানো হচ্ছে...")

  # Upload simulation message
  await status_msg.edit_text(
      f"✅ সফল হয়েছে!\n\nক্যাপশন: {caption}\nভিডিও সাইজ: {message.video.file_size / (1024*1024):.2f} MB"
  )

  # Cleanup local file
  if os.path.exists(file_path):
    os.remove(file_path)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    exit(1)

  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(filters.VIDEO, handle_video)

  print("Bot is starting...")
  app.run_polling()
