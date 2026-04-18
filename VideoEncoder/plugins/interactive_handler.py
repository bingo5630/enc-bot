
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode
from .. import ASSETS_DIR
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat
from .. import data, download_dir

# State management for interactive encoding
# user_id: { 'step': 'subtitle'|'video', 'subtitle_msg': Message, 'video_msg': Message, 'mode': 'encode'|'hard_sub'|'soft_code' }
interactive_sessions = {}

@Client.on_message(filters.command("hard_code") & filters.private)
async def hard_code_cmd(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)

    user_id = message.from_user.id
    user_name = message.from_user.first_name

    thumb_path = os.path.join(ASSETS_DIR, f'thumb_{user_id}.jpg')
    if not (os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0):
        await message.reply_text("❌ <b>ᴇʀʀᴏʀ: ᴛʜᴜᴍʙɴᴀɪʟ ɴᴏᴛ ғᴏᴜɴᴅ!</b>\n\nPlease set a thumbnail first using /thumbnail command before using /hard_code.")
        return

    interactive_sessions[user_id] = {'step': 'subtitle', 'mode': 'hard_sub'}

    text = f"🫧 𝐘ᴜᴘᴘ...! <a href='tg://user?id={user_id}'>{user_name}</a>\n" \
           f"<blockquote expandable>🍃 𝐏ʟᴇᴀsᴇ 𝐒ᴇɴᴅ ʏᴏᴜʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ (.ass/.srt) to me! I'm good at my work.</blockquote>"

    buttons = [[InlineKeyboardButton("🗑️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_interactive")]]
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.command("soft_code") & filters.private)
async def soft_code_cmd(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)

    user_id = message.from_user.id
    user_name = message.from_user.first_name

    interactive_sessions[user_id] = {'step': 'subtitle', 'mode': 'soft_code'}

    text = f"🫧 𝐘ᴜᴘᴘ...! <a href='tg://user?id={user_id}'>{user_name}</a>\n" \
           f"<blockquote expandable>🍃 𝐏ʟᴇᴀsᴇ 𝐒ᴇɴᴅ ʏᴏᴜʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ (.ass/.srt) to me! I'm good at my work.</blockquote>"

    buttons = [[InlineKeyboardButton("🗑️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_interactive")]]
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.document | filters.video)
async def document_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in interactive_sessions:
        return # Standard handler will take over or ignore

    session = interactive_sessions[user_id]

    if session['step'] == 'subtitle':
        if not message.document or not (message.document.file_name.endswith(".ass") or message.document.file_name.endswith(".srt")):
            await message.reply_text("Please send a valid .ass or .srt subtitle file!")
            return

        session['subtitle_msg'] = message
        session['step'] = 'video'
        buttons = [[InlineKeyboardButton("🗑️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_interactive")]]
        await message.reply_text("<blockquote expandable>🚀 Great! Now send the video file you want me to process. I'll handle the rest! 😉</blockquote>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif session['step'] == 'video':
        if not (message.video or (message.document and message.document.mime_type.startswith("video/"))):
            await message.reply_text("Please send a valid video file!")
            return

        session['video_msg'] = message

        # Now we have both files. Add to queue.
        # We'll use a special format in 'data' to pass both messages
        # We can pass the video message and attach the subtitle message to it
        video_msg = session['video_msg']
        video_msg.subtitle_msg = session['subtitle_msg']
        video_msg.interactive_mode = session['mode']

        data.append(video_msg)

        if len(data) == 1:
            from ..utils.tasks import handle_tasks
            await handle_tasks(video_msg, session['mode'])
        else:
            await message.reply("📔 Waiting for queue...")

        del interactive_sessions[user_id]
