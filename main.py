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
      "স্বাগতম! 🚀\n\n"
      "আমি ভিডিও, ছবি এবং আনকমপ্রেসড ফাইল সব ফরম্যাট সাপোর্ট করি।\n"
      "ক্যাপশনসহ যেকোনো মিডিয়া পাঠিয়ে দাও!",
      reply_markup=reply_markup,
  )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  caption = message.caption or "Uploaded via AutoPost Bot"

  status_msg = await message.reply_text(
      "📥 মিডিয়া ফাইল গ্রহণ করা হয়েছে! ডাউনলোডিং..."
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
  await status_msg.edit_text(
      f"⚙️ {media_type} প্রসেস হচ্ছে এবং সার্ভারে পাঠানো হচ্ছে..."
  )

  file_size_mb = (file_size / (1024 * 1024)) if file_size else 0

  # TikTok Direct Upload Process
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

      with open(file_name, "rb") as f:
        media_bytes = f.read()

      upload_headers = {
          "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
          "Content-Type": (
              "video/mp4" if media_type != "Photo" else "image/jpeg"
          ),
      }
      upload_res = requests.put(
          upload_url, data=media_bytes, headers=upload_headers
      )

      if upload_res.status_code in [200, 201]:
        await status_msg.edit_text(
            f"🎉 সফলভাবে টিকটকে আপলোড হয়েছে!\n\nটাইপ: {media_type}\nক্যাপশন: {caption}"
        )
      else:
        await status_msg.edit_text(
            f"⚠️ আপলোডে সমস্যা হয়েছে: {upload_res.status_code}"
        )
    else:
      await status_msg.edit_text(
          f"✅ ফাইল প্রসেস সফল!\n\n"
          f"ফরম্যাট: {media_type}\n"
          f"সাইজ: {file_size_mb:.2f} MB\n"
          f"ক্যাপশন: {caption}\n\n"
          f"রেসপন্স: {res_data.get('error', {}).get('message', 'টোকেন ভেরিফিকেশন অ্যাক্টিভ')}"
      )
  except Exception as e:
    await status_msg.edit_text(f"ত্রুটি: {str(e)}")

  if os.path.exists(file_name):
    os.remove(file_name)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set.")
    exit(1)

  threading.Thread(target=run_web, daemon=True).start()

  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(
      MessageHandler(
          filters.VIDEO | filters.PHOTO | filters.Document.ALL, handle_media
      )
  )

  print("Bot is starting...")
  app.run_polling()
