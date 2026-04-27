
import asyncio

SETTINGS_PIC = "https://i.ibb.co/xV675RQ/image.png"

# Settings
async def OpenSettings(event, user_id: int):
    from pyrogram.errors import FloodWait
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    from .common import edit_msg
    from .. import LOGGER
    try:
        text = 'Efficiency is doing things right; effectiveness is doing the right things.'
        buttons = [
            [
                InlineKeyboardButton("📖 How to Translate", callback_data="how_to_translate"),
                InlineKeyboardButton("🛠️ Metadata", callback_data="metadata_help")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close_btn")
            ]
        ]
        try:
            await edit_msg(
                event,
                media=InputMediaPhoto(SETTINGS_PIC, caption=text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(event, caption=text, reply_markup=InlineKeyboardMarkup(buttons))

    except FloodWait as e:
        await asyncio.sleep(e.x)
        await OpenSettings(event, user_id)
    except Exception as e:
        LOGGER.error(f"Error in OpenSettings: {e}")
        await edit_msg(event, caption=f"An error occurred in OpenSettings: {e}")


# Video Settings
async def VideoSettings(event, user_id: int):
    from pyrogram.errors import FloodWait
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    from .common import edit_msg
    from .database.access_db import db
    from .. import LOGGER
    try:
        user = await db.get_user_data(user_id)

        ex = user.get('extensions', 'MP4')
        if ex == 'MP4':
            extensions = 'ᴍᴘ4'
        elif ex == 'MKV':
            extensions = 'ᴍᴋᴠ'
        elif ex == 'AVI':
            extensions = 'ᴀᴠɪ'
        else:
            extensions = 'ᴍᴘ4'

        fr = user.get('frame', 'source')
        if fr == 'ntsc':
            frame = 'ɴᴛsᴄ'
        elif fr == 'pal':
            frame = 'ᴘᴀʟ'
        elif fr == 'film':
            frame = 'ғɪʟᴍ'
        elif fr == '23.976':
            frame = '23.976'
        elif fr == '30':
            frame = '30'
        elif fr == '60':
            frame = '60'
        elif fr == 'source':
            frame = 'sᴏᴜʀᴄᴇ'
        else:
            frame = 'sᴏᴜʀᴄᴇ'

        p = user.get('preset', 'sf')
        if p == 'uf':
            pre = 'ᴜʟᴛʀᴀғᴀsᴛ'
        elif p == 'sf':
            pre = 'sᴜᴘᴇʀғᴀsᴛ'
        elif p == 'vf':
            pre = 'ᴠᴇʀʏғᴀsᴛ'
        elif p == 'f':
            pre = 'ғᴀsᴛ'
        elif p == 'm':
            pre = 'ᴍᴇᴅɪᴜᴍ'
        elif p == 's':
            pre = 'sʟᴏᴡ'
        else:
            pre = 'ɴᴏɴᴇ'

        crf = user.get('crf', 18)

        r = user.get('resolution', 'OG')
        if r == 'OG':
            res = 'sᴏᴜʀᴄᴇ'
        elif r == '1080':
            res = '1080ᴘ'
        elif r == '720':
            res = '720ᴘ'
        elif r == '576':
            res = '576ᴘ'
        elif r == '480':
            res = '480ᴘ'
        else:
            res = 'sᴏᴜʀᴄᴇ'

        # Reframe
        rf = user.get('reframe', 'pass')
        if rf == '4':
            reframe = '4'
        elif rf == '8':
            reframe = '8'
        elif rf == '16':
            reframe = '16'
        elif rf == 'pass':
            reframe = 'ᴘᴀss'
        else:
            reframe = 'ᴘᴀss'

        text = "Here's Your Video Settings"
        buttons = [
            [InlineKeyboardButton("ʙᴀsɪᴄ sᴇᴛᴛɪɴɢs", callback_data="ignore_callback")],
            [InlineKeyboardButton(f"ᴇxᴛ: {extensions} ", callback_data="triggerextensions"),
             InlineKeyboardButton(f"ʙɪᴛs: {'10' if (user.get('bits', False) is True) else '8'}", callback_data="triggerBits")],
            [InlineKeyboardButton(f"ᴄᴏᴅᴇᴄ: {'ʜ265' if (user.get('hevc', False) is True) else 'ʜ264'}", callback_data="triggerHevc"),
             InlineKeyboardButton(f"ᴄʀғ: {crf}", callback_data="triggerCRF")],
            [InlineKeyboardButton("ǫᴜᴀʟɪᴛʏ", callback_data="ignore_callback"),
             InlineKeyboardButton(f"{res}", callback_data="triggerResolution")],
            [InlineKeyboardButton("ᴛᴜɴᴇ", callback_data="ignore_callback"),
             InlineKeyboardButton(f"{'ᴀɴɪᴍᴀᴛɪᴏɴ' if (user.get('tune', False) is True) else 'ғɪʟᴍ'}", callback_data="triggertune")],
            [InlineKeyboardButton("ᴀᴅᴠᴀɴᴄᴇᴅ sᴇᴛᴛɪɴɢs", callback_data="ignore_callback")],
            [InlineKeyboardButton("ᴘʀᴇsᴇᴛ", callback_data="ignore_callback"),
             InlineKeyboardButton(f"{pre}", callback_data="triggerPreset")],
            [InlineKeyboardButton(f"ғᴘs: {frame}", callback_data="triggerframe"),
             InlineKeyboardButton(f"ᴀsᴘᴇᴄᴛ: {'16:9' if (user.get('aspect', False) is True) else 'sᴏᴜʀᴄᴇ'}", callback_data="triggeraspect")],
            [InlineKeyboardButton(f"ᴄᴀʙᴀᴄ {'☑️' if (user.get('cabac', False) is True) else ''}", callback_data="triggercabac"),
             InlineKeyboardButton(f"ʀᴇғʀᴀᴍᴇ: {reframe}", callback_data="triggerreframe")],
            [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="OpenSettings")]
        ]

        try:
            await edit_msg(
                event,
                media=InputMediaPhoto(SETTINGS_PIC, caption=text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(event, caption=text, reply_markup=InlineKeyboardMarkup(buttons))

    except FloodWait as e:
        await asyncio.sleep(e.x)
        await VideoSettings(event, user_id)
    except Exception as e:
        LOGGER.error(f"Error in VideoSettings: {e}")
        await edit_msg(event, caption=f"An error occurred in VideoSettings: {e}")


async def AudioSettings(event, user_id: int):
    from pyrogram.errors import FloodWait
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    from .common import edit_msg
    from .database.access_db import db
    from .. import LOGGER
    try:
        user = await db.get_user_data(user_id)

        a = user.get('audio', 'dd')
        if a == 'dd':
            audio = 'ᴀᴄ3'
        elif a == 'aac':
            audio = 'ᴀᴀᴄ'
        elif a == 'opus':
            audio = 'ᴏᴘᴜs'
        elif a == 'vorbis':
            audio = 'ᴠᴏʀʙɪs'
        elif a == 'alac':
            audio = 'ᴀʟᴀᴄ'
        elif a == 'copy':
            audio = 'sᴏᴜʀᴄᴇ'
        else:
            audio = 'ɴᴏɴᴇ'

        bit = user.get('bitrate', 'source')
        if bit == '400':
            bitrate = '400ᴋ'
        elif bit == '320':
            bitrate = '320ᴋ'
        elif bit == '256':
            bitrate = '256ᴋ'
        elif bit == '224':
            bitrate = '224ᴋ'
        elif bit == '192':
            bitrate = '192ᴋ'
        elif bit == '160':
            bitrate = '160ᴋ'
        elif bit == '128':
            bitrate = '128ᴋ'
        elif bit == 'source':
            bitrate = 'sᴏᴜʀᴄᴇ'
        else:
            bitrate = 'sᴏᴜʀᴄᴇ'

        sr = user.get('sample', 'source')
        if sr == '44.1K':
            sample = '44.1ᴋʜᴢ'
        elif sr == '48K':
            sample = '48ᴋʜᴢ'
        elif sr == 'source':
            sample = 'sᴏᴜʀᴄᴇ'
        else:
            sample = 'sᴏᴜʀᴄᴇ'

        c = user.get('channels', 'source')
        if c == '1.0':
            channels = 'ᴍᴏɴᴏ'
        elif c == '2.0':
            channels = 'sᴛᴇʀᴇᴏ'
        elif c == '2.1':
            channels = '2.1'
        elif c == '5.1':
            channels = '5.1'
        elif c == '7.1':
            channels = '7.1'
        elif c == 'source':
            channels = 'sᴏᴜʀᴄᴇ'
        else:
            channels = 'sᴏᴜʀᴄᴇ'

        text = "Here's Your Audio Settings"
        buttons = [
            [InlineKeyboardButton("ᴄᴏᴅᴇᴄ", callback_data="ignore_callback"), InlineKeyboardButton(
                f"{audio}", callback_data="triggerAudioCodec")],
            [InlineKeyboardButton("ᴄʜᴀɴɴᴇʟs", callback_data="ignore_callback"), InlineKeyboardButton(
                f"{channels}", callback_data="triggerAudioChannels")],
            [InlineKeyboardButton("sᴀᴍᴘʟᴇ ʀᴀᴛᴇ", callback_data="ignore_callback"), InlineKeyboardButton(
                f"{sample}", callback_data="triggersamplerate")],
            [InlineKeyboardButton("ʙɪᴛʀᴀᴛᴇ", callback_data="ignore_callback"), InlineKeyboardButton(
                f"{bitrate}", callback_data="triggerbitrate")],
            [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="OpenSettings")]
        ]

        try:
            await edit_msg(
                event,
                media=InputMediaPhoto(SETTINGS_PIC, caption=text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(event, caption=text, reply_markup=InlineKeyboardMarkup(buttons))

    except FloodWait as e:
        await asyncio.sleep(e.x)
        await AudioSettings(event, user_id)
    except Exception as e:
        LOGGER.error(f"Error in AudioSettings: {e}")
        await edit_msg(event, caption=f"An error occurred in AudioSettings: {e}")


async def ExtraSettings(event, user_id: int):
    from pyrogram.errors import FloodWait
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    from .common import edit_msg
    from .database.access_db import db
    from .. import LOGGER
    try:
        user = await db.get_user_data(user_id)
        text = "Here's Your Subtitle Settings"
        buttons = [
            [InlineKeyboardButton("sᴜʙᴛɪᴛʟᴇs sᴇᴛᴛɪɴɢs", callback_data="ignore_callback")],
            [InlineKeyboardButton(f"ʜᴀʀᴅsᴜʙ {'☑️' if (user.get('hardsub', False) is True) else ''}", callback_data="triggerHardsub"), InlineKeyboardButton(f"ᴄᴏᴘʏ {'☑️' if (user.get('subtitles', False) is True) else ''}", callback_data="triggerSubtitles")],
            [InlineKeyboardButton("ᴜᴘʟᴏᴀᴅ sᴇᴛᴛɪɴɢs", callback_data="ignore_callback")],
            [InlineKeyboardButton(f"{'ɢ-ᴅʀɪᴠᴇ' if (user.get('drive', False) is True) else 'ᴛᴇʟᴇɢʀᴀᴍ'}", callback_data="triggerMode"),
             InlineKeyboardButton(f"{'ᴅᴏᴄᴜᴍᴇɴᴛ' if (user.get('upload_as_doc', False) is True) else 'ᴠɪᴅᴇᴏ'}", callback_data="triggerUploadMode")],
            [InlineKeyboardButton("ᴡᴀᴛᴇʀᴍᴀʀᴋ sᴇᴛᴛɪɴɢs", callback_data="back_watermark")],
            [InlineKeyboardButton(f"ᴍᴇᴛᴀᴅᴀᴛᴀ {'☑️' if (user.get('metadata', False) is True) else ''}", callback_data="triggerMetadata"), InlineKeyboardButton(f"ᴠɪᴅᴇᴏ {'☑️' if (user.get('watermark', False) is True) else ''}", callback_data="triggerVideo")],
            [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="OpenSettings")]
        ]

        try:
            await edit_msg(
                event,
                media=InputMediaPhoto(SETTINGS_PIC, caption=text, has_spoiler=True),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            await edit_msg(event, caption=text, reply_markup=InlineKeyboardMarkup(buttons))

    except FloodWait as e:
        await asyncio.sleep(e.x)
        await ExtraSettings(event, user_id)
    except Exception as e:
        LOGGER.error(f"Error in ExtraSettings: {e}")
        await edit_msg(event, caption=f"An error occurred in ExtraSettings: {e}")
