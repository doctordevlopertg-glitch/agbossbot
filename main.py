from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# ================= CONFIG =================

API_ID = 123456
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

MONGO_URI = "YOUR_MONGO_URI"

ADMIN_ID = 123456789

# ================= BOT =================

app = Client(
    "lecture_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["lecture_bot"]

lectures = db["lectures"]
users = db["users"]

# ================= STATES =================

UPLOAD_STATE = {}
DELETE_STATE = {}
BROADCAST_STATE = {}

# ================= START =================

@app.on_message(filters.command("start"))
async def start(client, message):

    await users.update_one(
        {"id": message.from_user.id},
        {"$set": {"id": message.from_user.id}},
        upsert=True
    )

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
            caption=v.get("caption", ""),
            protect_content=True
        )

# ================= ADMIN ADD =================

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

    # ========== UPLOAD ==========
    state = UPLOAD_STATE.get(message.from_user.id)

    if state:

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

            await message.reply_text("📤 Send videos, /done when finished")
            return

    # ========== DELETE ==========
    dstate = DELETE_STATE.get(message.from_user.id)

    if dstate:

        if message.text.startswith("/"):
            return

        if dstate["step"] == "class":

            dstate["class"] = message.text.strip()
            dstate["step"] = "chapter"

            await message.reply_text("📖 Send Chapter Name to delete")
            return

        if dstate["step"] == "chapter":

            await lectures.delete_many({
                "class": dstate["class"],
                "chapter": message.text.strip()
            })

            DELETE_STATE.pop(message.from_user.id, None)

            await message.reply_text("🗑 Chapter Deleted")
            return

    # ========== BROADCAST ==========
    if message.from_user.id in BROADCAST_STATE:

        users_list = await users.find().to_list(length=10000)

        sent = 0

        for u in users_list:
            try:
                await client.send_message(u["id"], message.text)
                sent += 1
            except:
                pass

        BROADCAST_STATE.pop(message.from_user.id, None)

        await message.reply_text(f"📢 Sent to {sent} users")

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

    await message.reply_text("✅ Upload Finished")

# ================= DELETE CHAPTER =================

@app.on_message(filters.command("delchapter"))
async def delchapter(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    DELETE_STATE[message.from_user.id] = {"step": "class"}

    await message.reply_text("📚 Send Class")

# ================= STATS =================

@app.on_message(filters.command("stats"))
async def stats(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    u = await users.count_documents({})
    l = await lectures.count_documents({})

    await message.reply_text(
        f"""
📊 Stats

👥 Users: {u}
📚 Lectures: {l}
"""
    )

# ================= BROADCAST =================

@app.on_message(filters.command("broadcast"))
async def broadcast(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    BROADCAST_STATE[message.from_user.id] = True

    await message.reply_text("📢 Send message to broadcast")

# ================= RUN =================

print("Bot Started...")
app.run()
