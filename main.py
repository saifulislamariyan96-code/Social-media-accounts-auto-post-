import os
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- কনফিগারেশন ----------------- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")

# Render-এর ফ্রি সার্ভার বাঁচিয়ে রাখার জন্য ডামি Flask সার্ভার
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- Buffer API ফাংশন ----------------- #
def post_to_buffer(video_url: str, caption: str = ""):
    """Buffer API-তে ভিডিও ও টেক্সট পাঠিয়ে শিডিউল করা"""
    endpoint = "https://api.bufferapp.com/1/updates/create.json"
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}"
    }
    data = {
        "profile_ids[]": BUFFER_CHANNEL_ID,
        "text": caption if caption else "New Video",
        "now": False,  # সাথে সাথে পোস্ট করতে True, কিউতে রাখতে False
        "media[video]": video_url
    }
    return requests.post(endpoint, headers=headers, data=data)

# ----------------- /start কমান্ড ----------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "⚡ Fast Optimize (CompressBase)", 
                url="https://compressbase.com/upload-method"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = """👋 *স্বাগতম!*

📹 *ভিডিও পোস্ট করার নিয়ম:*
1. নিচের বাটনে চাপ দিয়ে CompressBase থেকে ভিডিওটি দ্রুত অপটিমাইজ করে নাও।
2. অপটিমাইজ করা ভিডিওটি এখানে পাঠাও (সাথে ক্যাপশন থাকলে লিখে দাও)।
3. বট স্বয়ংক্রিয়ভাবে ভিডিওটি Buffer-এর মাধ্যমে তোমার একাউন্টে শিডিউল করে দেবে!"""

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------- /help কমান্ড ----------------- #
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """ℹ️ *কীভাবে ব্যবহার করবেন?*

1. প্রথমে CompressBase দিয়ে ভিডিও সাইজ অপটিমাইজ করুন।
2. এরপর অপটিমাইজ করা ভিডিওটি এই বটে সেন্ড করুন।
3. ক্যাপশন দিতে চাইলে ভিডিওর সাথেই লিখে দিন।
4. বট স্বয়ংক্রিয়ভাবে Buffer-এ শিডিউল করে দেবে।"""

    await update.message.reply_text(help_text, parse_mode="Markdown")

# ----------------- ভিডিও রিসিভ হ্যান্ডলার ----------------- #
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    status_msg = await message.reply_text("⏳ ভিডিও প্রসেস হচ্ছে, Buffer-এ পাঠানো শুরু করছি...")

    try:
        # ভিডিও বা ডকুমেন্টের ফাইল ও ক্যাপশন রিট্রিভ করা
        if message.video:
            video_file = await message.video.get_file()
            caption = message.caption or ""
        elif message.document and message.document.mime_type.startswith("video/"):
            video_file = await message.document.get_file()
            caption = message.caption or ""
        else:
            await status_msg.edit_text("⚠️ অনুগ্রহ করে একটি ভিডিও ফাইল পাঠান।")
            return

        # টেলিগ্রাম থেকে সরাসরি ভিডিও ফাইল লিংক নেওয়া
        direct_file_url = video_file.file_path

        # বাফারে পাঠানো
        response = post_to_buffer(direct_file_url, caption)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("success"):
            await status_msg.edit_text(
                f"✅ *সফলভাবে Buffer-এ শিডিউল করা হয়েছে!*\n📌 ক্যাপশন: {caption if caption else 'None'}",
                parse_mode="Markdown"
            )
        else:
            err_msg = res_data.get("message", "অজানা ত্রুটি ঘটেছে।")
            await status_msg.edit_text(f"❌ Buffer আপলোড ব্যর্থ হয়েছে:\n`{err_msg}`", parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ কোনো একটি সমস্যা হয়েছে: {str(e)}")

# ----------------- মেইন রানার ----------------- #
def main():
    # ব্যাকগ্রাউন্ডে Flask সার্ভার চালু
    threading.Thread(target=run_flask, daemon=True).start()

    # টেলিগ্রাম বট অ্যাপ্লিকেশন
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VIDEO | (filters.Document.ALL & filters.Document.MimeType("video/")), handle_video))

    print("Bot is polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
