import asyncio

# Python 3.12+ ও 3.14 এর জন্য ইভেন্ট লুপ ফিক্স (Pyrogram ক্র্যাশ প্রতিরোধ)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import threading
import requests
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# ----------------- কনফিগারেশন ----------------- #
API_ID_RAW = os.getenv("API_ID", "").strip()
API_ID = int(API_ID_RAW) if API_ID_RAW.isdigit() else 0
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "").strip()

# Render সার্ভার সচল রাখার ফ্লাস্ক সার্ভার
app = Flask(__name__)

@app.route('/')
def home():
    return "Pyrogram Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- Buffer GraphQL API ----------------- #
def post_to_buffer(video_url: str, caption: str = ""):
    endpoint = "https://api.buffer.com/"
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

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

    variables = {
        "input": {
            "channelId": BUFFER_CHANNEL_ID,
            "text": caption if caption else "New Video",
            "mode": "addToQueue",
            "schedulingType": "automatic",
            "assets": [
                {"video": {"url": video_url}}
            ]
        }
    }

    return requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)

# ----------------- Pyrogram ক্লায়েন্ট ----------------- #
bot = Client(
    "auto_post_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    await message.reply_text("👋 স্বাগতম! যেকোনো সাইজের ভিডিও ক্যাপশনসহ এখানে পাঠাও, সরাসরি বাফারে শিডিউল হয়ে যাবে।")

@bot.on_message((filters.video | filters.document) & filters.private)
async def media_handler(client: Client, message: Message):
    if message.document:
        mime = message.document.mime_type or ""
        fname = (message.document.file_name or "").lower()
        if not (mime.startswith("video/") or fname.endswith((".mp4", ".mov", ".mkv", ".avi"))):
            return

    caption = message.caption or ""
    status_msg = await message.reply_text("⏳ ভিডিও পাওয়া গেছে! লিঙ্ক প্রস্তুত হচ্ছে...")

    try:
        target = message.video or message.document
        file_path_url = await client.get_file(target.file_id)
        
        if hasattr(file_path_url, "file_path") and file_path_url.file_path:
            direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path_url.file_path}"
        else:
            direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{target.file_id}"

        await status_msg.edit_text("⏳ Buffer-এ পোস্ট শিডিউল করা হচ্ছে...")
        response = post_to_buffer(direct_file_url, caption)
        
        try:
            res_data = response.json()
        except Exception:
            res_data = {"raw_text": response.text}

        create_post_data = res_data.get("data", {}).get("createPost", {})

        if response.status_code == 200 and "post" in create_post_data:
            await status_msg.edit_text(f"✅ সফলভাবে Buffer-এ শিডিউল করা হয়েছে!\n📌 ক্যাপশন: {caption if caption else 'None'}")
        else:
            errors = res_data.get("errors", [])
            err_msg = errors[0].get("message") if errors else create_post_data.get("message", str(res_data))
            await status_msg.edit_text(f"❌ Buffer আপলোড ব্যর্থ হয়েছে (Code {response.status_code}):\n`{err_msg}`")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ ত্রুটি: {str(e)}")

# ----------------- মেইন রানার ----------------- #
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot is running perfectly on Python 3.14...")
    bot.run()
