from ..utils.common import edit_msg, METADATA_HELP_TEXT
from VideoEncoder import LOGGER

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat

async def get_metadata_menu(user_id):
    is_on = await db.get_metadata_on(user_id)

    if is_on:
        on_text, off_text = "ON ✅", "OFF"
    else:
        on_text, off_text = "ON", "OFF ✅"

    buttons = [
        [
            InlineKeyboardButton(on_text, callback_data="meta_on"),
            InlineKeyboardButton(off_text, callback_data="meta_off")
        ],
        [
            InlineKeyboardButton("CLOSE ✖️", callback_data="close_meta")
        ]
    ]
    return METADATA_HELP_TEXT, InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command("metadata"))
async def metadata_handler(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)
    user_id = message.from_user.id
    text, reply_markup = await get_metadata_menu(user_id)

    await message.reply_photo(
        photo="https://graph.org/file/3f313447e012a34252704-c4fdaa14a9a0ae0a4b.jpg",
        caption=text,
        reply_markup=reply_markup,
        has_spoiler=True
    )


async def update_metadata_msg(cb: CallbackQuery):
    user_id = cb.from_user.id
    text, reply_markup = await get_metadata_menu(user_id)

    try:
        await edit_msg(
            cb.message,
            media=InputMediaPhoto(
                "https://graph.org/file/3f313447e012a34252704-c4fdaa14a9a0ae0a4b.jpg",
                caption=text,
                has_spoiler=True
            ),
            reply_markup=reply_markup
        )
    except:
        try:
            await edit_msg(cb.message, caption=text, reply_markup=reply_markup)
        except:
            pass

@Client.on_message(filters.command(["settitle", "setauthor", "setartist", "setaudio", "setsubtitle", "setvideo"]))
async def set_metadata_cmds(bot: Client, message: Message):
    # Keep these for backward compatibility unless user explicitly said remove them too.
    # The requirement said remove /settings, not these commands.
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
