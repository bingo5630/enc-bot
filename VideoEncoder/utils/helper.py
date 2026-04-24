
import asyncio
import os
import shutil

from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pySmartDL import SmartDL

from .. import all, everyone, owner, sudo_users, download_dir, encode_dir, LOGGER
from .database.access_db import db
from .display_progress import progress_for_url
from .encoding import encode, extract_subs, extract_subtitle, hard_sub, soft_code
from .uploads import upload_worker
from .uploads.telegram import upload_doc

output = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Back to Home", callback_data="backToStart"),
        InlineKeyboardButton("ᴄʟosᴇ", callback_data="closeMeh")
    ]
])

start_but = InlineKeyboardMarkup([
    [InlineKeyboardButton("⚙️ sᴇᴛᴛɪɴɢs", callback_data="OpenSettings")],
    [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_callback"), InlineKeyboardButton("👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/Dorashin_hlo")],
    [InlineKeyboardButton("• ᴍᴜɢɪᴡᴀʀᴀs ɴᴇᴛᴡᴏʀᴋ •", url="https://t.me/Mugiwaras_Network")]
])


async def edit_msg(msg, **kwargs):
    try:
        if 'media' in kwargs:
            return await msg.edit_media(**kwargs)
        if 'caption' in kwargs:
            return await msg.edit_caption(**kwargs)
        if 'text' in kwargs:
            return await msg.edit_text(**kwargs)
        return await msg.edit(**kwargs)
    except MessageNotModified:
        pass
    except Exception as e:
        LOGGER.error(f"Error in edit_msg: {e}")


async def check_chat(message, chat):
    ''' Authorize User! '''
    chat_id = message.chat.id
    user_id = message.from_user.id
    get_sudo = await db.get_sudo()
    get_auth = await db.get_chat()
    if user_id in owner or user_id == 885190545:
        title = 'God'
    elif user_id in sudo_users or chat_id in sudo_users:
        title = 'Sudo'
    elif chat_id in everyone or user_id in everyone:
        title = 'Auth'
    elif str(user_id) in get_sudo or str(chat_id) in get_sudo:
        title = 'Sudo'
    elif str(chat_id) in get_auth or str(user_id) in get_auth:
        title = 'Auth'
    else:
        title = None
    if title == 'God':
        return True
    if not chat == 'Owner':
        if title == 'Sudo':
            return True
        if chat == 'Both':
            if title == 'Auth':
                return True
    return None


async def handle_url(url, filepath, msg):
    downloader = SmartDL(url, filepath, progress_bar=False, threads=10)
    downloader.start(blocking=False)
    while not downloader.isFinished():
        await progress_for_url(downloader, msg)


async def handle_sub_extract(filepath, message, msg):
    await msg.edit("Processing... ⏳")
    result = await extract_subtitle(filepath)
    if os.path.isfile(result):
        try:
            await upload_doc(message, msg, 0, os.path.basename(result), result)
            await msg.edit("Subtitle extracted and uploaded successfully!")
        except Exception as e:
            await msg.edit(f"Error while uploading: {e}")
        finally:
            if os.path.isfile(result):
                os.remove(result)
    else:
        await msg.edit(f"Failed to extract subtitles: {result}")

    # Cleanup video file
    if os.path.isfile(filepath):
        os.remove(filepath)


async def handle_encode(filepath, message, msg, audio_map=None, quality=None, custom_name=None):
    sub_path = os.path.join(encode_dir, str(msg.id) + '.ass')
    new_file = None
    try:
        if custom_name:
            # Ensure it has an extension, if not use original's
            if not os.path.splitext(custom_name)[1]:
                custom_name += os.path.splitext(filepath)[1]
            # Replace filepath to use custom name for output base
            # Note: handle_encode/encode usually derive output name from input filepath
            # We can create a temp copy or just pass custom_name to encode()
            pass

        if await db.get_hardsub(message.from_user.id):
            subs = await extract_subs(filepath, msg, message.from_user.id)
            if not subs:
                await msg.edit("Something went wrong while extracting the subtitles!")
                return
            # Move subs to expected location if it was from existing subs
            if subs != sub_path and os.path.exists(subs):
                os.rename(subs, sub_path)

        new_file, error_log = await encode(filepath, message, msg, audio_map=audio_map, quality=quality, custom_name=custom_name)
        if new_file:
            # 1MB = 1048576 bytes
            if os.path.getsize(new_file) < 1048576:
                LOGGER.error(f"Encoded file is too small ({os.path.getsize(new_file)} bytes). FFmpeg likely failed.")
                error_file = f"ffmpeg_error_{msg.id}.txt"
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(error_log or "Unknown FFmpeg error")
                await message.reply_document(error_file, caption="FFmpeg error log (Output file < 1MB)")
                if os.path.exists(error_file):
                    os.remove(error_file)
                if os.path.exists(new_file):
                    os.remove(new_file)
                new_file = None
                link = None
            else:
                await msg.edit("<code>Video Encoded, getting metadata...</code>")
                try:
                    link = await upload_worker(new_file, message, msg)
                    # No extra success notification as per requirement
                except Exception as e:
                    await msg.edit(f"Error while uploading: {e}")
                    link = None
        else:
            error_file = f"ffmpeg_error_{msg.id}.txt"
            with open(error_file, 'w', encoding='utf-8-sig') as f:
                f.write(error_log or "Something went wrong during encoding.")
            await message.reply_document(error_file, caption="Something went wrong while encoding your file.")
            if os.path.exists(error_file):
                os.remove(error_file)
            link = None
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


async def handle_interactive_encode(video_path, sub_path, message, msg, mode, quality=None):
    # Ensure sub_path is named correctly for encode if needed
    sub_dest = os.path.join(encode_dir, str(msg.id) + '.ass')
    if sub_path != sub_dest:
        if os.path.exists(sub_path):
            os.rename(sub_path, sub_dest)
        sub_path = sub_dest

    new_file = None
    error_log = None
    try:
        if mode == 'encode':
            new_file, error_log = await encode(video_path, message, msg, quality=quality)
        elif mode == 'hard_sub':
            new_file, error_log = await hard_sub(video_path, sub_path, message, msg, quality=quality)
        elif mode == 'soft_code':
            new_file, error_log = await soft_code(video_path, sub_path, message, msg, quality=quality)
        else:
            new_file = None

        if new_file:
            # 1MB = 1048576 bytes
            if os.path.getsize(new_file) < 1048576:
                LOGGER.error(f"Processed file is too small ({os.path.getsize(new_file)} bytes). FFmpeg likely failed.")
                error_file = f"ffmpeg_error_{msg.id}.txt"
                with open(error_file, 'w', encoding='utf-8-sig') as f:
                    f.write(error_log or "Unknown FFmpeg error")
                await message.reply_document(error_file, caption="FFmpeg error log (Output file < 1MB)")
                if os.path.exists(error_file):
                    os.remove(error_file)
                if os.path.exists(new_file):
                    os.remove(new_file)
                new_file = None
            else:
                await msg.edit("<code>Process Completed, getting metadata...</code>")
                try:
                    link = await upload_worker(new_file, message, msg)
                    # No extra success notification as per requirement
                except Exception as e:
                    await msg.edit(f"Error while uploading: {e}")
        else:
            error_file = f"ffmpeg_error_{msg.id}.txt"
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


async def handle_extract(archieve):
    # get current directory
    path = os.getcwd()
    archieve = os.path.join(path, archieve)
    cmd = [f'./extract', archieve]
    rio = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await rio.communicate()
    os.remove(archieve)
    return path


async def get_zip_folder(orig_path: str):
    if orig_path.endswith(".tar.bz2"):
        return orig_path.rsplit(".tar.bz2", 1)[0]
    elif orig_path.endswith(".tar.gz"):
        return orig_path.rsplit(".tar.gz", 1)[0]
    elif orig_path.endswith(".bz2"):
        return orig_path.rsplit(".bz2", 1)[0]
    elif orig_path.endswith(".gz"):
        return orig_path.rsplit(".gz", 1)[0]
    elif orig_path.endswith(".tar.xz"):
        return orig_path.rsplit(".tar.xz", 1)[0]
    elif orig_path.endswith(".tar"):
        return orig_path.rsplit(".tar", 1)[0]
    elif orig_path.endswith(".tbz2"):
        return orig_path.rsplit("tbz2", 1)[0]
    elif orig_path.endswith(".tgz"):
        return orig_path.rsplit(".tgz", 1)[0]
    elif orig_path.endswith(".zip"):
        return orig_path.rsplit(".zip", 1)[0]
    elif orig_path.endswith(".7z"):
        return orig_path.rsplit(".7z", 1)[0]
    elif orig_path.endswith(".Z"):
        return orig_path.rsplit(".Z", 1)[0]
    elif orig_path.endswith(".rar"):
        return orig_path.rsplit(".rar", 1)[0]
    elif orig_path.endswith(".iso"):
        return orig_path.rsplit(".iso", 1)[0]
    elif orig_path.endswith(".wim"):
        return orig_path.rsplit(".wim", 1)[0]
    elif orig_path.endswith(".cab"):
        return orig_path.rsplit(".cab", 1)[0]
    elif orig_path.endswith(".apm"):
        return orig_path.rsplit(".apm", 1)[0]
    elif orig_path.endswith(".arj"):
        return orig_path.rsplit(".arj", 1)[0]
    elif orig_path.endswith(".chm"):
        return orig_path.rsplit(".chm", 1)[0]
    elif orig_path.endswith(".cpio"):
        return orig_path.rsplit(".cpio", 1)[0]
    elif orig_path.endswith(".cramfs"):
        return orig_path.rsplit(".cramfs", 1)[0]
    elif orig_path.endswith(".deb"):
        return orig_path.rsplit(".deb", 1)[0]
    elif orig_path.endswith(".dmg"):
        return orig_path.rsplit(".dmg", 1)[0]
    elif orig_path.endswith(".fat"):
        return orig_path.rsplit(".fat", 1)[0]
    elif orig_path.endswith(".hfs"):
        return orig_path.rsplit(".hfs", 1)[0]
    elif orig_path.endswith(".lzh"):
        return orig_path.rsplit(".lzh", 1)[0]
    elif orig_path.endswith(".lzma"):
        return orig_path.rsplit(".lzma", 1)[0]
    elif orig_path.endswith(".lzma2"):
        return orig_path.rsplit(".lzma2", 1)[0]
    elif orig_path.endswith(".mbr"):
        return orig_path.rsplit(".mbr", 1)[0]
    elif orig_path.endswith(".msi"):
        return orig_path.rsplit(".msi", 1)[0]
    elif orig_path.endswith(".mslz"):
        return orig_path.rsplit(".mslz", 1)[0]
    elif orig_path.endswith(".nsis"):
        return orig_path.rsplit(".nsis", 1)[0]
    elif orig_path.endswith(".ntfs"):
        return orig_path.rsplit(".ntfs", 1)[0]
    elif orig_path.endswith(".rpm"):
        return orig_path.rsplit(".rpm", 1)[0]
    elif orig_path.endswith(".squashfs"):
        return orig_path.rsplit(".squashfs", 1)[0]
    elif orig_path.endswith(".udf"):
        return orig_path.rsplit(".udf", 1)[0]
    elif orig_path.endswith(".vhd"):
        return orig_path.rsplit(".vhd", 1)[0]
    elif orig_path.endswith(".xar"):
        return orig_path.rsplit(".xar", 1)[0]
    else:
        raise IndexError("File format not supported for extraction!")


def delete_downloads():
    dir = encode_dir
    dir2 = download_dir
    for files in os.listdir(dir):
        path = os.path.join(dir, files)
        try:
            shutil.rmtree(path)
        except OSError:
            try:
                os.remove(path)
            except PermissionError:
                pass
    for files in os.listdir(dir2):
        path = os.path.join(dir2, files)
        try:
            shutil.rmtree(path)
        except OSError:
            try:
                os.remove(path)
            except PermissionError:
                pass
