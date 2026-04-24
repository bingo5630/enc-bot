
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .. import LOGGER

output = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Back to Home", callback_data="backToStart"),
        InlineKeyboardButton("ᴄʟosᴇ", callback_data="closeMeh")
    ]
])

start_but = InlineKeyboardMarkup([
    [InlineKeyboardButton("⚙️ sᴇᴛᴛɪɴɢs", callback_data="OpenSettings")],
    [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_callback"), InlineKeyboardButton("👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/Dorashin_hlo")],
    [InlineKeyboardButton("• ᴍᴜɢɪᴡᴀʀᴀs ɴᴇᴛᴡᴏʀᴋ •", url="https://t.me/Mugiwaras_Network")]
])


async def edit_msg(msg, **kwargs):
    try:
        if 'media' in kwargs:
            return await msg.edit_media(**kwargs)
        if 'caption' in kwargs:
            return await msg.edit_caption(**kwargs)
        if 'text' in kwargs:
            return await msg.edit_text(**kwargs)
        return await msg.edit(**kwargs)
    except MessageNotModified:
        pass
    except Exception as e:
        LOGGER.error(f"Error in edit_msg: {e}")
