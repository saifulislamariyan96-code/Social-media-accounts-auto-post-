import static_ffmpeg
static_ffmpeg.add_paths()

import logging
import os
import re
import subprocess
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
from telegram.request import HTTPXRequest

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

web_app = Flask(__name__)


@web_app.route("/")
def home():
  return "AutoPost Bot 1080p60 Engine running 24/7!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  web_app.run(host="0.0.0.0", port=port)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# Buffer Integration Variables (Render Environment থেকে নেবে)
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "")
BUFFER_TIKTOK_PROFILE_ID = os.getenv("BUFFER_TIKTOK_PROFILE_ID", "")

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


def optimize_for_tiktok(input_path: str, output_path: str) -> bool:
  """4K, 120fps বা যেকোনো র ভিডিওকে টিকটকের গোল্ড স্ট্যান্ডার্ড Sweet Spot-এ রূপান্তর করে।

  1080p, 60fps CFR, 14.5 Mbps, H.264 High Profile, AAC 48kHz
  """
  cmd = [
      "ffmpeg",
      "-y",
      "-i",
      input_path,
      "-vf",
      "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
      "-r",
      "60",
      "-c:v",
      "libx264",
      "-preset",
      "fast",
      "-profile:v",
      "high",
      "-level",
      "4.2",
      "-b:v",
      "14500k",
      "-maxrate",
      "15000k",
      "-bufsize",
      "30000k",
      "-c:a",
      "aac",
      "-b:a",
      "192k",
      "-ar",
      "48000",
      "-movflags",
      "+faststart",
      output_path,
  ]

  try:
    logging.info(f"FFmpeg Optimization শুরু হচ্ছে: {input_path}")
    process = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
    )
    return True
  except Exception as e:
    logging.error(f"FFmpeg Error: {str(e)}")
    return False


async def upload_via_buffer(file_path, caption, target, status_msg):
  """Buffer API ব্যবহার করে ক্লাউড-টু-ক্লাউড লসলেস পোস্টিং"""
  try:
    await status_msg.edit_text("🚀 Buffer API দিয়ে টিকটকে পুশ করা হচ্ছে...")

    url = f"https://api.bufferapp.com/1/updates/create.json?access_token={BUFFER_ACCESS_TOKEN}"

    with open(file_path, "rb") as media_file:
      files = {"media[video]": media_file}
      data = {
          "profile_ids[]": BUFFER_TIKTOK_PROFILE_ID,
          "text": caption,
          "now": "true",
      }
      res = requests.post(url, data=data, files=files, timeout=300)

    res_json = res.json()
    if res.status_code == 200 and res_json.get("success"):
      await status_msg.edit_text(
          "🎉 **Buffer এর মাধ্যমে টিকটকে সফলভাবে পোস্ট হয়েছে!**\n\n"
          "🌟 মোড: **Buffer Lossless Cloud Pipeline (1080P 60FPS)**\n"
          f"🎯 টার্গেট: **{target}**\n"
          f"📝 ক্যাপশন: {caption}\n\n"
          "কোনো প্রকার কোয়ালিটি লস ছাড়াই ভিডিও পাবলিশ হয়েছে!",
          parse_mode="Markdown",
      )
    else:
      error_msg = res_json.get("message", str(res_json))
      logging.warning(
          f"Buffer API Error: {error_msg}. Falling back to Direct Post."
      )
      await status_msg.edit_text(
          "⚠️ বাফার এপিআই রেসপন্স দেয়নি। ব্যাকআপ ডিরেক্ট এপিআই দিয়ে চেষ্টা করা"
          " হচ্ছে..."
      )
      file_size = os.path.getsize(file_path)
      await upload_direct_to_tiktok(
          file_path, file_size, caption, target, status_msg
      )
  except Exception as e:
    logging.error(f"Buffer Exception: {str(e)}")
    file_size = os.path.getsize(file_path)
    await upload_direct_to_tiktok(
        file_path, file_size, caption, target, status_msg
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
      "স্বাগতম! 🚀 (FFmpeg 1080P 60FPS Sweet Spot Engine)\n\n"
      f"🎯 **বর্তমান টার্গেট:** `{USER_TARGETS[user_id]}`\n\n"
      "🔹 **ব্যবহারের নিয়ম:**\n"
      "১. ছোট ভিডিও টেলিগ্রামে সরাসরি পাঠাও।\n"
      "২. বড় হাই-বিটরেট গেমিং ক্লিপের জন্য **Google Drive লিংক** পাঠাও।\n"
      "সার্ভার নিজে থেকে ভিডিওকে 1080p 60fps CFR-এ অপটিমাইজ করে পোস্ট করবে!"
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
      "১. নিচে থাকা কিবোর্ড বাটন চেপে অ্যাকাউন্ট সিলেক্ট করো।\n"
      "২. বড় গেমিং ক্লিপ Google Drive-এ দিয়ে লিংক পাঠাও (Anyone with link)।\n"
      "৩. ব্যাকএন্ডে FFmpeg স্বয়ংক্রিয়ভাবে Sweet Spot 1080p 60fps-এ রূপান্তর"
      " করবে।"
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
  buffer_status = (
      "🟢 সক্রিয় আছে" if BUFFER_ACCESS_TOKEN else "⚪ সেট করা নেই (Direct Mode)"
  )
  status_text = (
      "📊 **বট ও সার্ভার স্ট্যাটাস:**\n\n"
      "🟢 সার্ভার: **অনলাইন (২৪/৭ সচল)**\n"
      "⚙️ অপটিমাইজার: **FFmpeg 1080P 60FPS Sweet Spot Engine**\n"
      f"🔑 টিকটক ডিরেক্ট টোকেন: **{token_status}**\n"
      f"📦 বাফার ইন্টিগ্রেশন: **{buffer_status}**\n"
      f"🎯 বর্তমান টার্গেট: **{target}**"
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


async def upload_direct_to_tiktok(
    file_path, file_size, caption, target, status_msg
):
  headers = {
      "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
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

  response = requests.post(init_url, json=payload, headers=headers, timeout=60)
  res_data = response.json()

  if response.status_code == 200 and "data" in res_data:
    upload_url = res_data["data"]["upload_url"]
    publish_id = res_data["data"].get("publish_id", "N/A")

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
          f"🎉 **সরাসরি টিকটকে পোস্ট সম্পন্ন হয়েছে!**\n\n"
          f"🌟 মোড: **Direct 1080P 60FPS (Pre-optimized)**\n"
          f"📊 সাইজ: {file_size_mb:.2f} MB\n"
          f"🆔 Publish ID: `{publish_id}`\n"
          f"🎯 টার্গেট: **{target}**\n"
          f"📝 ক্যাপশন: {caption}\n\n"
          f"প্রি-অপটিমাইজড ফাইলে প্রোফাইলে আপলোড হয়েছে!",
          parse_mode="Markdown",
      )
    else:
      await status_msg.edit_text(
          f"⚠️ বাইট আপলোডে সমস্যা হয়েছে: {upload_res.status_code}"
      )
  else:
    error_info = res_data.get("error", {})
    await status_msg.edit_text(
        f"⚠️ টিকটক এপিআই রেসপন্স:\n{error_info.get('message', 'ত্রুটি')}\n"
        f"কোড: `{error_info.get('code', 'N/A')}`"
    )


def download_gdrive_file(url, destination):
  match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(
      r"id=([a-zA-Z0-9_-]+)", url
  )
  if not match:
    raise Exception("সঠিক Google Drive ফাইল আইডি পাওয়া যায়নি!")

  file_id = match.group(1)
  session = requests.Session()
  download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

  response = session.get(download_url, stream=True, timeout=60)

  for key, value in response.cookies.items():
    if key.startswith("download_warning"):
      download_url = f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}"
      response = session.get(download_url, stream=True, timeout=60)
      break

  if response.status_code != 200:
    raise Exception(
        f"ড্রাইভ থেকে ফাইল ডাউনলোড ব্যর্থ হয়েছে (Status: {response.status_code})।"
        " লিংকটি 'Anyone with the link' নিশ্চিত করো।"
    )

  with open(destination, "wb") as f:
    for chunk in response.iter_content(chunk_size=1024 * 1024 * 4):
      if chunk:
        f.write(chunk)


async def dispatch_upload(file_path, caption, target, status_msg):
  """বাফার টোকেন থাকলে বাফার দিয়ে পোস্ট করবে, না থাকলে ডিরেক্ট টিকটকে"""
  if BUFFER_ACCESS_TOKEN and BUFFER_TIKTOK_PROFILE_ID:
    await upload_via_buffer(file_path, caption, target, status_msg)
  else:
    file_size = os.path.getsize(file_path)
    await upload_direct_to_tiktok(
        file_path, file_size, caption, target, status_msg
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")

  if "drive.google.com" in text:
    if not TIKTOK_ACCESS_TOKEN and not BUFFER_ACCESS_TOKEN:
      await update.message.reply_text(
          "⚠️ কোনো অ্যাকাউন্ট টোকেন সেট করা নেই! আগে কানেক্ট করে নাও।"
      )
      return

    status_msg = await update.message.reply_text(
        "📥 Google Drive লিংক পাওয়া গেছে!\nসার্ভারে ডাউনলোড হচ্ছে..."
    )
    raw_file = f"raw_{user_id}.mp4"
    opt_file = f"opt_{user_id}.mp4"

    try:
      lines = text.split("\n")
      url = lines[0].strip()
      caption = (
          "\n".join(lines[1:])
          if len(lines) > 1
          else "Uploaded via AutoPost Bot 🚀"
      )

      download_gdrive_file(url, raw_file)

      if not os.path.exists(raw_file):
        await status_msg.edit_text("⚠️ ড্রাইভ ফাইল সেভ হতে সমস্যা হয়েছে!")
        return

      await status_msg.edit_text(
          "⚙️ FFmpeg ইঞ্জিন দিয়ে ভিডিওকে Sweet Spot (1080p 60fps CFR) এ"
          " অপটিমাইজ করা হচ্ছে..."
      )

      success = optimize_for_tiktok(raw_file, opt_file)
      final_file = opt_file if success else raw_file

      await dispatch_upload(final_file, caption, target, status_msg)

    except Exception as e:
      await status_msg.edit_text(f"ত্রুটি: {str(e)}")
    finally:
      if os.path.exists(raw_file):
        os.remove(raw_file)
      if os.path.exists(opt_file):
        os.remove(opt_file)


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  user_id = update.effective_user.id
  target = USER_TARGETS.get(user_id, "🚀 Post to All Accounts")
  caption = message.caption or "Uploaded via AutoPost Bot"

  if not TIKTOK_ACCESS_TOKEN and not BUFFER_ACCESS_TOKEN:
    await message.reply_text(
        "⚠️ কোনো অ্যাকাউন্ট টোকেন সেট করা নেই! আগে কানেক্ট করে নাও।"
    )
    return

  status_msg = await message.reply_text(
      f"📥 মিডিয়া ফাইল পাওয়া গেছে!\n🎯 টার্গেট: **{target}**\nডাউনলোড হচ্ছে...",
      parse_mode="Markdown",
  )

  raw_file = ""
  opt_file = f"opt_{message.message_id}.mp4"

  try:
    if message.video:
      file_size = message.video.file_size
      if file_size and file_size > 20 * 1024 * 1024:
        await status_msg.edit_text(
            f"⚠️ ফাইলের সাইজ {file_size / (1024 * 1024):.1f} MB!\n\nটেলিগ্রাম"
            " লিমিট ২০ MB। বড় গেমিং ক্লিপের জন্য Google Drive লিংক পাঠাও।"
        )
        return
      media_file = await message.video.get_file(read_timeout=120)
      raw_file = f"raw_{message.video.file_id}.mp4"
    elif message.document:
      file_size = message.document.file_size
      if file_size and file_size > 20 * 1024 * 1024:
        await status_msg.edit_text(
            f"⚠️ ফাইলের সাইজ {file_size / (1024 * 1024):.1f} MB!\n\nটেলিগ্রাম"
            " লিমিট ২০ MB। বড় ফাইল হলে Google Drive লিংক দাও।"
        )
        return
      media_file = await message.document.get_file(read_timeout=120)
      ext = (
          os.path.splitext(message.document.file_name)[1]
          if message.document.file_name
          else ".mp4"
      )
      raw_file = f"raw_{message.document.file_id}{ext}"
    else:
      await status_msg.edit_text("⚠️ আনসাপোর্টেড ফরম্যাট!")
      return

    await media_file.download_to_drive(raw_file)
    await status_msg.edit_text(
        "⚙️ FFmpeg ইঞ্জিন দিয়ে ভিডিওকে Sweet Spot (1080p 60fps CFR) এ রূপান্তর"
        " করা হচ্ছে..."
    )

    success = optimize_for_tiktok(raw_file, opt_file)
    final_file = opt_file if success else raw_file

    await dispatch_upload(final_file, caption, target, status_msg)

  except Exception as e:
    await status_msg.edit_text(f"ত্রুটি: {str(e)}")
  finally:
    if os.path.exists(raw_file):
      os.remove(raw_file)
    if os.path.exists(opt_file):
      os.remove(opt_file)


if __name__ == "__main__":
  if not TELEGRAM_BOT_TOKEN:
    exit(1)

  threading.Thread(target=run_web, daemon=True).start()

  t_request = HTTPXRequest(
      connection_pool_size=8, read_timeout=120.0, write_timeout=120.0
  )
  app = (
      ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(t_request).build()
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
