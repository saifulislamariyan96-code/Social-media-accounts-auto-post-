import asyncio

# Python 3.14 ইভেন্ট লুপ ফিক্স
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import time
import uuid
import threading
from datetime import datetime
import pytz
import dateparser
import requests
from flask import Flask, send_from_directory
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- কনফিগারেশন ----------------- #
API_ID_RAW = os.getenv("API_ID", "").strip()
API_ID = int(API_ID_RAW) if API_ID_RAW.isdigit() else 0
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "").strip()

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://social-media-accounts-auto-post-l13g.onrender.com").rstrip("/")
TEMP_DOWNLOAD_DIR = "/tmp/buffer_videos"
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# পোস্ট সেশন এবং ইউজারের শিডিউল ইনপুট ট্র্যাক রাখার ডিকশনারি
PENDING_POSTS = {}
AWAITING_TIME_INPUT = {}

# ----------------- Flask সার্ভার ----------------- #
app = Flask(__name__)

@app.route('/')
def home():
    return "TikTok Schedule & Post Bot is Live!"

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(TEMP_DOWNLOAD_DIR, filename)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def delayed_delete(file_path, delay=180):
    time.sleep(delay)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Cleaned up: {file_path}")
        except Exception:
            pass

# ----------------- Buffer GraphQL API ----------------- #
def post_to_buffer(video_url: str, caption: str, settings: dict):
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

    tiktok_payload = {
        "privacy": settings.get("privacy", "PUBLIC"),
        "allowComments": settings.get("allow_comments", True),
        "allowDuet": settings.get("allow_duet", True),
        "allowStitch": settings.get("allow_stitch", True)
    }

    mode = settings.get("mode", "shareNow")
    due_at = settings.get("due_at")

    input_data = {
        "channelId": BUFFER_CHANNEL_ID,
        "text": caption if caption else "New Video",
        "mode": mode,
        "assets": [
            {"video": {"url": video_url}}
        ],
        "channelServiceSpecificData": {
            "tiktok": tiktok_payload
        }
    }

    if mode == "customSchedule" and due_at:
        input_data["schedulingType"] = "custom"
        input_data["dueAt"] = due_at
    else:
        input_data["schedulingType"] = "automatic"

    variables = {"input": input_data}
    return requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)

# ----------------- বাটন কিবোর্ড বিল্ডার ----------------- #
def build_settings_keyboard(post_id: str):
    data = PENDING_POSTS.get(post_id, {})
    priv = data.get("privacy", "PUBLIC")
    comm = "✅ On" if data.get("allow_comments", True) else "🚫 Off"
    duet = "✅ Allow" if data.get("allow_duet", True) else "🚫 Off"
    stitch = "✅ Allow" if data.get("allow_stitch", True) else "🚫 Off"
    
    mode = data.get("mode", "shareNow")
    if mode == "shareNow":
        mode_btn = "🚀 Mode: Share Now"
    elif mode == "addToQueue":
        mode_btn = "📥 Mode: Queue"
    else:
        time_text = data.get("schedule_display", "Set Time")
        mode_btn = f"📅 Schedule: {time_text}"

    priv_display = {
        "PUBLIC": "🌐 Public",
        "MUTUAL_FOLLOW_FRIENDS": "👥 Friends",
        "SELF_ONLY": "🔒 Private"
    }.get(priv, "🌐 Public")

    keyboard = [
        [
            InlineKeyboardButton(f"Privacy: {priv_display}", callback_data=f"toggle_priv:{post_id}"),
            InlineKeyboardButton(f"Comments: {comm}", callback_data=f"toggle_comm:{post_id}")
        ],
        [
            InlineKeyboardButton(f"Duet: {duet}", callback_data=f"toggle_duet:{post_id}"),
            InlineKeyboardButton(f"Stitch: {stitch}", callback_data=f"toggle_stitch:{post_id}")
        ],
        [
            InlineKeyboardButton(mode_btn, callback_data=f"toggle_mode:{post_id}")
        ],
        [
            InlineKeyboardButton("🚀 Confirm & Post to TikTok", callback_data=f"submit:{post_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

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
    await message.reply_text(
        "👋 **TikTok Auto-Post Assistant-এ স্বাগতম!**\n\n"
        "ভিডিও ক্যাপশনসহ ড্রপ করো। বাটন চেপে সরাসরি পোস্ট বা সহজ টাইমে (যেমন: `8:30 pm`) শিডিউল করতে পারবে।"
    )

# ভিডিও হ্যান্ডলার
@bot.on_message((filters.video | filters.document) & filters.private)
async def media_handler(client: Client, message: Message):
    if message.document:
        mime = message.document.mime_type or ""
        fname = (message.document.file_name or "").lower()
        if not (mime.startswith("video/") or fname.endswith((".mp4", ".mov", ".mkv", ".avi"))):
            return

    status_msg = await message.reply_text("⏳ ভিডিও ডাউনলোড ও লিঙ্ক তৈরি হচ্ছে...")

    post_id = uuid.uuid4().hex[:8]
    filename = f"vid_{post_id}.mp4"
    local_path = os.path.join(TEMP_DOWNLOAD_DIR, filename)

    try:
        await message.download(file_name=local_path)
        public_url = f"{RENDER_EXTERNAL_URL}/files/{filename}"

        PENDING_POSTS[post_id] = {
            "video_url": public_url,
            "local_path": local_path,
            "caption": message.caption or "",
            "privacy": "PUBLIC",
            "allow_comments": True,
            "allow_duet": True,
            "allow_stitch": True,
            "mode": "shareNow",
            "due_at": None,
            "schedule_display": None,
            "message_id": status_msg.id,
            "chat_id": message.chat.id
        }

        cap_preview = message.caption if message.caption else "None"
        dashboard_text = (
            f"🎬 **ভিডিও প্রস্তুত! টিকটক সেটিংস নির্বাচন করো:**\n\n"
            f"📌 **ক্যাপশন:** `{cap_preview}`\n"
            f"⚙️ নিচের বাটনগুলোতে ট্যাপ করে সেটিংস পরিবর্তন করো:"
        )

        await status_msg.edit_text(
            dashboard_text,
            reply_markup=build_settings_keyboard(post_id)
        )

    except Exception as e:
        if os.path.exists(local_path):
            os.remove(local_path)
        await status_msg.edit_text(f"⚠️ ভিডিও ডাউনলোডে ত্রুটি: {str(e)}")

# টেক্সট মেসেজ হ্যান্ডলার (সহজ টাইম ইনপুট নেওয়ার জন্য)
@bot.on_message(filters.text & filters.private & ~filters.command(["start"]))
async def text_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in AWAITING_TIME_INPUT:
        post_id = AWAITING_TIME_INPUT.pop(user_id)
        if post_id not in PENDING_POSTS:
            await message.reply_text("⚠️ সেশনের সময় শেষ হয়ে গেছে! নতুন করে ভিডিও পাঠাও।")
            return

        raw_time = message.text.strip()
        # বাংলাদেশ টাইমজোন অনুযায়ী স্বাভাবিক ভাষা থেকে টাইম পার্স করা
        local_tz = pytz.timezone("Asia/Dhaka")
        parsed_time = dateparser.parse(
            raw_time,
            settings={
                'TIMEZONE': 'Asia/Dhaka',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DATES_FROM': 'future'
            }
        )

        if not parsed_time:
            AWAITING_TIME_INPUT[user_id] = post_id
            await message.reply_text(
                "❌ সময়টি ঠিকমতো বোঝা যায়নি!\n"
                "দয়া করে এভাবে লেখো: `8:30 pm` অথবা `tomorrow 10:00 am`"
            )
            return

        # বাফার চায় UTC ISO 8601 ফরম্যাট (Z যুক্ত)
        utc_time = parsed_time.astimezone(pytz.utc)
        iso_time = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # ব্যবহারকারীকে দেখানোর জন্য সহজ সময়
        display_str = parsed_time.strftime("%d %b, %I:%M %p")

        PENDING_POSTS[post_id]["mode"] = "customSchedule"
        PENDING_POSTS[post_id]["due_at"] = iso_time
        PENDING_POSTS[post_id]["schedule_display"] = display_str

        chat_id = PENDING_POSTS[post_id]["chat_id"]
        msg_id = PENDING_POSTS[post_id]["message_id"]

        await message.reply_text(f"🕒 শিডিউল টাইম সেট করা হয়েছে: **{display_str}**")
        await client.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=build_settings_keyboard(post_id)
        )

# বাটন ক্লিক হ্যান্ডলার
@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    action, post_id = data.split(":")

    if post_id not in PENDING_POSTS:
        await query.answer("⚠️ সেশনটির মেয়াদ শেষ!", show_alert=True)
        return

    post_config = PENDING_POSTS[post_id]

    if action == "toggle_priv":
        levels = ["PUBLIC", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"]
        cur_idx = levels.index(post_config.get("privacy", "PUBLIC"))
        post_config["privacy"] = levels[(cur_idx + 1) % len(levels)]
        await query.answer()
        await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))

    elif action == "toggle_comm":
        post_config["allow_comments"] = not post_config.get("allow_comments", True)
        await query.answer()
        await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))

    elif action == "toggle_duet":
        post_config["allow_duet"] = not post_config.get("allow_duet", True)
        await query.answer()
        await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))

    elif action == "toggle_stitch":
        post_config["allow_stitch"] = not post_config.get("allow_stitch", True)
        await query.answer()
        await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))

    elif action == "toggle_mode":
        # সাইকেল: shareNow -> addToQueue -> customSchedule
        cur = post_config.get("mode", "shareNow")
        if cur == "shareNow":
            post_config["mode"] = "addToQueue"
            await query.answer("Mode: Add to Queue")
            await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))
        elif cur == "addToQueue":
            # কাস্টম শিডিউলের জন্য টেক্সট ইনপুট চাওয়া
            AWAITING_TIME_INPUT[query.from_user.id] = post_id
            await query.answer()
            await query.message.reply_text(
                "🕒 **কখন পোস্ট করতে চাও?**\n\n"
                "সহজ ভাষায় চ্যাটে সময়টি লিখে পাঠাও। যেমন:\n"
                "• `8:30 pm` (আজকের জন্য)\n"
                "• `tomorrow 9:00 pm` (আগামীকালের জন্য)\n"
                "• `12 Nov 4:30 pm`"
            )
        else:
            post_config["mode"] = "shareNow"
            post_config["due_at"] = None
            post_config["schedule_display"] = None
            await query.answer("Mode: Share Now")
            await query.message.edit_reply_markup(reply_markup=build_settings_keyboard(post_id))

    elif action == "submit":
        if post_config["mode"] == "customSchedule" and not post_config.get("due_at"):
            await query.answer("⚠️ আগে শিডিউল টাইম লিখে পাঠাও!", show_alert=True)
            return

        await query.answer("🚀 Buffer-এ পাঠানো হচ্ছে...")
        await query.message.edit_text("⏳ টিকটকে পাঠানোর কাজ চলছে, অনুগ্রহ করে অপেক্ষা করো...")

        resp = post_to_buffer(
            video_url=post_config["video_url"],
            caption=post_config["caption"],
            settings=post_config
        )

        try:
            res_data = resp.json()
        except Exception:
            res_data = {"raw_text": resp.text}

        create_post_data = res_data.get("data", {}).get("createPost", {})

        if resp.status_code == 200 and "post" in create_post_data:
            mode = post_config["mode"]
            if mode == "shareNow":
                mode_str = "🚀 সরাসরি পোস্ট (Share Now)"
            elif mode == "addToQueue":
                mode_str = "📥 কিউতে জমা রাখা হয়েছে"
            else:
                mode_str = f"📅 শিডিউল করা হয়েছে ({post_config['schedule_display']})"

            success_msg = (
                f"✅ **সফলভাবে সম্পন্ন হয়েছে!**\n\n"
                f"📌 **অ্যাকশন:** {mode_str}\n"
                f"🔒 **প্রাইভেসি:** {post_config['privacy']}\n"
                f"💬 **কমেন্ট:** {'চালু' if post_config['allow_comments'] else 'বন্ধ'}\n"
                f"📝 **ক্যাপশন:** {post_config['caption'] if post_config['caption'] else 'None'}"
            )
            await query.message.edit_text(success_msg)
            threading.Thread(target=delayed_delete, args=(post_config["local_path"], 180), daemon=True).start()
        else:
            errors = res_data.get("errors", [])
            err_msg = errors[0].get("message") if errors else create_post_data.get("message", str(res_data))
            await query.message.edit_text(f"❌ ব্যর্থ হয়েছে:\n`{err_msg}`")
            if os.path.exists(post_config["local_path"]):
                os.remove(post_config["local_path"])

        PENDING_POSTS.pop(post_id, None)

# ----------------- রানার ----------------- #
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot with Easy Time Scheduling is running...")
    bot.run()
