
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .. import LOGGER

HELP_TEXT = """ʜᴏᴡ ᴛᴏ ᴛʀᴀɴsʟᴀᴛᴇ - sᴛᴇᴘ ʙʏ sᴛᴇᴘ ɢᴜɪᴅᴇ:
<blockquote expandable>➼ sᴛᴇᴘ 1: ɢᴇᴛ ɢʀᴏǫ ᴋᴇʏ | <a href='https://console.groq.com/keys?hl=en-IN'>ᴄʟɪᴄᴋ ʜᴇʀᴇ</a> ᴛᴏ ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴀᴘɪ ᴋᴇʏ.
➼ sᴛᴇᴘ 2: ᴜᴘʟᴏᴀᴅ ʏᴏᴜʀ ғɪʟᴇ
sᴇɴᴅ ʏᴏᴜʀ .ᴀss ᴏʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ᴛʜᴇ ʙᴏᴛ.
➼ sᴛᴇᴘ 3: sᴇʟᴇᴄᴛ ᴛʜᴇ ᴇɴɢɪɴᴇ
ᴄʜᴏᴏsᴇ ᴛʜᴇ ʜɪɢʜ-sᴛᴀʙɪʟɪᴛʏ ɢʀᴏǫ ᴇɴɢɪɴᴇ ғᴏʀ ʟɪɢʜᴛɴɪɴɢ-ғᴀsᴛ ʀᴇsᴜʟᴛs.
➼ sᴛᴇᴘ 4: ᴡᴀɪᴛ ғᴏʀ ᴘʀᴏᴄᴇssɪɴɢ
ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ sᴘʟɪᴛ ʏᴏᴜʀ ғɪʟᴇ ɪɴᴛᴏ ᴍɪᴄʀᴏ-ᴄʜᴜɴᴋs ᴛᴏ ᴇɴsᴜʀᴇ ʜɪɢʜ-ǫᴜᴀʟɪᴛʏ ʜɪɴɢʟɪsʜ ᴛʀᴀɴsʟᴀᴛɪᴏɴ.</blockquote>
ɴᴏᴛᴇ: ᴛʜᴇ ʙᴏᴛ ɴᴏᴡ ᴜsᴇs ᴀɴ ᴏᴘᴛɪᴍɪᴢᴇᴅ ɢʀᴏǫ-ᴏɴʟʏ ᴀʀᴄʜɪᴛᴇᴄᴛᴜʀᴇ ғᴏʀ 100% sᴛᴀʙɪʟɪᴛʏ!"""

METADATA_HELP_TEXT = HELP_TEXT

output = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Back to Home", callback_data="back_start"),
        InlineKeyboardButton("ᴄʟosᴇ", callback_data="close_btn")
    ]
])

start_but = InlineKeyboardMarkup([
    [InlineKeyboardButton("[ • ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ • ]", url="https://t.me/HellFire_Academy")],
    [
        InlineKeyboardButton("[ • ᴅᴇᴠᴇʟᴏᴘᴇʀ • ]", url="https://t.me/DoraShin_hlo"),
        InlineKeyboardButton("[ • ᴄʜᴀᴛ • ]", url="https://t.me/HellFire_Academy_Chat")
    ],
    [InlineKeyboardButton("[ • ᴍᴜɢɪᴡᴀʀᴀs ɴᴇᴛᴡᴏʀᴋ • ]", url="https://t.me/Mugiwaras_Network")]
])


async def edit_msg(message, text=None, **kwargs):
    try:
        if text:
            return await message.edit_text(text, **kwargs)
        if 'caption' in kwargs:
            return await message.edit_caption(**kwargs)
        return await message.edit(**kwargs)
    except:
        pass
