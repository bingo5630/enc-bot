import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from .. import ASSETS_DIR
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat

@Client.on_message(filters.command(["sthumb"]))
async def sthumb_command(client: Client, message: Message):
    try:
        c = await check_chat(message, chat='Both')
        if not c:
            return
        await AddUserToDatabase(client, message)

        user_id = message.from_user.id

        if not (message.reply_to_message and message.reply_to_message.photo):
            await message.reply_text("❌ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴛᴏ sᴇᴛ ɪᴛ ᴀs ᴛʜᴜᴍʙɴᴀɪʟ.")
            return

        # Define absolute path
        target_path = os.path.abspath(os.path.join(ASSETS_DIR, f"thumb_{user_id}.jpg"))

        # Download and overwrite
        await message.reply_to_message.download(file_name=target_path)
        
        if os.path.exists(target_path):
            # (Bold, Quote, Small Caps)
            success_text = (
                "<b><blockquote>✅ ᴛʜᴜᴍʙɴᴀɪʟ sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!\n"
                "ʏᴏᴜʀ ɴᴇᴡ ᴄᴏᴠᴇʀ ɪᴍᴀɢᴇ ʜᴀs ʙᴇᴇɴ sᴀᴠᴇᴅ. ᴀʟʟ ʏᴏᴜʀ ғᴜᴛᴜʀᴇ ᴇɴᴄᴏᴅᴇᴅ ᴠɪᴅᴇᴏs/ᴅᴏᴄs ᴡɪʟʟ ɴᴏᴡ ᴜsᴇ ᴛʜɪs ᴛʜᴜᴍʙɴᴀɪʟ.</blockquote></b>"
            )
            
            buttons = [
                [
                    InlineKeyboardButton("ʜᴇʟᴘ", callback_data="help_callback")
                ],
                [
                    InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="closeMeh")
                ]
            ]
            
            await message.reply_text(
                text=success_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await message.reply_text("❌ ᴇʀʀᴏʀ: ᴅᴏᴡɴʟᴏᴀᴅ ғᴀɪʟᴇᴅ, ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.")

    except Exception as e:
        logging.error(f"Error in sthumb_command: {e}")
        await message.reply_text(f"❌ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {str(e)}")
