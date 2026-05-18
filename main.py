from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ================= CONFIG =================

API_ID = 39683282
API_HASH = "ab1cc41ca283d480ebe386b1dce182f3"
BOT_TOKEN = "8965308397:AAFlZZglV1p5z4o4Caovgw6BaJu2K0oYpYs"

MONGO_URI = "mongodb+srv://doctorprotg:1234@cluster0.jdd1egz.mongodb.net/?appName=Cluster0"

ADMIN_ID = 7960300322




# ================= BOT =================

app = Client(
    "lecture_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo["lecture_bot"]
lectures = db["lectures"]

# ================= STATE =================

UPLOAD_STATE = {}

# ================= START =================

@app.on_message(filters.command("start"))
async def start(client, message):

    buttons = [
        [InlineKeyboardButton("📚 Class 11th", callback_data="class_11")],
        [InlineKeyboardButton("📘 Class 12th", callback_data="class_12")]
    ]

    await message.reply_text(
        "📚 Select Your Class",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CLASS =================

@app.on_callback_query(filters.regex("^class_"))
async def class_open(client, query):

    class_name = query.data.split("_")[1]

    chapters = await lectures.distinct("chapter", {"class": class_name})

    buttons = [
        [InlineKeyboardButton(ch, callback_data=f"chapter_{class_name}_{ch}")]
        for ch in chapters
    ]

    await query.message.edit_text(
        "📖 Select Chapter",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CHAPTER (SEND ALL VIDEOS) =================

@app.on_callback_query(filters.regex("^chapter_"))
async def chapter_open(client, query):

    data = query.data.split("_")
    class_name = data[1]
    chapter = "_".join(data[2:])

    vids = await lectures.find({
        "class": class_name,
        "chapter": chapter
    }).to_list(length=1000)

    await query.message.delete()

    for v in vids:
        await client.send_video(
            chat_id=query.message.chat.id,
            video=v["file_id"],
            caption=v.get("caption", "")
        )

# ================= ADMIN /add =================

@app.on_message(filters.command("add"))
async def add(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    UPLOAD_STATE[message.from_user.id] = {"step": "class"}

    await message.reply_text("📚 Send Class (11 or 12)")

# ================= TEXT HANDLER =================

@app.on_message(filters.text & filters.private)
async def text_handler(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    state = UPLOAD_STATE.get(message.from_user.id)
    if not state:
        return

    if message.text.startswith("/"):
        return

    if state["step"] == "class":

        state["class"] = message.text.strip()
        state["step"] = "chapter"

        await message.reply_text("📖 Send Chapter Name")
        return

    if state["step"] == "chapter":

        state["chapter"] = message.text.strip()
        state["step"] = "videos"

        await message.reply_text(
            "📤 Now send all videos one by one.\nSend /done when finished"
        )
        return

# ================= SAVE VIDEO =================

@app.on_message(filters.video & filters.private)
async def save_video(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    state = UPLOAD_STATE.get(message.from_user.id)

    if not state or state["step"] != "videos":
        return

    await lectures.insert_one({
        "class": state["class"],
        "chapter": state["chapter"],
        "file_id": message.video.file_id,
        "caption": message.caption or ""
    })

    await message.reply_text("✅ Saved")

# ================= DONE =================

@app.on_message(filters.command("done"))
async def done(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    UPLOAD_STATE.pop(message.from_user.id, None)

    await message.reply_text("✅ Upload Completed")

# ================= RUN =================

print("Bot Started...")
app.run()
