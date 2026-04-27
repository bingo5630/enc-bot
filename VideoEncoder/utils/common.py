
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .. import LOGGER

HELP_TEXT = """<blockquote><b>How to Translate - Step by Step Guide:</b></blockquote>
<blockquote expandable>➼ <b>Step 1: Get Groq Key</b>
[Click here to Create Groq API Key](https://console.groq.com/keys) and add it using /set_groq_api.

➼ <b>Step 2: Upload Your File</b>
Send your .ass or subtitle file directly to the bot.

➼ <b>Step 3: Select the Engine</b>
Choose the high-stability Groq engine for lightning-fast results.

➼ <b>Step 4: Wait for Processing</b>
The bot will split your file into micro-chunks to ensure high-quality Hinglish translation. Once done, you'll receive the translated file.</blockquote>

<b>Note:</b> The bot now uses an optimized Groq-Only architecture for 100% stability!"""

output = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Back to Home", callback_data="back_start"),
        InlineKeyboardButton("ᴄʟosᴇ", callback_data="close_btn")
    ]
])

start_but = InlineKeyboardMarkup([
    [InlineKeyboardButton("⚙️ sᴇᴛᴛɪɴɢs", callback_data="OpenSettings")],
    [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_callback"), InlineKeyboardButton("👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/Dorashin_hlo")],
    [InlineKeyboardButton("• ᴍᴜɢɪᴡᴀʀᴀs ɴᴇᴛᴡᴏʀᴋ •", url="https://t.me/Mugiwaras_Network")]
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
