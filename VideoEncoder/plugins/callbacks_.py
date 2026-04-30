import asyncio
import os
import json
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from .. import app

@app.on_callback_query()
async def main_callback_handler(bot: Client, cb: CallbackQuery):
    # Immediate answer to dismiss the loading spinner
    await cb.answer()

    data = cb.data
    user_id = cb.from_user.id
    from .. import LOGGER
    LOGGER.info(f"Executing logic for: {data}")

    try:
        # 1. Back to Start / Home
        if data == "back_start":
            from .start import START_MSG, START_PIC
            from ..utils.common import start_but, edit_msg
            from .. import LOGGER
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
                await edit_msg(cb.message, caption=START_MSG.format(mention=mention), reply_markup=start_but)

        # 2. General Close Button
        elif data in ["close_btn", "closeMeh", "close_fonts", "close_translator", "close_meta"]:
            await cb.message.delete()

        elif data == "help_callback":
            from ..utils.common import HELP_TEXT, edit_msg
            from .start import START_PIC
            buttons = [
                [
                    InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data="back_start"),
                    InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="closeMeh")
                ]
            ]
            await edit_msg(cb.message, media=InputMediaPhoto(START_PIC, caption=HELP_TEXT, has_spoiler=True), reply_markup=InlineKeyboardMarkup(buttons))


        # 7. Font Setting
        elif data.startswith("set_font_"):
            from ..utils.database.access_db import db
            font_name = data.split("_")[-1]
            await db.set_user_font(user_id, font_name)

        # 8. Translation
        elif data == "trans_llama33_groq":
            from .translator import process_translation
            await process_translation(bot, cb, "groq", "llama-3.3-70b-versatile")

        elif data == "toggle_trans_engine":
            from ..utils.database.access_db import db
            from .translator import get_translate_buttons, TRANSLATE_TEXT
            from ..utils.common import edit_msg
            current_engine = await db.get_translation_engine(user_id)
            new_engine = "deepseek" if current_engine == "groq" else "groq"
            await db.set_translation_engine(user_id, new_engine)
            reply_markup = await get_translate_buttons(user_id)
            await edit_msg(cb.message, caption=TRANSLATE_TEXT, reply_markup=reply_markup)

        elif data == "start_trans_process":
            from .translator import process_translation
            await process_translation(bot, cb)

        # 9. Cancel Handlers
        elif data.startswith("cancel"):
            from ..utils.common import edit_msg
            from .. import download_dir, sudo_users, owner, log
            if data == "cancel":
                status_file = os.path.join(download_dir, "status.json")
                try:
                    with open(status_file, 'r+') as f:
                        statusMsg = json.load(f)
                        if user_id != statusMsg['user'] and user_id not in sudo_users and user_id not in owner:
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
                            now = f"\n{ist} (GMT+05:30)`"
                            await bot.send_message(chat_id, f"**Last Process Cancelled, Bot is Free Now !!** \n\nProcess Done at `{now}`", parse_mode="markdown")
                        except:
                            pass
                except FileNotFoundError:
                     pass
            elif data == "cancel_interactive":
                from .interactive_handler import interactive_sessions
                if user_id in interactive_sessions:
                    del interactive_sessions[user_id]
                await cb.message.delete()

        # 10. Mode Handlers
        elif data.startswith("mode_"):
            from ..utils.database.access_db import db
            if data == "mode_video":
                await db.set_upload_as_doc(user_id, False)
                await cb.message.delete()
            elif data == "mode_document":
                await db.set_upload_as_doc(user_id, True)
                await cb.message.delete()

        # 11. Audio Selection
        elif "audiosel" in data:
            from ..video_utils.audio_selector import sessions
            if user_id in sessions:
                await sessions[user_id].resolve_callback(cb)
            else:
                await cb.message.reply_text("Session expired. Please try again.")

        # 12. Stats
        elif data in ["stats", "show_stats"]:
            from .start import showw_status
            stats = await showw_status(bot)
            stats = stats.replace('<b>', '').replace('</b>', '')
            await cb.message.reply_text(stats)

        # 13. Queue
        elif "queue+" in data:
            from ..plugins.queue import queue_answer
            from .. import app
            await queue_answer(app, cb)

        # 14. Status Refresh
        elif data.startswith("status "):
            data_split = data.split()
            cmd = data_split[1]
            if cmd == 'ref':
                from .. import data as active_data, download_dir, botStartTime
                from ..utils.display_progress import humanbytes, TimeFormatter
                from .status import get_task_info
                from psutil import cpu_percent, virtual_memory, disk_usage, net_io_counters
                from time import time
                from ..utils.common import edit_msg

                count = len(active_data)
                cpu = cpu_percent()
                mem = virtual_memory().percent
                disk = disk_usage(download_dir).free
                upload_speed = humanbytes(net_io_counters().bytes_sent)
                download_speed = humanbytes(net_io_counters().bytes_recv)
                uptime = TimeFormatter(time() - botStartTime)

                msg = (
                    f'<b>System Status</b>\n'
                    f'<b>CPU:</b> {cpu}% | <b>RAM:</b> {mem}%\n'
                    f'<b>FREE:</b> {humanbytes(disk)}\n'
                    f'<b>UP:</b> {upload_speed} | <b>DL:</b> {download_speed}\n'
                    f'<b>Uptime:</b> {uptime}\n\n'
                )

                if count:
                    msg += f"<b>Active Tasks:</b> {count}\n"
                    for i, task_msg in enumerate(active_data):
                         info = get_task_info(task_msg)
                         msg += f"{i+1}. {info}\n"
                else:
                    msg += "No Active Downloads!\n"

                buttons = InlineKeyboardMarkup([[InlineKeyboardButton("ʀᴇғʀᴇsʜ", callback_data="status ref")]])
                try:
                    await edit_msg(cb.message, text=msg, reply_markup=buttons)
                except:
                    pass
    except Exception as e:
        from VideoEncoder import LOGGER
        LOGGER.error(f"Error in main_callback_handler: {e}")
