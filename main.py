import asyncio
import logging
import os
import re
import subprocess
import threading
from flask import Flask
import gdown
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
    return "AutoPost Bot 1080p60 Low-RAM Engine running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def run_ffmpeg_encode(input_path: str, output_path: str) -> bool:
    """Render Free Tier (512MB RAM) এর জন্য আল্ট্রা লাইটওয়েট অপটিমাইজেশন"""
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        vf_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(1080-iw)/2:(1920-ih)/2:black,format=yuv420p"
        
        cmd = [
            ffmpeg_exe, "-y",
            "-threads", "1",
            "-i", input_path,
            "-vf", vf_filter,
            "-r", "60",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-maxrate", "12000k",
            "-bufsize", "4000k",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            output_path,
        ]

        logging.info(f"FFmpeg (Low-RAM) শুরু হচ্ছে: {input_path}")
        # বড় ফাইলের রেন্ডারিংয়ের জন্য টাইমআউট বাড়িয়ে ৬০০ সেকেন্ড (১০ মিনিট) করা হলো
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600
        )
        
        if process.returncode == 0 and os.path.exists(output_path):
            logging.info("FFmpeg এনকোডিং সফলভাবে সম্পন্ন!")
            return True
        else:
            err_msg = process.stderr.decode("utf-8", errors="ignore")
            logging.error(f"FFmpeg Error Log: {err_msg}")
            return False

    except Exception as e:
        logging.error(f"FFmpeg Exception: {str(e)}")
        return False

async def optimize_video_async(input_path: str, output_path: str) -> bool:
    return await asyncio.to_thread(run_ffmpeg_encode, input_path, output_path)

def download_gdrive_file(url, destination):
    """gdown ব্যবহার করে 100MB+ বড় ফাইলের ভাইরাস স্ক্যান ওয়ার্নিং বাইপাস করে ডাউনলোড"""
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
    if not match:
        raise Exception("সঠিক Google Drive ফাইল আইডি পাওয়া যায়নি!")

    file_id = match.group(1)
    download_url = f"https://drive.google.com/uc?id={file_id}"
    
    output = gdown.download(download_url, destination, quiet=False)
    if not output or not os.path.exists(destination) or os.path.getsize(destination) < 1000:
        raise Exception("ড্রাইভ থেকে ফাইল ডাউনলোড ব্যর্থ হয়েছে! ফাইল অ্যাক্সেস 'Anyone with the link' আছে কি না চেক করো।")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **1080p 60fps Optimizer Bot সচল আছে!**\n\n"
        "ভিডিও পাঠাও অথবা Google Drive লিংক দাও।"
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
            await status_msg.edit_text(f"⚙️ {raw_size:.1f} MB ডাউনলোড সম্পন্ন।\nSweet Spot (1080p 60fps) এ এনকোড হচ্ছে...")

            success = await optimize_video_async(raw_file, opt_file)
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
                    read_timeout=600,
                    write_timeout=600,
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
        await status_msg.edit_text("⚙️ Sweet Spot (1080p 60fps CFR)-এ রেন্ডার হচ্ছে...")

        success = await optimize_video_async(raw_file, opt_file)
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
                read_timeout=600,
                write_timeout=600,
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

    t_request = HTTPXRequest(connection_pool_size=8, read_timeout=300.0, write_timeout=600.0)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(t_request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()
