from ..utils.common import edit_msg
from VideoEncoder import LOGGER

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat

@Client.on_message(filters.command("metadata"))
async def metadata_handler(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)
    user_id = message.from_user.id

    metadata_on = await db.get_metadata_on(user_id)
    title = await db.get_metadata_title(user_id)
    author = await db.get_metadata_author(user_id)
    artist = await db.get_metadata_artist(user_id)
    audio = await db.get_metadata_audio(user_id)
    subtitle = await db.get_metadata_subtitle(user_id)
    video = await db.get_metadata_video(user_id)

    status = "ON" if metadata_on else "OFF"
    on_btn = "✅ ᴏɴ" if metadata_on else "ᴏɴ"
    off_btn = "❌ ᴏғғ" if not metadata_on else "ᴏғғ"

    text = f"㊋ Yᴏᴜʀ Mᴇᴛᴀᴅᴀᴛᴀ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ: {status}\n" \
           f"◈ Tɪᴛʟᴇ ▹ {title}  \n" \
           f"◈ Aᴜᴛʜᴏʀ ▹ {author}  \n" \
           f"◈ Aʀᴛɪꜱᴛ ▹ {artist}  \n" \
           f"◈ Aᴜᴅɪᴏ ▹ {audio}  \n" \
           f"◈ Sᴜʙᴛɪᴛʟᴇ ▹ {subtitle}  \n" \
           f"◈ Vɪᴅᴇᴏ ▹ {video}"

    buttons = [
        [
            InlineKeyboardButton(on_btn, callback_data="metadata_on"),
            InlineKeyboardButton(off_btn, callback_data="metadata_off")
        ],
        [
            InlineKeyboardButton("🥂 ʜᴏᴡ ᴛᴏ sᴇᴛ ᴍᴇᴛᴀᴅᴀᴛᴀ", callback_data="metadata_how_to")
        ],
        [
            InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="closeMeh")
        ]
    ]

    await message.reply_photo(
        photo="https://graph.org/file/3f313447e012a34252704-c4fdaa14a9a0ae0a4b.jpg",
        caption=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        has_spoiler=True
    )


async def update_metadata_msg(cb: CallbackQuery):
    user_id = cb.from_user.id
    metadata_on = await db.get_metadata_on(user_id)
    title = await db.get_metadata_title(user_id)
    author = await db.get_metadata_author(user_id)
    artist = await db.get_metadata_artist(user_id)
    audio = await db.get_metadata_audio(user_id)
    subtitle = await db.get_metadata_subtitle(user_id)
    video = await db.get_metadata_video(user_id)

    status = "ON" if metadata_on else "OFF"
    on_btn = "✅ ᴏɴ" if metadata_on else "ᴏɴ"
    off_btn = "❌ ᴏғғ" if not metadata_on else "ᴏғғ"

    text = f"㊋ Yᴏᴜʀ Mᴇᴛᴀᴅᴀᴛᴀ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ: {status}\n" \
           f"◈ Tɪᴛʟᴇ ▹ {title}  \n" \
           f"◈ Aᴜᴛʜᴏʀ ▹ {author}  \n" \
           f"◈ Aʀᴛɪꜱᴛ ▹ {artist}  \n" \
           f"◈ Aᴜᴅɪᴏ ▹ {audio}  \n" \
           f"◈ Sᴜʙᴛɪᴛʟᴇ ▹ {subtitle}  \n" \
           f"◈ Vɪᴅᴇᴏ ▹ {video}"

    buttons = [
        [
            InlineKeyboardButton(on_btn, callback_data="metadata_on"),
            InlineKeyboardButton(off_btn, callback_data="metadata_off")
        ],
        [
            InlineKeyboardButton("🥂 ʜᴏᴡ ᴛᴏ sᴇᴛ ᴍᴇᴛᴀᴅᴀᴛᴀ", callback_data="metadata_how_to")
        ],
        [
            InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="closeMeh")
        ]
    ]

    try:
        await edit_msg(
            cb.message,
            media=InputMediaPhoto(
                "https://graph.org/file/3f313447e012a34252704-c4fdaa14a9a0ae0a4b.jpg",
                caption=text,
                has_spoiler=True
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        try:
            await edit_msg(cb.message, caption=text, reply_markup=InlineKeyboardMarkup(buttons))
        except:
            pass

@Client.on_message(filters.command(["settitle", "setauthor", "setartist", "setaudio", "setsubtitle", "setvideo"]))
async def set_metadata_cmds(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)
    user_id = message.from_user.id

    cmd = message.command[0]
    if len(message.command) < 2:
        await message.reply_text(f"Usage: <code>/{cmd} [text]</code>")
        return

    text = message.text.split(None, 1)[1]

    if cmd == "settitle":
        await db.set_metadata_title(user_id, text)
    elif cmd == "setauthor":
        await db.set_metadata_author(user_id, text)
    elif cmd == "setartist":
        await db.set_metadata_artist(user_id, text)
    elif cmd == "setaudio":
        await db.set_metadata_audio(user_id, text)
    elif cmd == "setsubtitle":
        await db.set_metadata_subtitle(user_id, text)
    elif cmd == "setvideo":
        await db.set_metadata_video(user_id, text)

    await message.reply_text(f"Successfully set <b>{cmd[3:]}</b> to: <code>{text}</code>")
