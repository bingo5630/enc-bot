from VideoEncoder import LOGGER
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from .. import ASSETS_DIR
from ..utils.database.access_db import db
from ..utils.helper import check_chat
from ..utils.database.add_user import AddUserToDatabase
import logging
import asyncio
import os

WATERMARK_PIC = "https://graph.org/file/65aea4e00b2a2b6015d0e-6492306dbbd65ad3bc.jpg"

# user_id: timestamp of when they clicked 'set_watermark'
watermark_sessions = {}

async def get_watermark_menu(user_id):
    watermark_path = os.path.join(ASSETS_DIR, f'watermark_{user_id}.png')
    has_watermark = os.path.exists(watermark_path)

    text = "> <b>\"ᴡᴀɴɴᴀ sᴛᴀᴍᴘ ʏᴏᴜʀ ᴀᴜᴛʜᴏʀɪᴛʏ? ᴀᴅᴅ ᴀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴀɴᴅ ʟᴇᴛ ᴛʜᴇ ᴡᴏʀʟᴅ ᴋɴᴏᴡ ᴡʜᴏ ᴛʜᴇ ʙᴏss ɪs!\"</b>"

    if has_watermark:
        btn_row1 = [InlineKeyboardButton("🔄 ᴄʜᴀɴɢᴇ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="set_watermark")]
    else:
        btn_row1 = [InlineKeyboardButton("🖼️ sᴇᴛ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="set_watermark")]

    buttons = [
        btn_row1,
        [
            InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="del_watermark"),
            InlineKeyboardButton("🔙 Back to Home", callback_data="back_start")
        ],
        [
            InlineKeyboardButton("❓ ʜᴏᴡ ᴛᴏ sᴇᴛ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="how_watermark"),
            InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="closeMeh")
        ]
    ]
    return text, InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command(["watermark"]))
async def watermark_command(client, message):
    try:
        c = await check_chat(message, chat='Both')
        if not c:
            return
        await AddUserToDatabase(client, message)
        user_id = message.from_user.id
        text, reply_markup = await get_watermark_menu(user_id)

        await message.reply_photo(
            photo=WATERMARK_PIC,
            caption=text,
            reply_markup=reply_markup,
            has_spoiler=True
        )
    except Exception as e:
        logging.error(f"Error in watermark_command: {e}")
        await message.reply_text(f"An error occurred: {str(e)}")


@Client.on_message(filters.photo & filters.private)
async def save_watermark(client, message):
    try:
        user_id = message.from_user.id

        # Check if user has an active session
        if user_id in watermark_sessions:
            start_time = watermark_sessions[user_id]
            current_time = asyncio.get_event_loop().time()

            if current_time - start_time <= 30:
                await message.reply_text("<b>⏳ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴡᴀᴛᴇʀᴍᴀʀᴋ...</b>")
                path = os.path.join(ASSETS_DIR, f'watermark_{user_id}.png')
                await message.download(file_name=path)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    await message.reply_text("<b>✅ ᴡᴀᴛᴇʀᴍᴀʀᴋ sᴀᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>")
                else:
                    await message.reply_text("<b>❌ Failed to save watermark!</b>")
                del watermark_sessions[user_id]
                return
            else:
                del watermark_sessions[user_id]
                await message.reply_text("<b>⏳ ᴛɪᴍᴇᴏᴜᴛ! ʏᴏᴜ ᴅɪᴅɴ'ᴛ sᴇɴᴅ ᴛʜᴇ ᴘʜᴏᴛᴏ ᴡɪᴛʜɪɴ 30 sᴇᴄᴏɴᴅs.</b>")
                return

    except Exception as e:
        logging.error(f"Error in save_watermark: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")
