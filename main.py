from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatMemberStatus
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# ================= CONFIG =================

API_ID = 39683282
API_HASH = "ab1cc41ca283d480ebe386b1dce182f3"
BOT_TOKEN = "8965308397:AAFlZZglV1p5z4o4Caovgw6BaJu2K0oYpYs"

MONGO_URI = "mongodb+srv://doctorprotg:1234@cluster0.jdd1egz.mongodb.net/?appName=Cluster0"

ADMIN_ID = 7960300322
FORCE_SUB_CHANNEL = "@PHYSICSAHOLIC_CHANNEL"

async def subscribed(user_id):
    try:
        member = await app.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        print("Status:", member.status)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception as e:
        print("ForceSub Error:", repr(e))
        return False

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
dpps = db["dpps"]

# ================= STATES =================

STATE = {}
DEL_STATE = {}
BROADCAST = {}
DPP_STATE = {}

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, msg):

    await users.update_one(
        {"id": msg.from_user.id},
        {"$set": {"id": msg.from_user.id}},
        upsert=True
    )

    if not await subscribed(msg.from_user.id):
        return await msg.reply_text(
            "🚫 Please join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@','')}")],
                [InlineKeyboardButton("✅ Try Again", callback_data="check_sub")]
            ])
        )

    if msg.from_user.id == ADMIN_ID:

        keyboard = [

            [InlineKeyboardButton("📤 Upload Lectures", callback_data="admin_upload")],

            [InlineKeyboardButton("📝 Upload DPP", callback_data="upload_dpp")],

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
        [InlineKeyboardButton("📚 Class 12", callback_data="class_12")],
        [InlineKeyboardButton("📝 DPP", callback_data="dpp")]
    ]

    await msg.reply_text(
        "📚 Select Option",
        reply_markup=InlineKeyboardMarkup(buttons)
    )



@app.on_callback_query(filters.regex("^check_sub$"))
async def check_sub(_, q):
    if not await subscribed(q.from_user.id):
        return await q.answer("❌ Please join the channel first.", show_alert=True)
    await q.message.delete()
    buttons=[
        [InlineKeyboardButton("📚 Class 11", callback_data="class_11")],
        [InlineKeyboardButton("📚 Class 12", callback_data="class_12")],
        [InlineKeyboardButton("📝 DPP", callback_data="dpp")]
    ]
    await app.send_message(q.message.chat.id,"📚 Select Option",reply_markup=InlineKeyboardMarkup(buttons))

# ================= DPP MENU =================

# ================= DPP MENU =================

@app.on_callback_query(filters.regex(r"^dpp$"))
async def dpp_menu(_, q):

    buttons = [

        [InlineKeyboardButton(
            "📄 Class 11 DPP",
            callback_data="dpp_11"
        )],

        [InlineKeyboardButton(
            "📄 Class 12 DPP",
            callback_data="dpp_12"
        )]
    ]

    await q.message.edit_text(
        "📝 Select DPP",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    

# ================= SEND DPP =================

# ================= SEND DPP =================

@app.on_callback_query(filters.regex(r"^dpp_(11|12)$"))
async def send_dpp(_, q):

    class_name = q.data.split("_")[1]

    files = await dpps.find({
        "class": class_name
    }).to_list(length=1000)

    if not files:
        return await q.answer(
            "No DPP uploaded",
            show_alert=True
        )

    await q.message.delete()

    for f in files:

        await q.message.reply_document(
            f["file_id"],
            caption=f.get("name", "DPP"),
              )

# ================= ADMIN PANEL =================

@app.on_callback_query(filters.regex("^admin_|^upload_dpp$"))
async def admin_panel(_, q):

    if q.from_user.id != ADMIN_ID:
        return await q.answer("Not allowed", show_alert=True)

    # ================= UPLOAD LECTURES =================

    if q.data == "admin_upload":

        STATE[q.from_user.id] = {"step": "class"}

        return await q.message.edit_text(
            "📚 Send Class (11/12)"
        )

    # ================= UPLOAD DPP =================

    if q.data == "upload_dpp":

        buttons = [

            [InlineKeyboardButton(
                "📚 Class 11 DPP",
                callback_data="upload_dpp_11"
            )],

            [InlineKeyboardButton(
                "📘 Class 12 DPP",
                callback_data="upload_dpp_12"
            )]
        ]

        return await q.message.edit_text(
            "📝 Select DPP Class",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ================= STATS =================

    if q.data == "admin_stats":

        u = await users.count_documents({})
        l = await lectures.count_documents({})

        return await q.message.edit_text(
            f"📊 Users: {u}\n📚 Lectures: {l}"
        )

    # ================= BROADCAST =================

    if q.data == "admin_broadcast":

        BROADCAST[q.from_user.id] = True

        return await q.message.edit_text(
            "📢 Send broadcast message"
        )

    # ================= DELETE =================

    if q.data == "admin_delete":

        DEL_STATE[q.from_user.id] = {"step": "class"}

        return await q.message.edit_text(
            "🗑 Send Class to delete"
        )

# ================= DPP CLASS SELECT =================

@app.on_callback_query(filters.regex("^upload_dpp_"))
async def upload_dpp_class(_, q):

    if q.from_user.id != ADMIN_ID:
        return

    class_name = q.data.split("_")[-1]

    DPP_STATE[q.from_user.id] = class_name

    await q.message.edit_text(
        f"📤 Now send ALL PDFs for Class {class_name}"
    )

# ================= CLASS =================

@app.on_callback_query(filters.regex("^class_"))
async def class_open(_, q):

    class_name = q.data.split("_")[1]

    chapters = await lectures.distinct(
        "chapter",
        {"class": class_name}
    )

    buttons = [

        [InlineKeyboardButton(
            ch,
            callback_data=f"chapter_{class_name}_{ch}"
        )]

        for ch in chapters
    ]

    await q.message.edit_text(
        "📖 Select Chapter",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CHAPTER =================

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

        asyncio.create_task(
            delete_after(
                q.message.chat.id,
                sent.id
            )
        )

    await app.send_message(
        q.message.chat.id,
        "🙏 Enjoy your lectures!\n⏳ Auto-delete in 24 hours enabled.IF YOU WANT TO ACCEES IT PERMANENTLY WITHOUT COPYRIGHT ISSUES OR ANY OTHER ALL*N BUN ACADEMY SEE W SARVAM OR ANY OTHER LECTURES BOTH HINDI AND ENGLISH MEDIUM MESSAGE HERE @THE_PHYSICS_LAD_BACKUP"
    )

# ================= AUTO DELETE =================

async def delete_after(chat_id, message_id):

    await asyncio.sleep(10800)

    try:

        await app.delete_messages(
            chat_id,
            message_id
        )

    except Exception as e:
        print(e)

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

        return await msg.reply_text(
            f"📢 Sent to {sent} users"
        )

    # ================= UPLOAD =================

    state = STATE.get(uid)

    if uid == ADMIN_ID and state:

        if state["step"] == "class":

            state["class"] = text

            state["step"] = "chapter"

            return await msg.reply_text(
                "📖 Send Chapter Name"
            )

        if state["step"] == "chapter":

            state["chapter"] = text

            state["step"] = "videos"

            return await msg.reply_text(
                "📤 Now send videos"
            )

    # ================= DELETE =================

    d = DEL_STATE.get(uid)

    if uid == ADMIN_ID and d:

        if d["step"] == "class":

            d["class"] = text

            d["step"] = "chapter"

            return await msg.reply_text(
                "📖 Send Chapter Name"
            )

        if d["step"] == "chapter":

            await lectures.delete_many({
                "class": d["class"],
                "chapter": text
            })

            DEL_STATE.pop(uid, None)

            return await msg.reply_text(
                "🗑 Deleted"
            )

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

    await msg.reply_text(
        "✅ Lecture Saved"
    )

# ================= SAVE DPP =================

@app.on_message(filters.document & filters.private)
async def save_dpp(_, msg):

    if msg.from_user.id != ADMIN_ID:
        return

    class_name = DPP_STATE.get(msg.from_user.id)

    if not class_name:
        return

    await dpps.insert_one({

        "class": class_name,

        "file_id": msg.document.file_id,

        "name": msg.document.file_name

    })

    await msg.reply_text(
        f"✅ Saved: {msg.document.file_name}"
    )

# ================= RUN =================

print("Bot Started...")

app.run()
