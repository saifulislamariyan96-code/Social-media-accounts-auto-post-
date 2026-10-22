import logging
import os
import threading
import urllib.parse
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

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Mini Web Server for Render Keep-Alive
web_app = Flask(__name__)


@web_app.route("/")
def home():
  return "AutoPost Bot is running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  web_app.run(host="0.0.0.0", port=port)


# Tokens and Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")

USER_TARGETS = {}
TIKTOK_TOKENS = {}

KEYBOARD_LAYOUT = [
    [
        KeyboardButton("📱 Account 1 (@ayman9200)"),
        KeyboardButton("📱 Account 2 (@saiful.islam.ayman)"),
    ],
    [
        KeyboardButton("📱 Account 3 (@saiful.islam.ayman1)"),
        KeyboardButton("🚀 Post to All Accounts"),
    ],
]
REPLY_KEYBOARD = ReplyKeyboardMarkup(
    KEYBOARD_LAYOUT, resize_keyboard=True, is_persistent=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if user_id not in USER_TARGETS:
    USER_TARGETS[user_id] = "🚀 Post to All Accounts"

  auth_url = (
      f"https://www.tiktok.com/v2/auth/authorize/"
      f"?client_key={TIKTOK_CLIENT_KEY}"
      f"&scope=user.info.basic,video.upload,video.publish"
      f"&response_type=code"
      f"&redirect_uri=https://google.com"
  )

  inline_kb = [
      [InlineKeyboardButton("🔗 Connect TikTok Account", url=auth_url)]
  ]

  text = (
      "স্বাগতম! 🚀\n\n"
      f"🎯 **বর্তমান টার্গেট:** `{USER_TARGETS[user_id]}`\n\n"
      "নিচের বাটন চেপে টার্গেট নির্বাচন করতে পারো। এরপর যেকোনো ভিডিও, ছবি বা"
      " ডকুমেন্ট পাঠালে তা স্বয়ংক্রিয়ভাবে প্রস্তুত হবে।"
  )

  await update.message.reply_text(
      text, parse_mode="Markdown", reply_markup=REPLY_KEYBOARD
  )
  await update.message.reply_text(
      "অ্যাকাউন্ট কানেক্ট করতে নিচের বাটনে চাপ দাও:",
      reply_markup=InlineKeyboardMarkup(inline_kb),
  )


async def token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not context.args:
    await update.message.reply_text("ব্যবহার: `/token <সম্পূর্ণ লিংক বা কোড>`")
    return

  raw_input = " ".join(context.args)

  if "code=" in raw_input:
    parsed = urllib.parse.urlparse(raw_input)
    qs = urllib.parse.parse_qs(parsed.query)
    auth_code = qs.get("code", [raw_input])[0]
  else:
    auth_code = raw_input

  auth_code = urllib.parse.unquote(auth_code)

  await update.message.reply_text(
      "🔄 কোড এক্সচেঞ্জ করে টিকটক অ্যাক্সেস টোকেন আনা হচ্ছে..."
  )

  token_url = "https://open.tiktokapis.com/v2/oauth/token/"
  headers = {"Content-Type": "application/x-www-form-urlencoded"}
  data = {
      "client_key": TIKTOK_CLIENT_KEY,
      "client_secret": TIKTOK_CLIENT_SECRET,
      "code": auth_code,
      "grant_type": "authorization_code",
      "redirect_uri": "https://google.com",
  }

  try:
    res = requests.post(token_url, headers=headers, data=data)
    res_json = res.json()

    if "access_token" in res_json:
      token = res_json["access_token"]
      open_id = res_json.get("open_id", "Default")
      TIKTOK_TOKENS["primary"] = token
      await update.message.reply_text(
          f"🎉 **অভিনন্দন! TikTok অ্যাকাউন্ট সফলভাবে যুক্ত হয়েছে!**\n\n"
          f"🔑 OpenID: `{open_id}`\n\n"
          f"এখন ভিডিও বা ছবি ক্যাপশনসহ পাঠালে সরাসরি টিকটকে আপলোড হবে!",
          parse_mode="Markdown",
      )
    else:
      error_msg = res_json.get("error_description") or res_json.get(
          "message", str(res_json)
      )
      await update.message.reply_text(f"⚠️ টোকেন ত্রুটি: {error_msg}")
  except Exception as e:
    await update.message.reply_text(f"ত্রুটি: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  help_text = (
      "ℹ️ **বট ব্যবহারের নিয়মাবলী:**\n\n"
      "১. নিচে থাকা কিবোর্ড বাটন চেপে কোন অ্যাকাউন্টে পোস্ট করতে চাও তা"
      " সিলেক্ট করো।\n"
      "২. ভিডিও, ফটো বা ডকুমেন্ট ফাইল হিসেবে মিডিয়া পাঠাও।\n"
      "৩. ক্যাপশনে যা লিখবে, সেটাই ভিডিওর আসল ক্যাপশন হিসেবে যাবে।\n"
      "৪. /status দিয়ে বর্তমান কানেকশন ও অ্যাক্টিভ টার্গেট দেখে নিতে পারো।"
  )
  await update.message.reply_text(
      help_text, parse_mode="Markdown", reply_markup=REPLY_KEYBOARD
  )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  token_status = (
      "🟢 সংযুক্ত আছে" if "primary" in TIKTOK_TOKENS else "🔴 এখনো যুক্ত হয়নি"
  )
  status_text = (
      "📊 **বট ও সার্ভার স্ট্যাটাস:**\n\n"
      "🟢 সার্ভার: **অনলাইন (২৪/৭ সচল)**\n"
      f"🔑 টিকটক অ্যাকাউন্ট: **{token_status}**\n"
      f"🎯 বর্তমান টার্গেট: **{target}**\n"
      "📦 ফরম্যাট সাপোর্ট: ভিডিও, ফটো, আনকমপ্রেসড ফাইল"
  )
  await update.message.reply_text(
      status_text, parse_mode="Markdown", reply_markup=REPLY_KEYBOARD
  )


async def handle_button_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  text = update.message.text
  user_id = update.effective_user.id

  valid_buttons = [
      "📱 Account 1 (@ayman9200)",
      "📱 Account 2 (@saiful.islam.ayman)",
      "📱 Account 3 (@saiful.islam.ayman1)",
      "🚀 Post to All Accounts",
  ]

  if text in valid_buttons:
    USER_TARGETS[user_id] = text
    await update.message.reply_text(
        f"✅ টার্গেট সফলভাবে নির্বাচন করা হয়েছে!\n\n🎯 বর্তমান টার্গেট:"
        f" **{text}**\nএখন মিডিয়া পাঠালে এই টার্গেটে পোস্ট হবে।",
        parse_mode="Markdown",
        reply_markup=REPLY_KEYBOARD,
    )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  caption = message.caption or "Uploaded via AutoPost Bot"

  token = TIKTOK_TOKENS.get("primary")
  if not token:
    await message.reply_text(
        "⚠️ কোনো টিকটক অ্যাকাউন্ট এখনো যুক্ত করা হয়নি! আগে কানেক্ট করে নাও।"
    )
    return

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
  await status_msg.edit_text(
      f"⚙️ {media_type} টিকটকে সরাসরি আপলোড করা হচ্ছে..."
  )

  headers = {
      "Authorization": f"Bearer {token}",
      "Content-Type": "application/json; charset=UTF-8",
  }

  init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
  payload = {
      "post_info": {
          "title": caption,
          "privacy_level": "SELF_ONLY",
          "disable_duet": False,
          "disable_comment": False,
          "disable_stitch": False,
          "video_cover_timestamp_ms": 1000,
      },
      "source_info": {
          "source": "FILE_UPLOAD",
          "video_size": file_size,
          "chunk_size": file_size,
          "total_chunk_count": 1,
      },
  }

  try:
    response = requests.post(init_url, json=payload, headers=headers)
    res_data = response.json()

    if response.status_code == 200 and "data" in res_data:
      upload_url = res_data["data"]["upload_url"]
      publish_id = res_data["data"].get("publish_id", "N/A")

      with open(file_name, "rb") as f:
        media_bytes = f.read()

      upload_headers = {
          "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
          "Content-Type": "video/mp4",
      }
      upload_res = requests.put(
          upload_url, data=media_bytes, headers=upload_headers
      )

      if upload_res.status_code in [200, 201]:
        await status_msg.edit_text(
            f"🎉 **সফলভাবে টিকটকে পোস্ট হয়েছে!**\n\n"
            f"📦 টাইপ: {media_type}\n"
            f"🆔 Publish ID: `{publish_id}`\n"
            f"🎯 পোস্ট হয়েছে: **{target}**\n"
            f"📝 ক্যাপশন: {caption}\n\n"
            f"🔒 মোড: Private (স্যান্ডবক্স পলিসি অনুযায়ী)। টিকটক অ্যাপে ভিডিওটি"
            f" সরাসরি দেখতে পাবে!",
            parse_mode="Markdown",
        )
      else:
        await status_msg.edit_text(
            f"⚠️ বাইট আপলোডে সমস্যা: {upload_res.status_code}"
        )
    else:
      error_info = res_data.get("error", {})
      await status_msg.edit_text(
          f"⚠️ টিকটক এপিআই রেসপন্স:\n{error_info.get('message', 'ত্রুটি')}\n"
          f"কোড: `{error_info.get('code', 'N/A')}`"
      )
  except Exception as e:
    await status_msg.edit_text(f"ত্রুটি: {str(e)}")

  if os.path.exists(file_name):
    os.remove(file_name)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    exit(1)

  threading.Thread(target=run_web, daemon=True).start()

  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("help", help_command))
  app.add_handler(CommandHandler("status", status_command))
  app.add_handler(CommandHandler("token", token_handler))
  app.add_handler(
      MessageHandler(
          filters.Regex(r"^(📱 Account|🚀 Post to All Accounts)"),
          handle_button_click,
      )
  )
  app.add_handler(
      MessageHandler(
          filters.VIDEO | filters.PHOTO | filters.Document.ALL, handle_media
      )
  )

  app.run_polling()
