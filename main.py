import logging
import os
import threading
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

# Mini Web Server for Render Port Check
web_app = Flask(__name__)


@web_app.route("/")
def home():
  return "AutoPost Bot is running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  web_app.run(host="0.0.0.0", port=port)


# Telegram Bot Logic
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  auth_url = (
      f"https://www.tiktok.com/v2/auth/authorize/"
      f"?client_key={TIKTOK_CLIENT_KEY}"
      f"&scope=user.info.basic,video.upload"
      f"&response_type=code"
      f"&redirect_uri=https://google.com"
  )

  keyboard = [
      [InlineKeyboardButton("🔗 Connect TikTok Account", url=auth_url)]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await update.message.reply_text(
      "স্বাগতম! 🚀\n\n১. নিচের লিংকে ক্লিক করে টিকটক অ্যাকাউন্ট কানেক্ট করে নাও।\n"
      "২. এরপর যেকোনো ভিডিও ক্যাপশনসহ পাঠালে আমি প্রসেস করে দেবো।",
      reply_markup=reply_markup,
  )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  caption = message.caption or "Uploaded via AutoPost Bot"

  status_msg = await message.reply_text("📥 ভিডিও গ্রহণ করা হয়েছে! ডাউনলোডিং...")

  video_file = await message.video.get_file()
  file_path = f"downloads_{message.video.file_id}.mp4"
  await video_file.download_to_drive(file_path)

  await status_msg.edit_text("⚙️ টিকটক স্যান্ডবক্সে পাঠানো হচ্ছে...")

  file_size = os.path.getsize(file_path)

  # Direct Video Post payload
  headers = {
      "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
      "Content-Type": "application/json; charset=UTF-8",
  }

  init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
  payload = {
      "source_info": {
          "source": "FILE_UPLOAD",
          "video_size": file_size,
          "chunk_size": file_size,
          "total_chunk_count": 1,
      }
  }

  try:
    response = requests.post(init_url, json=payload, headers=headers)
    res_data = response.json()

    if response.status_code == 200 and "data" in res_data:
      upload_url = res_data["data"]["upload_url"]

      with open(file_path, "rb") as f:
        video_bytes = f.read()

      upload_headers = {
          "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
          "Content-Type": "video/mp4",
      }
      upload_res = requests.put(
          upload_url, data=video_bytes, headers=upload_headers
      )

      if upload_res.status_code in [200, 201]:
        await status_msg.edit_text(
            f"🎉 সফলভাবে টিকটকে আপলোড হয়েছে!\n\nক্যাপশন: {caption}"
        )
      else:
        await status_msg.edit_text(
            f"⚠️ ভিডিও আপলোডে সমস্যা হয়েছে: {upload_res.status_code}"
        )
    else:
      await status_msg.edit_text(
          f"⚠️ টিকটক রেসপন্স:\n{res_data.get('error', {}).get('message', 'টোকেন ভেরিফিকেশন প্রয়োজন')}\n\n"
          f"ভিডিও প্রসেস সম্পন্ন: {file_size / (1024*1024):.2f} MB"
      )
  except Exception as e:
    await status_msg.edit_text(f"ত্রুটি: {str(e)}")

  if os.path.exists(file_path):
    os.remove(file_path)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set.")
    exit(1)

  # Run Web Server in a separate thread for Render health check
  threading.Thread(target=run_web, daemon=True).start()

  # Run Telegram Polling
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(MessageHandler(filters.VIDEO, handle_video))

  print("Bot is starting with Web Server...")
  app.run_polling()
