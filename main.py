from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

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

# ================= START =================

@app.on_message(filters.command("start"))
async def start(client, message):

    buttons = [
        [InlineKeyboardButton("📚 Class 11th", callback_data="class_11")],
        [InlineKeyboardButton("📘 Class 12th", callback_data="class_12")]
    ]

    await message.reply_text(
        "❤️ Welcome To Lecture Bot\n\nSelect Your Class",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CLASS =================

@app.on_callback_query(filters.regex("^class_"))
async def class_open(client, query):

    class_name = query.data.split("_")[1]

    chapter_list = await lectures.distinct(
        "chapter",
        {"class": class_name}
    )

    buttons = []

    for chapter in chapter_list:

        buttons.append(
            [
                InlineKeyboardButton(
                    chapter,
                    callback_data=f"chapter_{class_name}_{chapter}"
                )
            ]
        )

    await query.message.edit_text(
        "📖 Select Chapter",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CHAPTER =================

@app.on_callback_query(filters.regex("^chapter_"))
async def chapter_open(client, query):

    data = query.data.split("_")

    class_name = data[1]

    chapter = "_".join(data[2:])

    lecture_list = lectures.find({
        "class": class_name,
        "chapter": chapter
    }).sort("lecture_no", 1)

    buttons = []

    async for lec in lecture_list:

        buttons.append(
            [
                InlineKeyboardButton(
                    lec["lecture_name"],
                    callback_data=f"lecture_{lec['_id']}"
                )
            ]
        )

    await query.message.edit_text(
        f"🎥 {chapter} Lectures",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= SEND VIDEO =================

@app.on_callback_query(filters.regex("^lecture_"))
async def send_video(client, query):

    lec_id = query.data.split("_")[1]

    lec = await lectures.find_one({
        "_id": ObjectId(lec_id)
    })

    await query.message.reply_video(
        video=lec["file_id"],
        caption=f"""
📚 Class {lec['class']}
📖 {lec['chapter']}
🎥 {lec['lecture_name']}
"""
    )

# ================= ADMIN UPLOAD =================

@app.on_message(filters.video & filters.private)
async def upload_lecture(client, message):

    if message.from_user.id != ADMIN_ID:
        return

    if not message.caption:

        return await message.reply_text(
            "❌ Use Caption:\n\n11|Mechanics|1|Lecture 1"
        )

    try:

        data = message.caption.split("|")

        class_name = data[0].strip()

        chapter = data[1].strip()

        lecture_no = int(data[2].strip())

        lecture_name = data[3].strip()

        file_id = message.video.file_id

        await lectures.insert_one({

            "class": class_name,

            "chapter": chapter,

            "lecture_no": lecture_no,

            "lecture_name": lecture_name,

            "file_id": file_id

        })

        await message.reply_text(
            f"✅ Saved\n\n{lecture_name}"
        )

    except Exception as e:

        await message.reply_text(
            f"❌ Error\n{e}"
        )

# ================= RUN =================

print("Bot Started...")
app.run()
