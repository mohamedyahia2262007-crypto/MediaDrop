import os
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("media_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_urls = {}

def get_formats(url):
    ydl_opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    formats = []
    seen = set()
    for f in info.get("formats", []):
        if f.get("vcodec") != "none" and f.get("height"):
            label = f"{f['height']}p"
            if label not in seen:
                seen.add(label)
                formats.append(("video", f['format_id'], label))
    formats.append(("audio", "bestaudio", "🎵 صوت MP3"))
    return formats, info.get("title", "ملف")

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "👋 **أهلاً! أنا MediaDrop**\n\n"
        "📎 ابعتلي أي رابط من:\n"
        "▶️ يوتيوب | 🎵 تيك توك | 📸 إنستغرام\n"
        "🐦 تويتر | 👥 فيسبوك | وأكتر!\n\n"
        "⬇️ ابعت الرابط وأنا هجيبهولك 🚀"
    )

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_url(client, message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply("❌ ابعتلي رابط صحيح يبدأ بـ http")
        return
    status_msg = await message.reply("🔍 بفحص الرابط...")
    try:
        formats, title = get_formats(url)
        user_urls[message.from_user.id] = {"url": url, "title": title}
        buttons = []
        for ftype, fid, label in formats:
            buttons.append([InlineKeyboardButton(label, callback_data=f"dl|{ftype}|{fid}")])
        await status_msg.edit(
            f"✅ **تم العثور على الملف:**\n📌 {title[:50]}\n\n🎯 **اختار الجودة:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await status_msg.edit("❌ **فشل في قراءة الرابط**\nتأكد إن الرابط صح")

@app.on_callback_query()
async def handle_download(client, callback_query):
    data = callback_query.data.split("|")
    ftype, fid = data[1], data[2]
    user_id = callback_query.from_user.id
    if user_id not in user_urls:
        await callback_query.answer("❌ انتهت الجلسة، ابعت الرابط تاني")
        return
    url = user_urls[user_id]["url"]
    await callback_query.message.edit("⬇️ **جاري التحميل...**")
    try:
        output_path = f"downloads/{user_id}"
        os.makedirs(output_path, exist_ok=True)
        if ftype == "audio":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{output_path}/%(title)s.%(ext)s",
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                "quiet": True,
            }
        else:
            ydl_opts = {
                "format": f"bestvideo[format_id={fid}]+bestaudio/best",
                "outtmpl": f"{output_path}/%(title)s.%(ext)s",
                "merge_output_format": "mp4",
                "quiet": True,
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if ftype == "audio":
                filename = filename.rsplit(".", 1)[0] + ".mp3"
        await callback_query.message.edit("📤 **جاري الإرسال...**")
        file_size = os.path.getsize(filename) / (1024 * 1024)
        if file_size > 2000:
            await callback_query.message.edit("❌ الملف أكبر من 2GB")
            return
        if ftype == "audio":
            await callback_query.message.reply_audio(filename)
        else:
            await callback_query.message.reply_video(filename)
        await callback_query.message.delete()
        os.remove(filename)
    except Exception as e:
        await callback_query.message.edit(f"❌ **فشل التحميل**\n{str(e)[:100]}")

app.run()
