
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat

FONTS_PIC = "https://graph.org/file/345a253f5043d9a0a06cf-8b3ff931578171d109.jpg"

@Client.on_message(filters.command("fonts"))
async def fonts_handler(bot: Client, event: Message):
    c = await check_chat(event, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, event)

    # Message: Use a Collapsible Quote with Small Caps.
    # 📥 𝖲𝖤𝖫𝖤𝖢𝖳 𝖸𝖮𝖴𝖱 𝖯𝖱𝖤𝖥𝖤𝖱𝖱𝖤𝖣 𝖥𝖮𝖭𝖳
    # > ➤ ᴄʜᴏᴏsᴇ ᴀ sᴛʏʟᴇ ʙᴇʟᴏᴡ. ɪғ ɴᴏ ꜰᴏɴᴛ ɪs sᴇʟᴇᴄᴛᴇᴅ, ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴜsᴇ ᴛʜᴇ ᴅᴇꜰᴀᴜʟᴛ sʏsᴛᴇᴍ ꜰᴏɴᴛ.

    caption = (
        "📥 𝖲𝖤𝖫𝖤𝖢𝖳 𝖸𝖮𝖴𝖱 𝖯𝖱𝖤𝖥𝖤𝖱𝖱𝖤𝖣 𝖥𝖮𝖭𝖳\n\n"
        "**> ➤ ᴄʜᴏᴏsᴇ ᴀ sᴛʏʟᴇ ʙᴇʟᴏᴡ. ɪғ ɴᴏ ꜰᴏɴᴛ ɪs sᴇʟᴇᴄᴛᴇᴅ, ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴜsᴇ ᴛʜᴇ ᴅᴇꜰᴀᴜʟᴛ sʏsᴛᴇᴍ ꜰᴏɴᴛ.**"
    )

    buttons = [
        [
            InlineKeyboardButton("[ ᴀʀɪᴀʟ ]", callback_data="set_font_Arial"),
            InlineKeyboardButton("[ ʀᴏʙᴏᴛᴏ ]", callback_data="set_font_Roboto")
        ],
        [
            InlineKeyboardButton("[ ᴠᴇʀᴅᴀɴᴀ ]", callback_data="set_font_Verdana"),
            InlineKeyboardButton("[ ᴛɪᴍᴇs ]", callback_data="set_font_Times")
        ],
        [
            InlineKeyboardButton("[ ᴄʟᴏsᴇ ]", callback_data="close_fonts")
        ]
    ]

    await event.reply_photo(
        photo=FONTS_PIC,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
