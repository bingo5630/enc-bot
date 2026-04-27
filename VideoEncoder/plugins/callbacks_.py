import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from .. import app


@app.on_callback_query(filters.regex("^back_start$"))
async def back_to_start(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .start import START_MSG, START_PIC
    from ..utils.common import start_but, edit_msg
    from .. import LOGGER
    print(f"DEBUG: Received callback data: {cb.data}")
    user = cb.from_user
    name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    mention = f"<a href='{link}'>{name}</a>"
    try:
        await edit_msg(
            cb.message,
            media=InputMediaPhoto(START_PIC, caption=START_MSG.format(mention=mention), has_spoiler=True),
            reply_markup=start_but
        )
    except Exception as e:
        LOGGER.error(f"Error in backToStart: {e}")
        await edit_msg(
            cb.message,
            caption=START_MSG.format(mention=mention),
            reply_markup=start_but
        )

@app.on_callback_query(filters.regex("^close_btn$"))
async def delete_msg(bot: Client, cb: CallbackQuery):
    await cb.answer()
    print(f"DEBUG: Received callback data: {cb.data}")
    await cb.message.delete()

@app.on_callback_query(filters.regex("^metadata_start$"))
async def metadata_start_callback(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .metadata_plugin import update_metadata_msg
    await update_metadata_msg(cb)

@app.on_callback_query(filters.regex("^watermark_start$"))
async def watermark_start_callback(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .watermark import get_watermark_menu, WATERMARK_PIC
    from ..utils.common import edit_msg
    text, reply_markup = await get_watermark_menu(cb.from_user.id)
    try:
        await edit_msg(
            cb.message,
            media=InputMediaPhoto(WATERMARK_PIC, caption=text, has_spoiler=True),
            reply_markup=reply_markup
        )
    except:
        await edit_msg(cb.message, caption=text, reply_markup=reply_markup)

@app.on_callback_query(filters.regex("^(set|del|how|back)_watermark$"))
async def watermark_handlers(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .watermark import watermark_sessions, WATERMARK_PIC, get_watermark_menu
    from ..utils.common import edit_msg
    from .. import ASSETS_DIR
    import os
    print(f"DEBUG: Received callback data: {cb.data}")
    user_id = cb.from_user.id
    if cb.data == "set_watermark":
        await cb.answer("ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴘʜᴏᴛᴏ ᴡɪᴛʜɪɴ 30 sᴇᴄᴏɴᴅs.", show_alert=True)
        watermark_sessions[user_id] = asyncio.get_event_loop().time()
        await cb.message.reply_text("<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴘʜᴏᴛᴏ ᴡɪᴛʜɪɴ 30 sᴇᴄᴏɴᴅs.</b>")

    elif cb.data == "del_watermark":
        path = os.path.join(ASSETS_DIR, f"watermark_{user_id}.png")
        if os.path.exists(path):
            os.remove(path)
            await cb.answer("ᴡᴀᴛᴇʀᴍᴀʀᴋ ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)
        else:
            await cb.answer("ɴᴏ ᴡᴀᴛᴇʀᴍᴀʀᴋ ғᴏᴜɴᴅ!", show_alert=True)
        text, reply_markup = await get_watermark_menu(user_id)
        await edit_msg(cb.message, caption=text, reply_markup=reply_markup)

    elif cb.data == "how_watermark":
        how_to_text = "<b>\"ᴅᴇᴋʜᴏ ʙʜᴀɪ, ᴡᴀᴛᴇʀᴍᴀʀᴋ ʟᴀɢᴀɴᴀ ɪs ʟɪᴋᴇ ᴀᴘɴɪ ɢᴀᴀᴅɪ ᴘᴇ ɴᴀᴀᴍ ʟɪᴋʜᴡᴀɴᴀ! ʙᴀs sᴇᴛ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀᴏ, ᴘʜᴏᴛᴏ ʙʜᴇᴊᴏ, ᴀᴜʀ ʙᴏᴍ! ᴀʙ ᴄʜᴏʀ ʙʜɪ ᴅᴀʀᴇɴɢᴇ ᴛᴇʀɪ ᴠɪᴅᴇᴏ ᴄʜᴜʀᴀɴᴇ sᴇ. ʜᴇʜᴇʜᴇ...\"</b>"
        buttons = [
            [
                InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="back_start"),
                InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_watermark")
            ],
            [
                InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_btn")
            ]
        ]
        try:
            await edit_msg(
                cb.message,
                media=InputMediaPhoto(WATERMARK_PIC, caption=how_to_text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(cb.message, caption=how_to_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif cb.data == "back_watermark":
        text, reply_markup = await get_watermark_menu(user_id)
        try:
            await edit_msg(
                cb.message,
                media=InputMediaPhoto(WATERMARK_PIC, caption=text, has_spoiler=True),
                reply_markup=reply_markup
            )
        except:
            await edit_msg(cb.message, caption=text, reply_markup=reply_markup)

@app.on_callback_query(filters.regex("^metadata_(on|off|how_to|back)$"))
async def metadata_handlers(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..utils.database.access_db import db
    from .metadata_plugin import update_metadata_msg
    from ..utils.common import edit_msg
    print(f"DEBUG: Received callback data: {cb.data}")
    if cb.data == "metadata_on":
        await db.set_metadata_on(cb.from_user.id, True)
        await cb.answer("ᴍᴇᴛᴀᴅᴀᴛᴀ ᴛᴜʀɴᴇᴅ ᴏɴ", show_alert=True)
        await update_metadata_msg(cb)

    elif cb.data == "metadata_off":
        await db.set_metadata_on(cb.from_user.id, False)
        await cb.answer("ᴍᴇᴛᴀᴅᴀᴛᴀ ᴛᴜʀɴᴇᴅ ᴏғғ", show_alert=True)
        await update_metadata_msg(cb)

    elif cb.data == "metadata_how_to":
        how_to_text = "ᴍᴀɴᴀɢɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ ғᴏʀ ʏᴏᴜʀ ᴠɪᴅᴇᴏs ᴀɴᴅ ғɪʟᴇs\n\n" \
                    "ᴠᴀʀɪᴏᴜꜱ ᴍᴇᴛᴀᴅᴀᴛᴀ:\n" \
                    "- ᴛɪᴛʟᴇ: Descriptive title of the media.\n" \
                    "- ᴀᴜᴅɪᴏ: Title or description of audio content.\n" \
                    "- ꜱᴜʙᴛɪᴛʟᴇ: Title of subtitle content.\n" \
                    "- ᴠɪᴅᴇᴏ: Title or description of video content.\n\n" \
                    "ᴄᴏᴍᴍᴀɴᴅꜱ ᴛᴏ ᴛᴜʀɴ ᴏɴ ᴏғғ ᴍᴇᴛᴀᴅᴀᴛᴀ:\n" \
                    "➜ /metadata: Turn on or off metadata.\n\n" \
                    "ᴄᴏᴍᴍᴀɴᴅꜱ ᴛᴏ ꜱᴇᴛ ᴍᴇᴛᴀᴅᴀᴛᴀ:\n" \
                    "➜ /settitle: Set a custom title of media.\n" \
                    "➜ /setaudio: Set audio title.\n" \
                    "➜ /setsubtitle: Set subtitle title.\n" \
                    "➜ /setvideo: Set video title.\n\n" \
                    "ᴇxᴀᴍᴘʟᴇ: /settitle Your Title Here\n\n" \
                    "ᴜꜱᴇ ᴛʜᴇꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ ᴛᴏ ᴇɴʀɪᴄʜ ʏᴏᴜʀ ᴍᴇᴅɪᴀ ᴡɪᴛʜ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ᴍᴇᴛᴀᴅᴀᴛᴀ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ!"
        buttons = [
            [
                InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="back_start"),
                InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="metadata_back")
            ],
            [
                InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_btn")
            ]
        ]
        try:
            await edit_msg(
                cb.message,
                media=InputMediaPhoto(
                    "https://graph.org/file/a232c9818402f81093feb-383081a21200f77ae8.jpg",
                    caption=how_to_text,
                    has_spoiler=True
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(cb.message, caption=how_to_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif cb.data == "metadata_back":
        await update_metadata_msg(cb)

@app.on_callback_query(filters.regex("^set_font_"))
async def set_font_handler(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..utils.database.access_db import db
    print(f"DEBUG: Received callback data: {cb.data}")
    font_name = cb.data.split("_")[-1]
    await db.set_user_font(cb.from_user.id, font_name)
    await cb.answer(f"Font set to {font_name}!", show_alert=True)

@app.on_callback_query(filters.regex("^(close_fonts|close_translator)$"))
async def close_specific_menus(bot: Client, cb: CallbackQuery):
    await cb.answer()
    print(f"DEBUG: Received callback data: {cb.data}")
    await cb.message.delete()

@app.on_callback_query(filters.regex("^(trans_llama33_groq)$"))
async def translator_ui_handlers(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .translator import process_translation
    print(f"DEBUG: Received callback data: {cb.data}")
    if cb.data == "trans_llama33_groq":
        await process_translation(bot, cb, "groq", "llama-3.3-70b-versatile")

@app.on_callback_query(filters.regex("^cancel"))
async def cancel_handlers(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..utils.common import edit_msg
    from .. import download_dir, sudo_users, owner, log
    import os, json, datetime
    print(f"DEBUG: Received callback data: {cb.data}")
    if cb.data == "cancel":
        status_file = download_dir + "status.json"
        try:
            with open(status_file, 'r+') as f:
                statusMsg = json.load(f)
                user = cb.from_user.id
                if user != statusMsg['user'] and user not in sudo_users and user not in owner:
                     return
                statusMsg['running'] = False
                f.seek(0)
                json.dump(statusMsg, f, indent=2)
                if os.path.exists('VideoEncoder/utils/extras/downloads/process.txt'):
                    os.remove('VideoEncoder/utils/extras/downloads/process.txt')
                try:
                    await edit_msg(cb.message, text="🚦🚦 Process Cancelled 🚦🚦")
                    chat_id = log
                    utc_now = datetime.datetime.utcnow()
                    ist_now = utc_now + datetime.timedelta(minutes=30, hours=5)
                    ist = ist_now.strftime("%d/%m/%Y, %H:%M:%S")
                    bst_now = utc_now + datetime.timedelta(minutes=00, hours=6)
                    bst = bst_now.strftime("%d/%m/%Y, %H:%M:%S")
                    now = f"\n{ist} (GMT+05:30)`\n`{bst} (GMT+06:00)"
                    await bot.send_message(chat_id, f"**Last Process Cancelled, Bot is Free Now !!** \n\nProcess Done at `{now}`", parse_mode="markdown")
                except:
                    pass
        except FileNotFoundError:
             await cb.answer("Nothing to cancel or process already finished!", show_alert=True)

    elif cb.data == "cancel_interactive":
        from .interactive_handler import interactive_sessions
        user_id = cb.from_user.id
        if user_id in interactive_sessions:
            del interactive_sessions[user_id]
        await cb.answer("ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!", show_alert=True)
        await cb.message.delete()

@app.on_callback_query(filters.regex("^mode_"))
async def mode_handlers(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..utils.database.access_db import db
    print(f"DEBUG: Received callback data: {cb.data}")
    if cb.data == "mode_video":
        await db.set_upload_as_doc(cb.from_user.id, False)
        await cb.answer("ᴘʀᴇғᴇʀᴇɴᴄᴇ sᴇᴛ ᴛᴏ ᴠɪᴅᴇᴏ", show_alert=True)
        await cb.message.delete()
    elif cb.data == "mode_document":
        await db.set_upload_as_doc(cb.from_user.id, True)
        await cb.answer("ᴘʀᴇғᴇʀᴇɴᴄᴇ sᴇᴛ ᴛᴏ ᴅᴏᴄᴜᴍᴇɴᴛ", show_alert=True)
        await cb.message.delete()

@app.on_callback_query(filters.regex("audiosel"))
async def audio_selector_handler(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..video_utils.audio_selector import sessions
    print(f"DEBUG: Received callback data: {cb.data}")
    user_id = cb.from_user.id
    if user_id in sessions:
        await sessions[user_id].resolve_callback(cb)
    else:
        await cb.answer("Session expired. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("stats"))
async def stats_callback_handler(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from .start import showw_status
    print(f"DEBUG: Received callback data: {cb.data}")
    stats = await showw_status(bot)
    stats = stats.replace('<b>', '').replace('</b>', '')
    await cb.answer(stats, show_alert=True)

@app.on_callback_query(filters.regex(r"queue\+"))
async def queue_callback_handler(bot: Client, cb: CallbackQuery):
    await cb.answer()
    from ..plugins.queue import queue_answer
    from .. import app
    print(f"DEBUG: Received callback data: {cb.data}")
    await queue_answer(app, cb)
