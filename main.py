from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# ================= CONFIG =================

API_ID = 39683282
API_HASH = "ab1cc41ca283d480ebe386b1dce182f3"
BOT_TOKEN = "8965308397:AAFlZZglV1p5z4o4Caovgw6BaJu2K0oYpYs"

MONGO_URI = "mongodb+srv://doctorprotg:1234@cluster0.jdd1egz.mongodb.net/?appName=Cluster0"

ADMIN_ID = 7960300322



# ================= APP =================

app = Client(
    "lecture_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

db = AsyncIOMotorClient(MONGO_URI)["lecture_bot"]
lectures = db["lectures"]
users = db["users"]

# ================= STATES =================

STATE = {}
DEL_STATE = {}
BROADCAST = {}

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, msg):

    await users.update_one(
        {"id": msg.from_user.id},
        {"$set": {"id": msg.from_user.id}},
        upsert=True
    )

    if msg.from_user.id == ADMIN_ID:

        keyboard = [
            [InlineKeyboardButton("📤 Upload", callback_data="admin_upload")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🗑 Delete Chapter", callback_data="admin_delete")]
        ]

        return await msg.reply_text(
            "👨‍💻 Admin Panel",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    buttons = [
        [InlineKeyboardButton("📚 Class 11", callback_data="class_11")],
        [InlineKeyboardButton("📚 Class 12", callback_data="class_12")]
    ]

    await msg.reply_text("📚 Select Class", reply_markup=InlineKeyboardMarkup(buttons))

# ================= ADMIN PANEL =================

@app.on_callback_query(filters.regex("^admin_"))
async def admin_panel(_, q):

    if q.from_user.id != ADMIN_ID:
        return await q.answer("Not allowed", show_alert=True)

    if q.data == "admin_upload":
        STATE[q.from_user.id] = {"step": "class"}
        return await q.message.edit_text("📚 Send Class (11/12)")

    if q.data == "admin_stats":
        u = await users.count_documents({})
        l = await lectures.count_documents({})
        return await q.message.edit_text(f"📊 Users: {u}\n📚 Lectures: {l}")

    if q.data == "admin_broadcast":
        BROADCAST[q.from_user.id] = True
        return await q.message.edit_text("📢 Send broadcast message")

    if q.data == "admin_delete":
        DEL_STATE[q.from_user.id] = {"step": "class"}
        return await q.message.edit_text("🗑 Send Class to delete")

# ================= CLASS =================

@app.on_callback_query(filters.regex("^class_"))
async def class_open(_, q):

    class_name = q.data.split("_")[1]

    chapters = await lectures.distinct("chapter", {"class": class_name})

    buttons = [
        [InlineKeyboardButton(ch, callback_data=f"chapter_{class_name}_{ch}")]
        for ch in chapters
    ]

    await q.message.edit_text(
        "📖 Select Chapter",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CHAPTER (BATCH SEND + AUTO DELETE) =================

@app.on_callback_query(filters.regex("^chapter_"))
async def chapter_open(_, q):

    data = q.data.split("_")
    class_name = data[1]
    chapter = "_".join(data[2:])

    vids = await lectures.find({
        "class": class_name,
        "chapter": chapter
    }).to_list(length=1000)

    await q.message.delete()

    for v in vids:

        sent = await app.send_video(
            q.message.chat.id,
            v["file_id"],
            caption=v.get("caption", ""),
            protect_content=True
        )

        # ✅ AUTO DELETE AFTER 24 HOURS
        asyncio.create_task(delete_after(sent, 86400))

    await app.send_message(
        q.message.chat.id,
        "🙏 Enjoy your lectures!\nAuto-delete in 24 hours enabled. IF YOU WANT TO ACCEES IT PERMANENTLY WITHOUT COPYRIGHT ISSUES OR ANY OTHER ALL*N BUN ACADEMY SEE W SARVAM OR ANY OTHER LECTURES BOTH HINDI AND ENGLISH MEDIUM MESSAGE HERE @THE_PHYSICS_LAD_BACKUP"
    )

# ================= AUTO DELETE FUNCTION =================

async def delete_after(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

# ================= TEXT ROUTER =================

@app.on_message(filters.text & filters.private)
async def router(_, msg):

    uid = msg.from_user.id
    text = msg.text.strip()

    # ================= BROADCAST =================

    if BROADCAST.get(uid):

        users_list = await users.find().to_list(length=10000)

        sent = 0
        for u in users_list:
            try:
                await app.send_message(u["id"], text)
                sent += 1
            except:
                pass

        BROADCAST.pop(uid, None)
        return await msg.reply_text(f"📢 Sent to {sent} users")

    # ================= UPLOAD =================

    state = STATE.get(uid)

    if uid == ADMIN_ID and state:

        if state["step"] == "class":
            state["class"] = text
            state["step"] = "chapter"
            return await msg.reply_text("📖 Send Chapter Name")

        if state["step"] == "chapter":
            state["chapter"] = text
            state["step"] = "videos"
            return await msg.reply_text("📤 Now send videos")

    # ================= DELETE =================

    d = DEL_STATE.get(uid)

    if uid == ADMIN_ID and d:

        if d["step"] == "class":
            d["class"] = text
            d["step"] = "chapter"
            return await msg.reply_text("📖 Send Chapter Name")

        if d["step"] == "chapter":

            await lectures.delete_many({
                "class": d["class"],
                "chapter": text
            })

            DEL_STATE.pop(uid, None)
            return await msg.reply_text("🗑 Deleted")

# ================= SAVE VIDEO =================

@app.on_message(filters.video & filters.private)
async def save_video(_, msg):

    if msg.from_user.id != ADMIN_ID:
        return

    state = STATE.get(msg.from_user.id)

    if not state or state["step"] != "videos":
        return

    await lectures.insert_one({
        "class": state["class"],
        "chapter": state["chapter"],
        "file_id": msg.video.file_id,
        "caption": msg.caption or ""
    })

    await msg.reply_text("✅ Saved")

# ================= RUN =================

print("Bot Started...")
app.run()
