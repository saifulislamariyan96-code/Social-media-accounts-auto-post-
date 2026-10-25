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

# ----------------- Buffer GraphQL API ফাংশন ----------------- #
def post_to_buffer(video_url: str, caption: str = ""):
    """Buffer GraphQL API দিয়ে ভিডিও পোস্ট কিউতে পাঠানো"""
    endpoint = "https://api.buffer.com/"
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Buffer GraphQL Mutation
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    # mode ফিল্ড বাধ্যতামূলক যুক্ত করা হয়েছে
    variables = {
        "input": {
            "channelId": BUFFER_CHANNEL_ID,
            "text": caption if caption else "New Video",
            "mode": "addToQueue",
            "assets": [
                {
                    "video": {
                        "url": video_url
                    }
                }
            ]
        }
    }

    return requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)

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
    caption = message.caption or ""

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

    status_msg = await message.reply_text("⏳ ভিডিও পাওয়া গেছে! Buffer-এ পাঠানোর লিঙ্ক প্রস্তুত হচ্ছে...")

    try:
        video_file = await context.bot.get_file(target_obj.file_id)
        
        # ইউআরএল ডুপ্লিকেশন প্রতিরোধ লজিক
        raw_path = video_file.file_path
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            direct_file_url = raw_path
        else:
            direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{raw_path}"

        await status_msg.edit_text("⏳ Buffer GraphQL-এ পোস্ট শিডিউল করা হচ্ছে...")

        response = post_to_buffer(direct_file_url, caption)
        
        try:
            res_data = response.json()
        except Exception:
            res_data = {"raw_text": response.text}

        # GraphQL রেসপন্স যাচাই
        create_post_data = res_data.get("data", {}).get("createPost", {})
        
        if response.status_code == 200 and "post" in create_post_data:
            await status_msg.edit_text(
                f"✅ *সফলভাবে Buffer-এ শিডিউল করা হয়েছে!*\n📌 ক্যাপশন: {caption if caption else 'None'}",
                parse_mode="Markdown"
            )
        else:
            errors = res_data.get("errors", [])
            if errors and isinstance(errors, list):
                err_msg = errors[0].get("message", str(errors[0]))
            elif "message" in create_post_data:
                err_msg = create_post_data["message"]
            else:
                err_msg = str(res_data)

            await status_msg.edit_text(
                f"❌ Buffer আপলোড ব্যর্থ হয়েছে (Code {response.status_code}):\n`{err_msg}`", 
                parse_mode="Markdown"
            )

    except Exception as e:
        await status_msg.edit_text(f"⚠️ কোনো একটি সমস্যা হয়েছে: {str(e)}")

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
