import logging
import os
import threading
import urllib.parse
from flask import Flask
import gdown
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
from telegram.request import HTTPXRequest

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

web_app = Flask(__name__)


@web_app.route("/")
def home():
  return "AutoPost Bot is running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  web_app.run(host="0.0.0.0", port=port)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

USER_TARGETS = {}

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
      f"&scope=user.info.basic,video.upload"
      f"&response_type=code"
      f"&redirect_uri=https://google.com"
  )

  inline_kb = [
      [InlineKeyboardButton("🔗 Connect TikTok Account", url=auth_url)]
  ]

  text = (
      "স্বাগতম! 🚀\n\n"
      f"🎯 **বর্তমান টার্গেট:** `{USER_TARGETS[user_id]}`\n\n"
      "🔹 **ব্যবহারের নিয়ম:**\n"
      "১. ২০ MB-র কম ফাইল সরাসরি টেলিগ্রামে পাঠাও।\n"
      "২. বড় গেমিং ক্লিপের (৪০ MB - ৮০০ MB+) ক্ষেত্রে **Google Drive লিংক**"
      " পাঠাও!\n"
      "ক্যাপশনসহ পাঠালেই টিকটকে চলে যাবে।"
  )

  await update.message.reply_text(
      text, parse_mode="Markdown", reply_markup=REPLY_KEYBOARD
  )
  await update.message.reply_text(
      "অ্যাকাউন্ট কানেক্ট বা টোকেন রিনিউ করতে নিচের বাটনে চাপ দাও:",
      reply_markup=InlineKeyboardMarkup(inline_kb),
  )


async def token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global TIKTOK_ACCESS_TOKEN
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
  await update.message.reply_text("🔄 কোড এক্সচেঞ্জ করে টোকেন আনা হচ্ছে...")

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
    res = requests.post(token_url, headers=headers, data=data, timeout=30)
    res_json = res.json()

    if "access_token" in res_json:
      TIKTOK_ACCESS_TOKEN = res_json["access_token"]
      open_id = res_json.get("open_id", "Default")
      await update.message.reply_text(
          f"🎉 **TikTok অ্যাকাউন্ট সফলভাবে যুক্ত হয়েছে!**\n\n"
          f"🔑 OpenID: `{open_id}`\n\n"
          f"📌 **টোকেন:** `{TIKTOK_ACCESS_TOKEN}`",
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
      "১. ছোট ভিডিও (২০ MB পর্যন্ত) সরাসরি সেন্ড করো।\n"
      "২. বড় গেমিং ভিডিও Google Drive-এ আপলোড করে লিংক শেয়ার করো (Access:"
      " Anyone with the link)।\n"
      "৩. লিংকের সাথে ক্যাপশন লিখে দিলে সেটিই পোস্টের ক্যাপশন হবে।"
  )
  await update.message.reply_text(
      help_text, parse_mode="Markdown", reply_markup=REPLY_KEYBOARD
  )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  token_status = (
      "🟢 সক্রিয় আছে" if TIKTOK_ACCESS_TOKEN else "🔴 টোকেন সেট করা নেই"
  )
  status_text = (
      "📊 **বট ও সার্ভার স্ট্যাটাস:**\n\n"
      "🟢 সার্ভার: **অনলাইন (২৪/৭ সচল)**\n"
      f"🔑 টিকটক অ্যাকাউন্ট: **{token_status}**\n"
      f"🎯 বর্তমান টার্গেট: **{target}**\n"
      "📦 সাপোর্ট: সরাসরি ভিডিও (২০ MB) ও গুগল ড্রাইভ লিংক (আনলিমিটেড)"
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
        f"✅ টার্গেট নির্বাচন সম্পন্ন: **{text}**",
        parse_mode="Markdown",
        reply_markup=REPLY_KEYBOARD,
    )


async def upload_to_tiktok(file_path, file_size, caption, target, status_msg):
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

  response = requests.post(init_url, json=payload, headers=headers, timeout=60)
  res_data = response.json()

  if response.status_code == 200 and "data" in res_data:
    upload_url = res_data["data"]["upload_url"]

    with open(file_path, "rb") as f:
      media_bytes = f.read()

    upload_headers = {
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        "Content-Type": "video/mp4",
    }
    upload_res = requests.put(
        upload_url, data=media_bytes, headers=upload_headers, timeout=300
    )

    if upload_res.status_code in [200, 201]:
      file_size_mb = file_size / (1024 * 1024)
      await status_msg.edit_text(
          f"🎉 **সফলভাবে টিকটকে আপলোড হয়েছে!**\n\n"
          f"📊 সাইজ: {file_size_mb:.2f} MB\n"
          f"🎯 পোস্ট হয়েছে: **{target}**\n"
          f"📝 ক্যাপশন: {caption}\n\n"
          f"🔔 টিকটক অ্যাপের System notifications চেক করো, সেখান থেকে এক ক্লিকে"
          f" পোস্ট হয়ে যাবে!",
          parse_mode="Markdown",
      )
    else:
      await status_msg.edit_text(
          f"⚠️ আপলোডে সমস্যা হয়েছে: {upload_res.status_code}"
      )
  else:
    error_info = res_data.get("error", {})
    await status_msg.edit_text(
        f"⚠️ টিকটক এপিআই রেসপন্স:\n{error_info.get('message', 'ত্রুটি')}"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")

  if "drive.google.com" in text:
    if not TIKTOK_ACCESS_TOKEN:
      await update.message.reply_text(
          "⚠️ টিকটক অ্যাকাউন্ট এখনো কানেক্ট করা নেই!"
      )
      return

    status_msg = await update.message.reply_text(
        "📥 Google Drive লিংক পাওয়া গেছে!\nসার্ভারে ফুল কোয়ালিটিতে ডাউনলোড"
        " হচ্ছে..."
    )
    file_name = f"gdrive_{user_id}.mp4"

    try:
      # Extract URL and Caption
      lines = text.split("\n")
      url = lines[0].strip()
      caption = "\n".join(lines[1:]) if len(lines) > 1 else "AutoPost Gaming"

      # Download using gdown
      gdown.download(url, file_name, quiet=False, fuzzy=True)

      if not os.path.exists(file_name):
        await status_msg.edit_text(
            "⚠️ ড্রাইভ থেকে ডাউনলোড করা যায়নি! নিশ্চিত হও ফাইল লিংকটি 'Anyone"
            " with the link' দেওয়া আছে।"
        )
        return

      file_size = os.path.getsize(file_name)
      await status_msg.edit_text(
          f"⚙️ {file_size / (1024 * 1024):.1f} MB ফাইল নামানো হয়েছে। টিকটকে"
          " আপলোড হচ্ছে..."
      )

      await upload_to_tiktok(
          file_name, file_size, caption, target, status_msg
      )
    except Exception as e:
      await status_msg.edit_text(f"ত্রুটি: {str(e)}")
    finally:
      if os.path.exists(file_name):
        os.remove(file_name)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  caption = message.caption or "Uploaded via AutoPost Bot"

  if not TIKTOK_ACCESS_TOKEN:
    await message.reply_text(
        "⚠️ কোনো টিকটক অ্যাকাউন্ট এখনো যুক্ত করা নেই! আগে কানেক্ট করে নাও।"
    )
    return

  status_msg = await message.reply_text(
      f"📥 মিডিয়া ফাইল গ্রহণ করা হয়েছে!\n🎯 টার্গেট: **{target}**\nডাউনলোডিং...",
      parse_mode="Markdown",
  )

  file_size = 0
  file_name = ""

  try:
    if message.video:
      file_size = message.video.file_size
      if file_size and file_size > 20 * 1024 * 1024:
        await status_msg.edit_text(
            f"⚠️ ফাইলের সাইজ {file_size / (1024 * 1024):.1f} MB!\n\nটেলিগ্রাম"
            " বট এপিআই-এর লিমিটের কারণে ২০ MB-র বড় ফাইল সরাসরি নেওয়া যায় না।\n👉"
            " এই ভিডিওটি Google Drive-এ রেখে ড্রাইভ লিংকটি চ্যাটে পাঠিয়ে দাও!"
        )
        return
      media_file = await message.video.get_file(read_timeout=120)
      file_name = f"downloads_{message.video.file_id}.mp4"
    elif message.document:
      file_size = message.document.file_size
      if file_size and file_size > 20 * 1024 * 1024:
        await status_msg.edit_text(
            f"⚠️ ফাইলের সাইজ {file_size / (1024 * 1024):.1f} MB!\n\nটেলিগ্রাম"
            " লিমিট ২০ MB। বড় ফাইল হলে Google Drive-এ আপলোড করে লিংক পাঠিয়ে"
            " দাও।"
        )
        return
      media_file = await message.document.get_file(read_timeout=120)
      ext = (
          os.path.splitext(message.document.file_name)[1]
          if message.document.file_name
          else ".mp4"
      )
      file_name = f"downloads_{message.document.file_id}{ext}"
    else:
      await status_msg.edit_text("⚠️ আনসাপোর্টেড ফরম্যাট!")
      return

    await media_file.download_to_drive(file_name)
    await status_msg.edit_text("⚙️ টিকটকে পাঠানো হচ্ছে...")
    await upload_to_tiktok(file_name, file_size, caption, target, status_msg)
  except Exception as e:
    await status_msg.edit_text(f"ত্রুটি: {str(e)}")
  finally:
    if os.path.exists(file_name):
      os.remove(file_name)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    exit(1)

  threading.Thread(target=run_web, daemon=True).start()

  t_request = HTTPXRequest(
      connection_pool_size=8, read_timeout=120.0, write_timeout=120.0
  )
  app = (
      ApplicationBuilder()
      .token(TELEGRAM_BOT_TOKEN)
      .request(t_request)
      .build()
  )

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
          filters.TEXT
          & ~filters.COMMAND
          & ~filters.Regex(r"^(📱 Account|🚀 Post to All Accounts)"),
          handle_text,
      )
  )
  app.add_handler(
      MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media)
  )

  app.run_polling()
