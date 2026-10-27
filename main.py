import os
import threading
import requests
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- কনফিগারেশন ----------------- #
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")

# Render ওয়েব সার্ভিস সচল রাখার জন্য Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Pyrogram Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ----------------- Buffer GraphQL ফাংশন ----------------- #
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
                {
                    "video": {
                        "url": video_url
                    }
                }
            ]
        }
    }

    return requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)

# ----------------- Pyrogram ক্লায়েন্ট ইনিশিয়ালাইজ ----------------- #
bot = Client(
    "auto_post_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ----------------- /start কমান্ড ----------------- #
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ CompressBase", url="https://compressbase.com/upload-method")]
    ])
    
    welcome_text = (
        "👋 **স্বাগতম!**\n\n"
        "এই বটে তুমি যেকোনো সাইজের ভিডিও সরাসরি পাঠাতে পারবে (কোনো ২০ MB লিমিট নেই)।\n"
        "ভিডিওর সাথে ক্যাপশন থাকলে তা পোস্টে যুক্ত হবে এবং সরাসরি Buffer কিউতে শিডিউল হয়ে যাবে!"
    )
    await message.reply_text(welcome_text, reply_markup=keyboard)

# ----------------- ভিডিও ও ডকুমেন্ট হ্যান্ডলার ----------------- #
@bot.on_message((filters.video | filters.document) & filters.private)
async def media_handler(client: Client, message: Message):
    # ডকুমেন্ট ফাইল হলে সেটি ভিডিও কিনা যাচাই
    if message.document:
        mime = message.document.mime_type or ""
        fname = (message.document.file_name or "").lower()
        if not (mime.startswith("video/") or fname.endswith((".mp4", ".mov", ".mkv", ".avi"))):
            return

    caption = message.caption or ""
    status_msg = await message.reply_text("⏳ ভিডিও পাওয়া গেছে! প্রসেস করা হচ্ছে...")

    try:
        # Pyrogram ফাইল অবজেক্ট থেকে সরাসরি ডাউনলোড লিঙ্ক বা পাথ নেওয়া
        # ছোট ও বড় সব ফাইলের জন্য অফিসিয়াল ফাইল লিঙ্ক ফেচ
        file_id = message.video.file_id if message.video else message.document.file_id
        file_obj = await client.get_file(file_id)

        # ডিরেক্ট URL প্রস্তুতকরণ
        if hasattr(file_obj, "file_path") and file_obj.file_path:
            direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_obj.file_path}"
        else:
            # বড় ফাইলের ক্ষেত্রে এক্সপোর্ট লিংক মেকানিজম
            direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}"

        await status_msg.edit_text("⏳ Buffer GraphQL-এ পোস্ট শিডিউল করা হচ্ছে...")

        response = post_to_buffer(direct_file_url, caption)
        
        try:
            res_data = response.json()
        except Exception:
            res_data = {"raw_text": response.text}

        create_post_data = res_data.get("data", {}).get("createPost", {})

        if response.status_code == 200 and "post" in create_post_data:
            await status_msg.edit_text(
                f"✅ **সফলভাবে Buffer-এ শিডিউল করা হয়েছে!**\n📌 ক্যাপশন: {caption if caption else 'None'}"
            )
        else:
            errors = res_data.get("errors", [])
            if errors and isinstance(errors, list):
                err_msg = errors[0].get("message", str(errors[0]))
            elif "message" in create_post_data:
                err_msg = create_post_data["message"]
            else:
                err_msg = str(res_data)

            await status_msg.edit_text(f"❌ Buffer আপলোড ব্যর্থ হয়েছে (Code {response.status_code}):\n`{err_msg}`")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ ত্রুটি: {str(e)}")

# ----------------- রানার ----------------- #
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot started via Pyrogram...")
    bot.run()
