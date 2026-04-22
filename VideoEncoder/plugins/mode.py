from VideoEncoder import LOGGER

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat

MODE_PIC = "https://graph.org/file/61211d0416a6e886f4afd-cfc84ede9ac2a83658.jpg"

@Client.on_message(filters.command("mode"))
async def mode_handler(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)
    user = message.from_user
    name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    mention = f"<a href='{link}'>{name}</a>"

    text = f"<blockquote expandable>ʜᴇʏʏ...! {mention}\n\"ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ғɪʟᴇ ғᴏʀᴍᴀᴛ, ᴏᴛʜᴇʀᴡɪsᴇ ɪ'ʟʟ ᴅᴏ ᴍʏ ᴏᴡɴ ғᴏʀᴍᴀᴛ ʜᴇʜᴇʜʜᴇ....\"</blockquote>"

    buttons = [
        [
            InlineKeyboardButton("ᴠɪᴅᴇᴏ", callback_data="mode_video"),
            InlineKeyboardButton("ᴅᴏᴄᴜᴍᴇɴᴛ", callback_data="mode_document")
        ],
        [
            InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="closeMeh")
        ]
    ]

    await message.reply_photo(
        photo=MODE_PIC,
        caption=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        has_spoiler=True
    )

