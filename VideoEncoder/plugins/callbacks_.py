from ..utils.common import edit_msg


import datetime
import json
import os
import asyncio

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup

from .. import app, download_dir, log, owner, sudo_users, LOGGER, ASSETS_DIR
from ..plugins.queue import queue_answer
from ..utils.database.access_db import db
from ..utils.settings import (AudioSettings, ExtraSettings, OpenSettings,
                              VideoSettings)
from .start import showw_status, START_MSG, START_PIC
from ..utils.helper import check_chat
from ..utils.common import output, start_but, HELP_TEXT
from ..video_utils.audio_selector import sessions


@app.on_callback_query(filters.regex("^back_start$"))
async def back_to_start(bot: Client, cb: CallbackQuery):
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
    await cb.message.delete()

@app.on_callback_query(filters.regex("^(Video|Open|Audio|Extra)Settings$"))
async def settings_nav_handlers(bot: Client, cb: CallbackQuery):
    if cb.data == "VideoSettings":
        await VideoSettings(cb.message, user_id=cb.from_user.id)
    elif cb.data == "OpenSettings":
        await OpenSettings(cb.message, user_id=cb.from_user.id)
    elif cb.data == "AudioSettings":
        await AudioSettings(cb.message, user_id=cb.from_user.id)
    elif cb.data == "ExtraSettings":
        await ExtraSettings(cb.message, user_id=cb.from_user.id)

@app.on_callback_query(filters.regex("^trigger"))
async def settings_trigger_handlers(bot: Client, cb: CallbackQuery):
    user_id = cb.from_user.id
    if cb.data == "triggerMode":
        drive = await db.get_drive(user_id)
        await db.set_drive(user_id, not drive)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerUploadMode":
        upload_as_doc = await db.get_upload_as_doc(user_id)
        await db.set_upload_as_doc(user_id, not upload_as_doc)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerResize":
        resize = await db.get_resize(user_id)
        await db.set_resize(user_id, not resize)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerMetadata":
        metadata = await db.get_metadata_w(user_id)
        await db.set_metadata_w(user_id, not metadata)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerVideo":
        watermark = await db.get_watermark(user_id)
        await db.set_watermark(user_id, not watermark)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerHardsub":
        hardsub = await db.get_hardsub(user_id)
        await db.set_hardsub(user_id, not hardsub)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerSubtitles":
        subtitles = await db.get_subtitles(user_id)
        await db.set_subtitles(user_id, not subtitles)
        await ExtraSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerextensions":
        ex = await db.get_extensions(user_id)
        new_ex = 'MKV' if ex == 'MP4' else 'AVI' if ex == 'MKV' else 'MP4'
        await db.set_extensions(user_id, new_ex)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerframe":
        fr = await db.get_frame(user_id)
        frames = ['ntsc', 'source', 'pal', 'film', '23.976', '30', '60']
        try:
            idx = frames.index(fr)
            new_fr = frames[(idx + 1) % len(frames)]
        except ValueError:
            new_fr = 'ntsc'
        await db.set_frame(user_id, new_fr)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerPreset":
        p = await db.get_preset(user_id)
        presets = ['uf', 'sf', 'vf', 'f', 'm', 's']
        try:
            idx = presets.index(p)
            new_p = presets[(idx + 1) % len(presets)]
        except ValueError:
            new_p = 'uf'
        await db.set_preset(user_id, new_p)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggersamplerate":
        sr = await db.get_samplerate(user_id)
        new_sr = '48K' if sr == '44.1K' else 'source' if sr == '48K' else '44.1K'
        await db.set_samplerate(user_id, new_sr)
        await AudioSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerbitrate":
        bit = await db.get_bitrate(user_id)
        bits = ['400', '320', '256', '224', '192', '160', '128', 'source']
        try:
            idx = bits.index(bit)
            new_bit = bits[(idx + 1) % len(bits)]
        except ValueError:
            new_bit = '400'
        await db.set_bitrate(user_id, new_bit)
        await AudioSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerAudioCodec":
        a = await db.get_audio(user_id)
        codecs = ['dd', 'copy', 'aac', 'opus', 'alac', 'vorbis']
        try:
            idx = codecs.index(a)
            new_a = codecs[(idx + 1) % len(codecs)]
        except ValueError:
            new_a = 'dd'
        await db.set_audio(user_id, new_a)
        await AudioSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerAudioChannels":
        c = await db.get_channels(user_id)
        channels = ['source', '1.0', '2.0', '2.1', '5.1', '7.1']
        try:
            idx = channels.index(c)
            new_c = channels[(idx + 1) % len(channels)]
            if new_c == '7.1':
                 await cb.answer("7.1 is for bluray only.", show_alert=True)
        except ValueError:
            new_c = 'source'
        await db.set_channels(user_id, new_c)
        await AudioSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerResolution":
        r = await db.get_resolution(user_id)
        res = ['OG', '1080', '720', '480', '576']
        try:
            idx = res.index(r)
            new_r = res[(idx + 1) % len(res)]
        except ValueError:
            new_r = 'OG'
        await db.set_resolution(user_id, new_r)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerBits":
        b = await db.get_bits(user_id)
        hevc = await db.get_hevc(user_id)
        if hevc:
            await db.set_bits(user_id, not b)
        else:
            if b:
                await db.set_bits(user_id, False)
            else:
                await cb.answer("H264 don't support 10 bits in this bot.", show_alert=True)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerHevc":
        hevc = await db.get_hevc(user_id)
        await db.set_hevc(user_id, not hevc)
        if not hevc:
             await cb.answer("H265 need more time for encoding video", show_alert=True)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggertune":
        tune = await db.get_tune(user_id)
        await db.set_tune(user_id, not tune)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerreframe":
        rf = await db.get_reframe(user_id)
        reframes = ['4', '8', '16', 'pass']
        try:
            idx = reframes.index(rf)
            new_rf = reframes[(idx + 1) % len(reframes)]
            if new_rf == '16':
                await cb.answer("Reframe 16 maybe not support", show_alert=True)
        except ValueError:
            new_rf = '4'
        await db.set_reframe(user_id, new_rf)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggercabac":
        cabac = await db.get_cabac(user_id)
        await db.set_cabac(user_id, not cabac)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggeraspect":
        aspect = await db.get_aspect(user_id)
        await db.set_aspect(user_id, not aspect)
        if not aspect:
             await cb.answer("This will help to force video to 16:9", show_alert=True)
        await VideoSettings(cb.message, user_id=user_id)

    elif cb.data == "triggerCRF":
        crf = await db.get_crf(user_id)
        nextcrf = int(crf) + 1
        if nextcrf > 30:
            await db.set_crf(user_id, 18)
        else:
            await db.set_crf(user_id, nextcrf)
        await VideoSettings(cb.message, user_id=user_id)

@app.on_callback_query(filters.regex("^(set|del|how|back)_watermark$"))
async def watermark_handlers(bot: Client, cb: CallbackQuery):
    from .watermark import watermark_sessions, WATERMARK_PIC
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
        await cb.message.delete()

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
        watermark_path = os.path.join(ASSETS_DIR, f"watermark_{user_id}.png")
        has_watermark = os.path.exists(watermark_path)
        text = "> <b>\"ᴡᴀɴɴᴀ sᴛᴀᴍᴘ ʏᴏᴜʀ ᴀᴜᴛʜᴏʀɪᴛʏ? ᴀᴅᴅ ᴀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴀɴᴅ ʟᴇᴛ ᴛʜᴇ ᴡᴏʀʟᴅ ᴋɴᴏᴡ ᴡʜᴏ ᴛʜᴇ ʙᴏss ɪs!\"</b>"
        btn_text = "🔄 ᴄʜᴀɴɢᴇ ᴡᴀᴛᴇʀᴍᴀʀᴋ" if has_watermark else "🖼️ sᴇᴛ ᴡᴀᴛᴇʀᴍᴀʀᴋ"
        buttons = [
            [InlineKeyboardButton(btn_text, callback_data="set_watermark")],
            [
                InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="del_watermark"),
                InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_btn")
            ],
            [
                InlineKeyboardButton("❓ ʜᴏᴡ ᴛᴏ sᴇᴛ ᴡᴀᴛᴇʀᴍᴀʀᴋ", callback_data="how_watermark")
            ]
        ]
        try:
            await edit_msg(
                cb.message,
                media=InputMediaPhoto(WATERMARK_PIC, caption=text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(cb.message, caption=text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^metadata_"))
async def metadata_handlers(bot: Client, cb: CallbackQuery):
    from .metadata_plugin import update_metadata_msg
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
                    "- ᴀᴜᴛʜᴏʀ: The creator or owner of the media.\n" \
                    "- ᴀʀᴛɪꜱᴛ: The artist associated with the media.\n" \
                    "- ᴀᴜᴅɪᴏ: Title or description of audio content.\n" \
                    "- ꜱᴜʙᴛɪᴛʟᴇ: Title of subtitle content.\n" \
                    "- ᴠɪᴅᴇᴏ: Title or description of video content.\n\n" \
                    "ᴄᴏᴍᴍᴀɴᴅꜱ ᴛᴏ ᴛᴜʀɴ ᴏɴ ᴏғғ ᴍᴇᴛᴀᴅᴀᴛᴀ:\n" \
                    "➜ /metadata: Turn on or off metadata.\n\n" \
                    "ᴄᴏᴍᴍᴀɴᴅꜱ ᴛᴏ ꜱᴇᴛ ᴍᴇᴛᴀᴅᴀᴛᴀ:\n" \
                    "➜ /settitle: Set a custom title of media.\n" \
                    "➜ /setauthor: Set the author.\n" \
                    "➜ /setartist: Set the artist.\n" \
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
    font_name = cb.data.split("_")[-1]
    await db.set_user_font(cb.from_user.id, font_name)
    await cb.answer(f"Font set to {font_name}!", show_alert=True)

@app.on_callback_query(filters.regex("^(close_fonts|close_translator)$"))
async def close_specific_menus(bot: Client, cb: CallbackQuery):
    await cb.message.delete()

@app.on_callback_query(filters.regex("^(trans_llama33_groq|how_to_translate|help_callback)$"))
async def translator_ui_handlers(bot: Client, cb: CallbackQuery):
    from .translator import process_translation
    if cb.data == "trans_llama33_groq":
        await process_translation(bot, cb, "groq", "llama-3.3-70b-versatile")
    elif cb.data in ["how_to_translate", "help_callback"]:
        help_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Back to Home", callback_data="back_start"),
                InlineKeyboardButton("❌ Close", callback_data="close_btn")
            ]
        ])
        try:
            await edit_msg(
                cb.message,
                media=InputMediaPhoto(START_PIC, caption=HELP_TEXT, has_spoiler=True),
                reply_markup=help_buttons
            )
        except Exception as e:
            LOGGER.error(f"Error in {cb.data}: {e}")
            await edit_msg(cb.message, caption=HELP_TEXT, reply_markup=help_buttons)

@app.on_callback_query(filters.regex("^cancel"))
async def cancel_handlers(bot: Client, cb: CallbackQuery):
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
    user_id = cb.from_user.id
    if user_id in sessions:
        await sessions[user_id].resolve_callback(cb)
    else:
        await cb.answer("Session expired. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("stats"))
async def stats_callback_handler(bot: Client, cb: CallbackQuery):
    stats = await showw_status(bot)
    stats = stats.replace('<b>', '').replace('</b>', '')
    await cb.answer(stats, show_alert=True)

@app.on_callback_query(filters.regex(r"queue\+"))
async def queue_callback_handler(bot: Client, cb: CallbackQuery):
    await queue_answer(app, cb)

@app.on_callback_query(filters.regex("^Watermark$"))
async def watermark_placeholder(bot: Client, cb: CallbackQuery):
    await cb.answer("Sir, this button not works XD\n\nPress Bottom Buttons.", show_alert=True)
