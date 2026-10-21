import logging
import os
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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "স্বাগতম! 🚀\nআমাকে একটি ভিডিও এবং সাথে ক্যাপশন পাঠিয়ে দাও, আমি স্বয়ংক্রিয়ভাবে প্রসেস করব।"
  )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  caption = message.caption or "Uploaded via AutoPost Bot"

  status_msg = await message.reply_text(
      "📥 ভিডিও গ্রহণ করা হয়েছে! প্রসেস হচ্ছে..."
  )

  video_file = await message.video.get_file()
  file_path = f"downloads_{message.video.file_id}.mp4"

  await video_file.download_to_drive(file_path)
  await status_msg.edit_text("⚙️ ভিডিও টিকটক স্যান্ডবক্সে পাঠানো হচ্ছে...")

  file_size_mb = (
      message.video.file_size / (1024 * 1024) if message.video.file_size else 0
  )
  await status_msg.edit_text(
      f"✅ সফল হয়েছে!\n\nক্যাপশন: {caption}\nভিডিও সাইজ: {file_size_mb:.2f} MB"
  )

  if os.path.exists(file_path):
    os.remove(file_path)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    exit(1)

  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(MessageHandler(filters.VIDEO, handle_video))

  print("Bot is starting...")
  app.run_polling()
