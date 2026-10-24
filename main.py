import os
import requests
import telebot
from telebot import types

# ----------------- কনফিগারেশন ----------------- #
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "YOUR_BUFFER_API_KEY")
BUFFER_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID", "YOUR_BUFFER_CHANNEL_ID")

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------- মেনু ও স্টার্ট কমান্ড ----------------- #
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # CompressBase ওপেন করার বাটন
    compress_btn = types.InlineKeyboardButton(
        text="⚡ Fast Optimize (CompressBase)",
        url="https://compressbase.com/upload-method"
    )
    markup.add(compress_btn)

    welcome_text = (
        "👋 **স্বাগতম!**\n\n"
        "📹 **ভিডিও পোস্ট করার সহজ উপায়:**\n"
        "1. নিচের বাটনে চাপ দিয়ে CompressBase থেকে ভিডিওটি দ্রুত অপটিমাইজ করে নাও।\n"
        "2. অপটিমাইজ করা ভিডিওটি এখানে পাঠাও (ক্যাপশন থাকলে সাথে লিখে দাও)।\n"
        "3. বাকি কাজ বট নিজে করে Buffer-এর মাধ্যমে স্বয়ংক্রিয়ভাবে শিডিউল করে দেবে!"
    )
    bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ----------------- Buffer API আপলোড ফাংশন ----------------- #
def post_to_buffer(video_url, caption=""):
    """Buffer API-তে ভিডিও ও টেক্সট পাঠিয়ে শিডিউল করা"""
    endpoint = "https://api.bufferapp.com/1/updates/create.json"
    
    headers = {
        "Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}"
    }
    
    data = {
        "profile_ids[]": BUFFER_CHANNEL_ID,
        "text": caption if caption else "New Video",
        "now": False, # সাথে সাথে পোস্ট করতে চাইলে True, কিউতে রাখতে False
        "media[video]": video_url
    }
    
    response = requests.post(endpoint, headers=headers, data=data)
    return response

# ----------------- ভিডিও রিসিভ হ্যান্ডলার ----------------- #
@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    try:
        status_msg = bot.reply_to(message, "⏳ ভিডিও প্রসেস হচ্ছে, Buffer-এ পাঠানো শুরু করছি...")
        
        # ভিডিও অথবা ডকুমেন্ট থেকে ফাইল আইডি নেওয়া
        if message.content_type == 'video':
            file_id = message.video.file_id
            caption = message.caption or ""
        else:
            if not message.document.mime_type.startswith('video/'):
                bot.edit_message_text("⚠️ অনুগ্রহ করে একটি ভিডিও ফাইল পাঠান।", chat_id=message.chat.id, message_id=status_msg.message_id)
                return
            file_id = message.document.file_id
            caption = message.caption or ""

        # টেলিগ্রামের ডিরেক্ট ফাইল ডাউনলোড লিংক তৈরি
        file_info = bot.get_file(file_id)
        direct_file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        # বাফারে পাঠানো
        response = post_to_buffer(direct_file_url, caption)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("success"):
            bot.edit_message_text(
                "✅ **সফলভাবে Buffer-এ শিডিউল করা হয়েছে!**\n"
                f"📌 ক্যাপশন: {caption if caption else 'None'}",
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                parse_mode="Markdown"
            )
        else:
            err_msg = res_data.get("message", "অজানা কোনো ত্রুটি ঘটেছে।")
            bot.edit_message_text(f"❌ Buffer আপলোড ব্যর্থ হয়েছে:\n`{err_msg}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ কোনো একটি সমস্যা হয়েছে: {str(e)}")

# বট চালু রাখা
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
