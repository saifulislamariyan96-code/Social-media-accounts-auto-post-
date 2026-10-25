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

# Render-এর ফ্রি সার্ভার বাঁচিয়ে রাখার জন্য Flask সার্ভার
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- Buffer স্কিমা ও পোস্ট ফাংশন ----------------- #
def inspect_buffer_schema():
    """Buffer GraphQL থেকে AssetInput ও CreatePostInput-এর সঠিক ফিল্ডের নাম জানা"""
    endpoint = "https://api.buffer.com/"
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    query = """
    query GetSchemaInfo {
      assetInput: __type(name: "AssetInput") {
        inputFields {
          name
          type { name kind ofType { name kind } }
        }
      }
      createPostInput: __type(name: "CreatePostInput") {
        inputFields {
          name
        }
      }
    }
    """
    try:
        res = requests.post(endpoint, json={"query": query}, headers=headers)
        data = res.json()
        asset_fields = [f["name"] for f in data.get("data", {}).get("assetInput", {}).get("inputFields", [])]
        post_fields = [f["name"] for f in data.get("data", {}).get("createPostInput", {}).get("inputFields", [])]
        return f"AssetInput fields: {asset_fields}\nCreatePostInput fields: {post_fields}"
    except Exception as e:
        return f"Schema inspection error: {str(e)}"

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

# ----------------- ভিডিও ও ডকুমেন্ট রিসিভ হ্যান্ডলার ----------------- #
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    target_obj = None
    if message.video:
        target_obj = message.video
    elif message.document:
        doc_name = (message.document.file_name or "").lower()
        mime_type = (message.document.mime_type or "").lower()
        if mime_type.startswith("video/") or doc_name.endswith((".mp4", ".mov", ".mkv", ".avi")):
            target_obj = message.document

    if not target_obj:
        await message.reply_text("⚠️ অনুগ্রহ করে একটি ভিডিও ফাইল পাঠান।")
        return

    status_msg = await message.reply_text("🔍 Buffer API-এর সঠিক ফিল্ড স্কিমা যাচাই করা হচ্ছে...")

    try:
        # Buffer-এর আসল ফিল্ডগুলো স্ক্যান করে আনা
        schema_info = inspect_buffer_schema()
        await status_msg.edit_text(f"📋 *Buffer GraphQL ফিল্ড লিস্ট:*\n```\n{schema_info}\n```", parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"⚠️ ত্রুটি: {str(e)}")

# ----------------- মেইন রানার ----------------- #
def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))

    print("Bot is polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
