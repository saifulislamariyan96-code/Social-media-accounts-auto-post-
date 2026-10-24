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

    welcome_text = (
        "👋 **স্বাগতম!**\n\n"
        "📹 **ভিডিও পোস্ট করার নিয়ম:**\n"
        "1. নিচের বাটনে চাপ দিয়ে CompressBase থেকে ভিডিওটি দ্রুত অপটিমাইজ করে নাও।\n"
        "2. অপটিমাইজ করা ভিডিওটি এখানে পাঠাও (সাথে ক্যাপশন থাকলে
