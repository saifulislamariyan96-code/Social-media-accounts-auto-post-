import logging
import os
import re
import subprocess
import threading
from flask import Flask
import requests
import imageio_ffmpeg
from telegram import Update
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

def optimize_for_tiktok(input_path: str, output_path: str) -> bool:
    """4K/র ভিডিওকে টিকটকের গোল্ড স্ট্যান্ডার্ড Sweet Spot-এ রূপান্তর করে"""
    try:
        # imageio-ffmpeg থেকে সরাসরি FFmpeg এক্সিকিউটেবলের পাথ নেওয়া
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        cmd = [
            ffmpeg_exe, "-y",
            "-i", input_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-r", "60",
            "-c:v", "libx264",
            "-preset", "fast",
            "-profile:v", "high",
            "-level", "4.2",
            "-b:v", "14500k",
            "-maxrate", "15000k",
            "-bufsize", "30000k",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            output_path,
        ]

        logging.info(f"FFmpeg Optimization শুরু হচ্ছে: {input_path}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        return True
    except Exception as e:
        err = e.stderr.decode("utf-8", errors="ignore") if hasattr(e, "stderr") and e.stderr else str(e)
        logging.error(f"FFmpeg Error: {err}")
        return False

def download_gdrive_file(url, destination):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
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
        raise Exception(f"ড্রাইভ ডাউনলোড ব্যর্থ হয়েছে (Status: {response.status_code})।")

    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024 * 4):
            if chunk:
                f.write(chunk)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **1080p 60fps Optimizer Bot সচল আছে!**\n\n"
        "ভিডিও সরাসরি পাঠাও অথবা Google Drive লিংক দাও।\n"
        "বট Sweet Spot-এ রেন্ডার করে তোমাকে ফেরত পাঠাবে।"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if "drive.google.com" in text:
        status_msg = await update.message.reply_text("📥 Google Drive থেকে কাঁচা ভিডিও ডাউনলোড হচ্ছে...")
        raw_file = f"raw_{user_id}.mp4"
        opt_file = f"opt_{user_id}.mp4"

        try:
            url = text.split("\n")[0].strip()
            download_gdrive_file(url, raw_file)

            raw_size = os.path.getsize(raw_file) / (1024 * 1024)
            await status_msg.edit_text(f"⚙️ {raw_size:.1f} MB ফাইল ডাউনলোড হয়েছে।\nFFmpeg দিয়ে 1080p 60fps CFR-এ এনকোড করা হচ্ছে...")

            success = optimize_for_tiktok(raw_file, opt_file)
            if not success or not os.path.exists(opt_file):
                await status_msg.edit_text("❌ অপটিমাইজেশন ব্যর্থ হয়েছে! সার্ভার লগ চেক করতে হবে।")
                return

            opt_size = os.path.getsize(opt_file) / (1024 * 1024)
            await status_msg.edit_text(f"✅ রেন্ডার সম্পন্ন ({opt_size:.1f} MB)!\nটেলিগ্রামে পাঠানো হচ্ছে...")

            with open(opt_file, "rb") as video_to_send:
                await update.message.reply_video(
                    video=video_to_send,
                    caption=f"🎯 **Sweet Spot Optimized Video**\n📐 রেজোলিউশন: 1080x1920\n🎞️ ফ্রেমরেট: 60 FPS (CFR)\n📊 সাইজ: {opt_size:.1f} MB",
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300,
                )
            await status_msg.delete()

        except Exception as e:
            await status_msg.edit_text(f"ত্রুটি: {str(e)}")
        finally:
            if os.path.exists(raw_file): os.remove(raw_file)
            if os.path.exists(opt_file): os.remove(opt_file)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    status_msg = await message.reply_text("📥 ভিডিও গ্রহণ করা হয়েছে, ডাউনলোড হচ্ছে...")
    raw_file = f"raw_{message.message_id}.mp4"
    opt_file = f"opt_{message.message_id}.mp4"

    try:
        if message.video:
            media_file = await message.video.get_file(read_timeout=120)
        elif message.document:
            media_file = await message.document.get_file(read_timeout=120)
        else:
            await status_msg.edit_text("⚠️ আনসাপোর্টেড ফরম্যাট!")
            return

        await media_file.download_to_drive(raw_file)
        await status_msg.edit_text("⚙️ FFmpeg ইঞ্জিন দিয়ে Sweet Spot (1080p 60fps CFR)-এ রেন্ডার হচ্ছে...")

        success = optimize_for_tiktok(raw_file, opt_file)
        if not success or not os.path.exists(opt_file):
            await status_msg.edit_text("❌ অপটিমাইজেশন ব্যর্থ হয়েছে!")
            return

        opt_size = os.path.getsize(opt_file) / (1024 * 1024)
        await status_msg.edit_text(f"✅ রেন্ডার সম্পন্ন ({opt_size:.1f} MB)!\nটেলিগ্রামে পাঠানো হচ্ছে...")

        with open(opt_file, "rb") as video_to_send:
            await update.message.reply_video(
                video=video_to_send,
                caption=f"🎯 **Sweet Spot Optimized Video**\n📐 1080x1920\n🎞️ 60 FPS CFR\n📊 সাইজ: {opt_size:.1f} MB",
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300,
            )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"ত্রুটি: {str(e)}")
    finally:
        if os.path.exists(raw_file): os.remove(raw_file)
        if os.path.exists(opt_file): os.remove(opt_file)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        exit(1)

    threading.Thread(target=run_web, daemon=True).start()

    t_request = HTTPXRequest(connection_pool_size=8, read_timeout=180.0, write_timeout=300.0)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(t_request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()
