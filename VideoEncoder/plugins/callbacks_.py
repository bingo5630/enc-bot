from ..utils.common import edit_msg


import datetime
import json
import os
import asyncio

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup

from .. import app, download_dir, log, owner, sudo_users, LOGGER
from ..plugins.queue import queue_answer
from ..utils.database.access_db import db
from ..utils.settings import (AudioSettings, ExtraSettings, OpenSettings,
                              VideoSettings)
from .start import showw_status, START_MSG, START_PIC
from ..utils.helper import check_chat
from ..utils.common import output, start_but, HELP_TEXT
from ..video_utils.audio_selector import sessions


@app.on_callback_query(filters.regex("main_menu"))
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

@app.on_callback_query(filters.regex("close_msg"))
async def delete_msg(bot: Client, cb: CallbackQuery):
    await cb.message.delete()

@app.on_callback_query()
async def callback_handlers(bot: Client, cb: CallbackQuery):
    try:
        # Import plugins on demand to avoid circular imports if any
        from .watermark import watermark_sessions, WATERMARK_PIC
        from .interactive_handler import interactive_sessions
        from .metadata_plugin import update_metadata_msg
        from .translator import process_translation

        # Settings

        if cb.data == "VideoSettings":
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "OpenSettings":
            await OpenSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "AudioSettings":
            await AudioSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "ExtraSettings":
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "triggerMode":
            if await db.get_drive(cb.from_user.id) is True:
                await db.set_drive(cb.from_user.id, drive=False)
            else:
                await db.set_drive(cb.from_user.id, drive=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "triggerUploadMode":
            if await db.get_upload_as_doc(cb.from_user.id) is True:
                await db.set_upload_as_doc(cb.from_user.id, upload_as_doc=False)
            else:
                await db.set_upload_as_doc(cb.from_user.id, upload_as_doc=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "triggerResize":
            if await db.get_resize(cb.from_user.id) is True:
                await db.set_resize(cb.from_user.id, resize=False)
            else:
                await db.set_resize(cb.from_user.id, resize=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        # Watermark
        elif cb.data == "Watermark":
            await cb.answer("Sir, this button not works XD\n\nPress Bottom Buttons.", show_alert=True)

        # Metadata
        elif cb.data == "triggerMetadata":
            if await db.get_metadata_w(cb.from_user.id):
                await db.set_metadata_w(cb.from_user.id, metadata=False)
            else:
                await db.set_metadata_w(cb.from_user.id, metadata=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        # Watermark
        elif cb.data == "triggerVideo":
            if await db.get_watermark(cb.from_user.id):
                await db.set_watermark(cb.from_user.id, watermark=False)
            else:
                await db.set_watermark(cb.from_user.id, watermark=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        # Subtitles
        elif cb.data == "triggerHardsub":
            if await db.get_hardsub(cb.from_user.id):
                await db.set_hardsub(cb.from_user.id, hardsub=False)
            else:
                await db.set_hardsub(cb.from_user.id, hardsub=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "triggerSubtitles":
            if await db.get_subtitles(cb.from_user.id):
                await db.set_subtitles(cb.from_user.id, subtitles=False)
            else:
                await db.set_subtitles(cb.from_user.id, subtitles=True)
            await ExtraSettings(cb.message, user_id=cb.from_user.id)

        # Extension
        elif cb.data == "triggerextensions":
            ex = await db.get_extensions(cb.from_user.id)
            if ex == 'MP4':
                await db.set_extensions(cb.from_user.id, extensions='MKV')
            elif ex == 'MKV':
                await db.set_extensions(cb.from_user.id, extensions='AVI')
            else:
                await db.set_extensions(cb.from_user.id, extensions='MP4')
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Frame
        elif cb.data == "triggerframe":
            fr = await db.get_frame(cb.from_user.id)
            if fr == 'ntsc':
                await db.set_frame(cb.from_user.id, frame='source')
            elif fr == 'source':
                await db.set_frame(cb.from_user.id, frame='pal')
            elif fr == 'pal':
                await db.set_frame(cb.from_user.id, frame='film')
            elif fr == 'film':
                await db.set_frame(cb.from_user.id, frame='23.976')
            elif fr == '23.976':
                await db.set_frame(cb.from_user.id, frame='30')
            elif fr == '30':
                await db.set_frame(cb.from_user.id, frame='60')
            else:
                await db.set_frame(cb.from_user.id, frame='ntsc')
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Preset
        elif cb.data == "triggerPreset":
            p = await db.get_preset(cb.from_user.id)
            if p == 'uf':
                await db.set_preset(cb.from_user.id, preset='sf')
            elif p == 'sf':
                await db.set_preset(cb.from_user.id, preset='vf')
            elif p == 'vf':
                await db.set_preset(cb.from_user.id, preset='f')
            elif p == 'f':
                await db.set_preset(cb.from_user.id, preset='m')
            elif p == 'm':
                await db.set_preset(cb.from_user.id, preset='s')
            else:
                await db.set_preset(cb.from_user.id, preset='uf')
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # sample rate
        elif cb.data == "triggersamplerate":
            sr = await db.get_samplerate(cb.from_user.id)
            if sr == '44.1K':
                await db.set_samplerate(cb.from_user.id, sample='48K')
            elif sr == '48K':
                await db.set_samplerate(cb.from_user.id, sample='source')
            else:
                await db.set_samplerate(cb.from_user.id, sample='44.1K')
            await AudioSettings(cb.message, user_id=cb.from_user.id)

        # bitrate
        elif cb.data == "triggerbitrate":
            bit = await db.get_bitrate(cb.from_user.id)
            if bit == '400':
                await db.set_bitrate(cb.from_user.id, bitrate='320')
            elif bit == '320':
                await db.set_bitrate(cb.from_user.id, bitrate='256')
            elif bit == '256':
                await db.set_bitrate(cb.from_user.id, bitrate='224')
            elif bit == '224':
                await db.set_bitrate(cb.from_user.id, bitrate='192')
            elif bit == '192':
                await db.set_bitrate(cb.from_user.id, bitrate='160')
            elif bit == '160':
                await db.set_bitrate(cb.from_user.id, bitrate='128')
            elif bit == '128':
                await db.set_bitrate(cb.from_user.id, bitrate='source')
            else:
                await db.set_bitrate(cb.from_user.id, bitrate='400')
            await AudioSettings(cb.message, user_id=cb.from_user.id)

        # Audio Codec
        elif cb.data == "triggerAudioCodec":
            a = await db.get_audio(cb.from_user.id)
            if a == 'dd':
                await db.set_audio(cb.from_user.id, audio='copy')
            elif a == 'copy':
                await db.set_audio(cb.from_user.id, audio='aac')
            elif a == 'aac':
                await db.set_audio(cb.from_user.id, audio='opus')
            elif a == 'opus':
                await db.set_audio(cb.from_user.id, audio='alac')
            elif a == 'alac':
                await db.set_audio(cb.from_user.id, audio='vorbis')
            else:
                await db.set_audio(cb.from_user.id, audio='dd')
            await AudioSettings(cb.message, user_id=cb.from_user.id)

        # Audio Channel
        elif cb.data == "triggerAudioChannels":
            c = await db.get_channels(cb.from_user.id)
            if c == 'source':
                await db.set_channels(cb.from_user.id, channels='1.0')
            elif c == '1.0':
                await db.set_channels(cb.from_user.id, channels='2.0')
            elif c == '2.0':
                await db.set_channels(cb.from_user.id, channels='2.1')
            elif c == '2.1':
                await db.set_channels(cb.from_user.id, channels='5.1')
            elif c == '5.1':
                await cb.answer("7.1 is for bluray only.", show_alert=True)
                await db.set_channels(cb.from_user.id, channels='7.1')
            else:
                await db.set_channels(cb.from_user.id, channels='source')
            await AudioSettings(cb.message, user_id=cb.from_user.id)

        # Resolution
        elif cb.data == "triggerResolution":
            r = await db.get_resolution(cb.from_user.id)
            if r == 'OG':
                await db.set_resolution(cb.from_user.id, resolution='1080')
            elif r == '1080':
                await db.set_resolution(cb.from_user.id, resolution='720')
            elif r == '720':
                await db.set_resolution(cb.from_user.id, resolution='480')
            elif r == '480':
                await db.set_resolution(cb.from_user.id, resolution='576')
            else:
                await db.set_resolution(cb.from_user.id, resolution='OG')
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Video Bits
        elif cb.data == "triggerBits":
            b = await db.get_bits(cb.from_user.id)
            if await db.get_hevc(cb.from_user.id):
                if b:
                    await db.set_bits(cb.from_user.id, bits=False)
                else:
                    await db.set_bits(cb.from_user.id, bits=True)
            else:
                if b:
                    await db.set_bits(cb.from_user.id, bits=False)
                else:
                    await cb.answer("H264 don't support 10 bits in this bot.",
                                    show_alert=True)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # HEVC
        elif cb.data == "triggerHevc":
            if await db.get_hevc(cb.from_user.id):
                await db.set_hevc(cb.from_user.id, hevc=False)
            else:
                await db.set_hevc(cb.from_user.id, hevc=True)
                await cb.answer("H265 need more time for encoding video", show_alert=True)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Tune
        elif cb.data == "triggertune":
            if await db.get_tune(cb.from_user.id):
                await db.set_tune(cb.from_user.id, tune=False)
            else:
                await db.set_tune(cb.from_user.id, tune=True)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Reframe
        elif cb.data == "triggerreframe":
            rf = await db.get_reframe(cb.from_user.id)
            if rf == '4':
                await db.set_reframe(cb.from_user.id, reframe='8')
            elif rf == '8':
                await db.set_reframe(cb.from_user.id, reframe='16')
                await cb.answer("Reframe 16 maybe not support", show_alert=True)
            elif rf == '16':
                await db.set_reframe(cb.from_user.id, reframe='pass')
            else:
                await db.set_reframe(cb.from_user.id, reframe='4')
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # CABAC
        elif cb.data == "triggercabac":
            if await db.get_cabac(cb.from_user.id):
                await db.set_cabac(cb.from_user.id, cabac=False)
            else:
                await db.set_cabac(cb.from_user.id, cabac=True)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Aspect
        elif cb.data == "triggeraspect":
            if await db.get_aspect(cb.from_user.id):
                await db.set_aspect(cb.from_user.id, aspect=False)
            else:
                await db.set_aspect(cb.from_user.id, aspect=True)
                await cb.answer("This will help to force video to 16:9", show_alert=True)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        elif cb.data == "triggerCRF":
            crf = await db.get_crf(cb.from_user.id)
            nextcrf = int(crf) + 1
            if nextcrf > 30:
                await db.set_crf(cb.from_user.id, crf=18)
            else:
                await db.set_crf(cb.from_user.id, crf=nextcrf)
            await VideoSettings(cb.message, user_id=cb.from_user.id)

        # Audio Selector Callbacks
        elif "audiosel" in cb.data:
            user_id = cb.from_user.id
            if user_id in sessions:
                await sessions[user_id].resolve_callback(cb)
            else:
                await cb.answer("Session expired. Please try again.", show_alert=True)

        # Cancel

        elif cb.data == "cancel":
            status = download_dir + "status.json"
            try:
                with open(status, 'r+') as f:
                    statusMsg = json.load(f)
                    user = cb.from_user.id
                    if user != statusMsg['user']:
                        if user == 885190545:
                            pass
                        elif user in sudo_users or user in owner:
                            pass
                        else:
                            return
                    statusMsg['running'] = False
                    f.seek(0)
                    json.dump(statusMsg, f, indent=2)
                    os.remove('VideoEncoder/utils/extras/downloads/process.txt')
                    try:
                        await edit_msg(cb.message, text="🚦🚦 Process Cancelled 🚦🚦")
                        chat_id = log
                        utc_now = datetime.datetime.utcnow()
                        ist_now = utc_now + \
                            datetime.timedelta(minutes=30, hours=5)
                        ist = ist_now.strftime("%d/%m/%Y, %H:%M:%S")
                        bst_now = utc_now + \
                            datetime.timedelta(minutes=00, hours=6)
                        bst = bst_now.strftime("%d/%m/%Y, %H:%M:%S")
                        now = f"\n{ist} (GMT+05:30)`\n`{bst} (GMT+06:00)"
                        await bot.send_message(chat_id, f"**Last Process Cancelled, Bot is Free Now !!** \n\nProcess Done at `{now}`", parse_mode="markdown")
                    except:
                        pass
            except FileNotFoundError:
                 await cb.answer("Nothing to cancel or process already finished!", show_alert=True)

        # Mode
        elif cb.data == "mode_video":
            await db.set_upload_as_doc(cb.from_user.id, False)
            await cb.answer("ᴘʀᴇғᴇʀᴇɴᴄᴇ sᴇᴛ ᴛᴏ ᴠɪᴅᴇᴏ", show_alert=True)
            await cb.message.delete()

        elif cb.data == "mode_document":
            await db.set_upload_as_doc(cb.from_user.id, True)
            await cb.answer("ᴘʀᴇғᴇʀᴇɴᴄᴇ sᴇᴛ ᴛᴏ ᴅᴏᴄᴜᴍᴇɴᴛ", show_alert=True)
            await cb.message.delete()

        # Watermark
        elif cb.data == "set_watermark":
            await cb.answer("ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴘʜᴏᴛᴏ ᴡɪᴛʜɪɴ 30 sᴇᴄᴏɴᴅs.", show_alert=True)
            watermark_sessions[cb.from_user.id] = asyncio.get_event_loop().time()
            await cb.message.reply_text("<b>ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴡᴀᴛᴇʀᴍᴀʀᴋ ᴘʜᴏᴛᴏ ᴡɪᴛʜɪɴ 30 sᴇᴄᴏɴᴅs.</b>")

        elif cb.data == "del_watermark":
            path = os.path.join(ASSETS_DIR, f"watermark_{cb.from_user.id}.png")
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
                    InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="main_menu"),
                    InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back_watermark")
                ],
                [
                    InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_msg")
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
            user_id = cb.from_user.id
            watermark_path = os.path.join(ASSETS_DIR, f"watermark_{user_id}.png")
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
                    InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_msg")
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

        # Metadata
        elif cb.data == "metadata_on":
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
                    InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="main_menu"),
                    InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="metadata_back")
                ],
                [
                    InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_msg")
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

        # Interactive Cancel
        elif cb.data == "cancel_interactive":
            user_id = cb.from_user.id
            if user_id in interactive_sessions:
                del interactive_sessions[user_id]
            await cb.answer("ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ!", show_alert=True)
            await cb.message.delete()

        # Stats
        elif 'stats' in cb.data:
            stats = await showw_status(bot)
            stats = stats.replace('<b>', '')
            stats = stats.replace('</b>', '')
            await cb.answer(stats, show_alert=True)

        # Queue
        elif "queue+" in cb.data:
            await queue_answer(app, cb)

        # Font Selection Callbacks
        elif cb.data.startswith("set_font_"):
            font_name = cb.data.split("_")[-1]
            await db.set_user_font(cb.from_user.id, font_name)
            await cb.answer(f"Font set to {font_name}!", show_alert=True)

        elif cb.data == "close_fonts":
            await cb.message.delete()

        # Translator Callbacks


        elif cb.data == "trans_llama33_groq":
            await process_translation(bot, cb, "groq", "llama-3.3-70b-versatile")

        elif cb.data == "close_translator":
            await cb.message.delete()

        elif cb.data in ["how_to_translate", "help_callback"]:
            help_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔙 Back to Home", callback_data="main_menu"),
                    InlineKeyboardButton("❌ Close", callback_data="close_msg")
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

    except Exception as e:
        LOGGER.error(f"Error in callback_handlers: {e}")
        try:
            await cb.answer("An error occurred. Please try again later.", show_alert=True)
        except:
            pass
