from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from ..utils.database.access_db import db
from ..utils.helper import check_chat
from ..utils.database.add_user import AddUserToDatabase
import logging
import asyncio
import os

THUMB_PIC = "https://graph.org/file/6504612917aad8701d6c9-24fac814bd1b49fe90.jpg"

# user_id: timestamp of when they clicked 'add_thumb'
thumbnail_sessions = {}

@Client.on_message(filters.command(["thumb", "thumbnail"]))
async def thumb_command(client, message):
    try:
        c = await check_chat(message, chat='Both')
        if not c:
            return
        await AddUserToDatabase(client, message)
        user_id = message.from_user.id
        thumbnail = await db.get_thumbnail(user_id)

        thumb_path = os.path.join(os.getcwd(), 'Assets', f'thumb_{user_id}.jpg')
        os.makedirs('Assets', exist_ok=True)
        has_thumb = os.path.exists(thumb_path)

        text = "> <b>\"ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴅᴅ ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ\"</b>\n\n✨ Let's make your files look amazing! Send me a high-quality image to set as your custom cover."

        if has_thumb:
            btn_row1 = [InlineKeyboardButton("🔄 ᴄʜᴀɴɢᴇ ᴛʜᴜᴍʙɴᴀɪʟ", callback_data="set_thumb")]
            photo = thumb_path
        elif thumbnail:
            btn_row1 = [InlineKeyboardButton("🔄 ᴄʜᴀɴɢᴇ ᴛʜᴜᴍʙɴᴀɪʟ", callback_data="set_thumb")]
            photo = thumbnail
        else:
            btn_row1 = [InlineKeyboardButton("📸 sᴇᴛ ᴛʜᴜᴍʙɴᴀɪʟ", callback_data="set_thumb")]
            photo = THUMB_PIC

        buttons = [
            btn_row1,
            [
                InlineKeyboardButton("ᴀᴅᴅ ᴛʜᴜᴍʙ", callback_data="set_thumb"),
                InlineKeyboardButton("ʀᴇᴍᴏᴠᴇ ᴛʜᴜᴍʙ", callback_data="del_thumb")
            ],
            [
                InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="closeMeh")
            ]
        ]

        await message.reply_photo(
            photo=photo,
            caption=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            has_spoiler=True
        )
    except Exception as e:
        logging.error(f"Error in thumb_command: {e}")
        await message.reply_text(f"An error occurred: {str(e)}")


@Client.on_message(filters.photo & filters.private)
async def save_thumb(client, message):
    try:
        user_id = message.from_user.id
        file_id = message.photo.file_id
        
        # Check if user has an active session
        if user_id in thumbnail_sessions:
            start_time = thumbnail_sessions[user_id]
            current_time = asyncio.get_event_loop().time()
            
            if current_time - start_time <= 30:
                await message.reply_text("<b>⏳ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ...</b>")
                await db.set_thumbnail(user_id, file_id)
                path = os.path.join(os.getcwd(), 'Assets', f'thumb_{user_id}.jpg')
                os.makedirs('Assets', exist_ok=True)
                await message.download(file_name=path)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    await message.reply_text("✅ Custom thumbnail saved!")
                else:
                    await message.reply_text("❌ Failed to save thumbnail.")
                del thumbnail_sessions[user_id]
                return
            else:
                del thumbnail_sessions[user_id]
                await message.reply_text("⏳ Timeout! You didn't send the photo within 30 seconds.")
                return

        # Alternative: Photo sent with command as caption
        if message.caption and (message.caption == "/thumb" or message.caption == "/thumbnail"):
            await message.reply_text("<b>⏳ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ...</b>")
            await db.set_thumbnail(user_id, file_id)
            path = os.path.join(os.getcwd(), 'Assets', f'thumb_{user_id}.jpg')
            os.makedirs('Assets', exist_ok=True)
            await message.download(file_name=path)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                await message.reply_text("✅ Custom thumbnail saved!")
            else:
                await message.reply_text("❌ Failed to save thumbnail.")
            
    except Exception as e:
        logging.error(f"Error in save_thumb: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")
