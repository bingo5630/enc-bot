
import asyncio
import html
import os
import time
from datetime import datetime
from urllib.parse import unquote_plus

from httpx import delete
from pyrogram.errors.exceptions.bad_request_400 import MessageIdInvalid
from pyrogram.parser import html as pyrogram_html
from pyrogram.types import Message
from requests.utils import unquote

from .. import LOGGER, data, download_dir, encode_dir, video_mimetype
from ..video_utils.audio_selector import AudioSelect

async def handle_sub_extract(filepath, message, edit_msg):
    from .encoding import extract_subtitle
    from .uploads.telegram import upload_doc
    await edit_msg.edit("Processing... ⏳")
    result = await extract_subtitle(filepath)
    if os.path.isfile(result):
        try:
            await upload_doc(message, edit_msg, 0, os.path.basename(result), result)
            await edit_msg.edit("Subtitle extracted and uploaded successfully!")
        except Exception as e:
            await edit_msg.edit(f"Error while uploading: {e}")
        finally:
            if os.path.isfile(result):
                os.remove(result)
    else:
        await edit_msg.edit(f"Failed to extract subtitles: {result}")

    # Cleanup video file
    if os.path.isfile(filepath):
        os.remove(filepath)


async def handle_encode(filepath, message, edit_msg, audio_map=None, quality=None, custom_name=None):
    from .encoding import encode, extract_subs
    from .uploads import upload_worker
    from .database.access_db import db
    sub_path = os.path.join(encode_dir, str(edit_msg.id) + '.ass')
    new_file = None
    link = None
    try:
        if await db.get_hardsub(message.from_user.id):
            subs = await extract_subs(filepath, edit_msg, message.from_user.id)
            if not subs:
                await edit_msg.edit("Something went wrong while extracting the subtitles!")
                return
            # Move subs to expected location if it was from existing subs
            if subs != sub_path and os.path.exists(subs):
                os.rename(subs, sub_path)

        new_file, error_log = await encode(filepath, message, edit_msg, audio_map=audio_map, quality=quality, custom_name=custom_name)
        if new_file:
            # 1MB = 1048576 bytes
            if os.path.getsize(new_file) < 1048576:
                LOGGER.error(f"Encoded file is too small ({os.path.getsize(new_file)} bytes). FFmpeg likely failed.")
                error_file = f"ffmpeg_error_{edit_msg.id}.txt"
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(error_log or "Unknown FFmpeg error")
                await message.reply_document(error_file, caption="FFmpeg error log (Output file < 1MB)")
                if os.path.exists(error_file):
                    os.remove(error_file)
                if os.path.exists(new_file):
                    os.remove(new_file)
                new_file = None
            else:
                await edit_msg.edit("<code>Video Encoded, getting metadata...</code>")
                try:
                    link = await upload_worker(new_file, message, edit_msg)
                except Exception as e:
                    await edit_msg.edit(f"Error while uploading: {e}")
        else:
            error_file = f"ffmpeg_error_{edit_msg.id}.txt"
            with open(error_file, 'w', encoding='utf-8-sig') as f:
                f.write(error_log or "Something went wrong during encoding.")
            await message.reply_document(error_file, caption="Something went wrong while encoding your file.")
            if os.path.exists(error_file):
                os.remove(error_file)
        return link
    finally:
        # Robust cleanup
        if new_file and os.path.exists(new_file):
            try: os.remove(new_file)
            except: pass
        if filepath and os.path.exists(filepath):
            try: os.remove(filepath)
            except: pass
        if os.path.exists(sub_path):
            try: os.remove(sub_path)
            except: pass


async def handle_interactive_encode(video_path, sub_path, message, edit_msg, mode, quality=None):
    from .encoding import encode, hard_sub, soft_code
    from .uploads import upload_worker

    video_path = os.path.abspath(video_path)
    sub_path = os.path.abspath(sub_path)

    # Ensure sub_path is moved to encode_dir while preserving original filename
    sub_name = os.path.basename(sub_path)
    sub_dest = os.path.join(encode_dir, sub_name)
    if sub_path != sub_dest:
        if os.path.exists(sub_path):
            os.rename(sub_path, sub_dest)
        sub_path = sub_dest

    new_file = None
    error_log = None
    try:
        if mode == 'encode':
            new_file, error_log = await encode(video_path, message, edit_msg, quality=quality)
        elif mode == 'hard_sub':
            new_file, error_log = await hard_sub(video_path, sub_path, message, edit_msg, quality=quality)
        elif mode == 'soft_code':
            new_file, error_log = await soft_code(video_path, sub_path, message, edit_msg, quality=quality)
        else:
            new_file = None

        if new_file:
            # 1MB = 1048576 bytes
            if os.path.getsize(new_file) < 1048576:
                LOGGER.error(f"Processed file is too small ({os.path.getsize(new_file)} bytes). FFmpeg likely failed.")
                error_file = f"ffmpeg_error_{edit_msg.id}.txt"
                with open(error_file, 'w', encoding='utf-8-sig') as f:
                    f.write(error_log or "Unknown FFmpeg error")
                await message.reply_document(error_file, caption="FFmpeg error log (Output file < 1MB)")
                if os.path.exists(error_file):
                    os.remove(error_file)
                if os.path.exists(new_file):
                    os.remove(new_file)
                new_file = None
            else:
                await edit_msg.edit("<code>Process Completed, getting metadata...</code>")
                try:
                    await upload_worker(new_file, message, edit_msg)
                except Exception as e:
                    await edit_msg.edit(f"Error while uploading: {e}")
        else:
            error_file = f"ffmpeg_error_{edit_msg.id}.txt"
            with open(error_file, 'w', encoding='utf-8-sig') as f:
                f.write(error_log or "Something went wrong during processing.")
            await message.reply_document(error_file, caption="Something went wrong while processing your file.")
            if os.path.exists(error_file):
                os.remove(error_file)
    finally:
        # Cleanup
        if new_file and os.path.exists(new_file):
            try: os.remove(new_file)
            except: pass
        if video_path and os.path.exists(video_path):
            try: os.remove(video_path)
            except: pass
        if sub_path and os.path.exists(sub_path):
            try: os.remove(sub_path)
            except: pass

async def on_task_complete():
    if not data:
        return
    del data[0]
    if not len(data) > 0:
        from .helper import delete_downloads
        delete_downloads()
        return
    message = data[0]

    # Determine text content (message text or caption)
    text_content = message.text or message.caption

    if text_content:
        text_parts = text_content.split()
        command = text_parts[0].lower()

        custom_name = None
        if "-n" in text_content:
            parts = text_content.split("-n", 1)
            if len(parts) > 1:
                custom_name = os.path.basename(parts[1].strip())

        if '/ddl' in command:
            await handle_tasks(message, 'url')
        elif '/batch' in command:
            await handle_tasks(message, 'batch')
        elif '/dl' in command:
            await handle_tasks(message, 'tg')
        elif '/480p' in command:
            await handle_tasks(message, '480p', custom_name=custom_name)
        elif '/720p' in command:
            await handle_tasks(message, '720p', custom_name=custom_name)
        elif '/1080p' in command:
            await handle_tasks(message, '1080p', custom_name=custom_name)
        elif '/af' in command:
            await handle_tasks(message, 'af')
        elif '/sub_extract' in command:
            # Detect whether it was a file or url based on presence of text/caption and file
            has_file = (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)) or \
                       (message.video or message.document)
            mode = 'sub_tg' if has_file else 'sub_url'
            await handle_tasks(message, mode)
        else:
             # If has text but not a known command, check if it's a file
            if message.document or message.video:
                 if message.document and not message.document.mime_type in video_mimetype:
                    await on_task_complete()
                    return
                 await handle_tasks(message, 'tg')
            else:
                 # Just text, maybe a link but without command? Or unhandled
                 pass
    else:
        # Fallback for any other file message if somehow added
        if message.document:
            if not message.document.mime_type in video_mimetype:
                await on_task_complete()
                return
        await handle_tasks(message, 'tg')


async def handle_tasks(message, mode, msg=None, custom_name=None):
    try:
        if msg:
            edit_msg = msg
            await edit_msg.edit("<b>💠 Downloading...</b>")
        else:
            edit_msg = await message.reply_text("<b>💠 Downloading...</b>")

        if mode == 'tg':
            await tg_task(message, edit_msg)
        elif mode in ['480p', '720p', '1080p']:
            await tg_task(message, edit_msg, quality=mode, custom_name=custom_name)
        elif mode == 'url':
            await url_task(message, edit_msg)
        elif mode == 'af':
            await af_task(message, edit_msg)
        elif mode == 'sub_tg':
            await sub_tg_task(message, edit_msg)
        elif mode == 'sub_url':
            await sub_url_task(message, edit_msg)
        elif mode in ['encode', 'hard_sub', 'soft_code']:
            await interactive_task(message, edit_msg, mode)
        else:
            await batch_task(message, edit_msg)
    except IndexError:
        return
    except MessageIdInvalid:
        try: await edit_msg.edit(text='Download Cancelled!')
        except: pass
    except FileNotFoundError:
        LOGGER.error('[FileNotFoundError]: Maybe due to cancel, hmm')
        import traceback
        LOGGER.error(traceback.format_exc())
    except Exception as e:
        import traceback
        LOGGER.error(traceback.format_exc())
        await message.reply(text=f"Error! <code>{e}</code>")
    finally:
        await on_task_complete()


async def tg_task(message, edit_msg, quality=None, custom_name=None):
    filepath = await handle_tg_down(message, edit_msg)
    if not filepath:
        await edit_msg.edit(text="Download failed or no file found.")
        return
    await edit_msg.edit(text='<b>Download complete. Initializing encoder...</b>')
    await handle_encode(filepath, message, edit_msg, quality=quality, custom_name=custom_name)


async def sub_tg_task(message, edit_msg):
    filepath = await handle_tg_down(message, edit_msg)
    if not filepath:
        await edit_msg.edit(text="Download failed or no file found.")
        return
    await handle_sub_extract(filepath, message, edit_msg)


async def sub_url_task(message, edit_msg):
    filepath = await handle_download_url(message, edit_msg, False)
    if not filepath:
        return
    await handle_sub_extract(filepath, message, edit_msg)


async def interactive_task(message, edit_msg, mode):
    # message here is the video message which has subtitle_msg attached
    subtitle_msg = message.subtitle_msg

    # Download subtitle
    await edit_msg.edit(text="Downloading Subtitle...")
    sub_path = await subtitle_msg.download(file_name=os.path.join(download_dir, ""))

    # Download video
    await edit_msg.edit(text="Downloading Video...")
    video_path = await handle_tg_down(message, edit_msg)

    if not video_path or not sub_path:
        await edit_msg.edit(text="Download failed.")
        return

    await edit_msg.edit(text="<b>Download complete. Initializing encoder...</b>")
    await handle_interactive_encode(video_path, sub_path, message, edit_msg, mode)


async def af_task(message, edit_msg):
    from .encoding import get_media_streams
    filepath = await handle_tg_down(message, edit_msg)
    if not filepath:
        await edit_msg.edit(text="Download failed or no file found.")
        return

    # Probe for streams
    streams = get_media_streams(filepath)
    if not streams:
         await edit_msg.edit(text="Could not retrieve media streams.")
         return

    selector = AudioSelect(message._client, message)
    await edit_msg.delete() # Delete the downloading message as AudioSelect will send its own interface

    # AudioSelect expects streams list
    audio_map, _ = await selector.get_buttons(streams)

    if audio_map == -1:
        # Cancelled or error
        return

    # Proceed to encode with the new map
    edit_msg = await message.reply("Encoding with new audio arrangement...")
    await handle_encode(filepath, message, edit_msg, audio_map)


async def url_task(message, edit_msg):
    filepath = await handle_download_url(message, edit_msg, False)
    if not filepath:
        return
    await edit_msg.edit(text="<b>Download complete. Initializing encoder...</b>")
    await handle_encode(filepath, message, edit_msg)


async def batch_task(message, edit_msg):
    from .helper import get_zip_folder, handle_extract
    if message.reply_to_message:
        filepath = await handle_tg_down(message, edit_msg, mode='reply')
    else:
        filepath = await handle_download_url(message, edit_msg, True)
    if not filepath:
        await edit_msg.edit(text='NO ZIP FOUND!')
        return
    if os.path.isfile(filepath):
        path = await get_zip_folder(filepath)
        await handle_extract(filepath)
        if not os.path.isdir(path):
            await edit_msg.edit(text='extract failed!')
            return
        filepath = path
    if os.path.isdir(filepath):
        path = filepath
    else:
        await edit_msg.edit(text='Something went wrong, hell!')
        return
    await edit_msg.edit(text='<b>📕 Encode Started!</b>')
    sentfiles = []
    # Encode
    for dirpath, subdir, files_ in sorted(os.walk(path)):
        for i in sorted(files_):
            msg_ = await message.reply('Encoding')
            filepath = os.path.join(dirpath, i)
            await edit_msg.edit(text='Encode Started!\nEncoding: <code>{}</code>'.format(i))
            try:
                url = await handle_encode(filepath, message, msg_)
            except Exception as e:
                await msg_.edit(text=str(e) + '\n\n Continuing...')
                continue
            else:
                sentfiles.append((i, url))
    text = '✨ <b>#EncodedFiles:</b> \n\n'
    quote = None
    first_index = None
    all_amount = 1
    for filename, filelink in sentfiles:
        if filelink:
            atext = f'- <a href="{filelink}">{html.escape(filename)}</a>'
        else:
            atext = f'- {html.escape(filename)} (empty)'
        atext += '\n'
        futtext = text + atext
        if all_amount > 100:
            thing = await message.reply_text(text, quote=quote, disable_web_page_preview=True)
            if first_index is None:
                first_index = thing
            quote = False
            futtext = atext
            all_amount = 1
            await asyncio.sleep(3)
        all_amount += 1
        text = futtext
    if not sentfiles:
        text = 'Files: None'
    thing = await message.reply_text(text, quote=quote, disable_web_page_preview=True)
    if first_index is None:
        first_index = thing
    await edit_msg.edit(text='Encoded Files! Links: {}'.format(first_index.link), disable_web_page_preview=True)


async def handle_download_url(message, edit_msg, batch):
    from .helper import handle_url
    from .uploads.drive import _get_file_id
    from .uploads.drive.download import Downloader
    from .direct_link_generator import direct_link_generator
    url = message.text.split(None, 1)[1].strip()
    if 'drive.google.com' in url:
        file_id = _get_file_id(url)
        n = Downloader()
        custom_file_name = n.name(file_id)
    else:
        # Default filename from URL basename
        custom_file_name = unquote_plus(os.path.basename(url))

    if "|" in url and not batch:
        url, c_file_name = url.split("|", maxsplit=1)
        url = url.strip()
        if c_file_name:
            custom_file_name = c_file_name.strip()
    elif " " in url and not batch:
        # Attempt to handle space-separated URL and filename
        # This assumes the URL itself doesn't contain unencoded spaces, which is standard.
        parts = url.split()
        if len(parts) > 1:
            url = parts[0]
            custom_file_name = " ".join(parts[1:])

    direct = direct_link_generator(url)
    if direct:
        url = direct

    # Ensure filename is safe/valid or fallback
    if not custom_file_name:
        custom_file_name = "downloaded_file"

    path = os.path.join(download_dir, custom_file_name)
    filepath = path
    if 'drive.google.com' in url:
        await n.handle_drive(edit_msg, url, custom_file_name, batch)
    else:
        await handle_url(url, filepath, edit_msg)
    return filepath


async def handle_tg_down(message, edit_msg, mode='no_reply'):
    from .helper import get_zip_folder, handle_extract
    from .display_progress import progress_for_pyrogram
    c_time = time.time()

    # Determine what to download
    target_msg = message
    if message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document):
        target_msg = message.reply_to_message
    elif message.video or message.document:
        target_msg = message
    elif mode == 'reply' and message.reply_to_message:
        target_msg = message.reply_to_message
    else:
        # If command was just /dl without reply and without attachment, and mode is not explicit reply
        if not (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)):
             return None
        target_msg = message.reply_to_message

    path = await target_msg.download(
        file_name=os.path.join(download_dir, ""),
        progress=progress_for_pyrogram,
        progress_args=("Downloading...", edit_msg, c_time))

    return path
