from VideoEncoder import LOGGER


import asyncio

from pyrogram import Client, filters

from .. import data, video_mimetype
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat
from ..utils.tasks import handle_tasks


@Client.on_message(filters.command('dl'))
async def encode_video(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)

    # Check if replying to a file or file is attached
    if not (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)) and \
       not (message.video or message.document):
           await message.reply("Please reply to a video or document, or attach one with the command.")
           return

    data.append(message)
    if len(data) == 1:
        await handle_tasks(message, 'tg')
    else:
        await message.reply("📔 Waiting for queue...")
    await asyncio.sleep(1)


@Client.on_message(filters.command(['480p', '720p', '1080p']))
async def quality_encode(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)

    # Check if replying to a file or file is attached
    if not (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)) and \
       not (message.video or message.document):
           await message.reply("Please reply to a video or document, or attach one with the command.")
           return

    data.append(message)
    text = (message.text or message.caption)
    cmd = text.split()[0][1:] # e.g. '480p'

    custom_name = None
    if "-n" in text:
        parts = text.split("-n", 1)
        if len(parts) > 1:
            custom_name = os.path.basename(parts[1].strip())

    if len(data) == 1:
        edit_msg = await message.reply_text("Processing...")
        await handle_tasks(message, cmd, msg=edit_msg, custom_name=custom_name)
    else:
        await message.reply(f"📔 Waiting for queue for {cmd}...")
    await asyncio.sleep(1)


@Client.on_message(filters.command('sub_extract'))
async def sub_extract_command(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)

    # Determine text/caption content
    content = message.text or message.caption

    # Check for file reply/attachment or URL
    has_file = (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)) or \
               (message.video or message.document)
    has_url = content and len(content.split()) > 1

    if not has_file and not has_url:
        await message.reply("Please reply to a video or document, attach one, or provide a URL with the command.")
        return

    data.append(message)
    if len(data) == 1:
        mode = 'sub_tg' if has_file else 'sub_url'
        await handle_tasks(message, mode)
    else:
        await message.reply("📔 Waiting for queue...")
    await asyncio.sleep(1)

@Client.on_message(filters.command('af'))
async def audio_features(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)

    # Check if replying to a file or file is attached
    if not (message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document)) and \
       not (message.video or message.document):
           await message.reply("Please reply to a video or document, or attach one with the command.")
           return

    data.append(message)
    if len(data) == 1:
        await handle_tasks(message, 'af')
    else:
        await message.reply("📔 Waiting for queue...")
    await asyncio.sleep(1)

@Client.on_message(filters.command('ddl'))
async def url_encode(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)
    data.append(message)
    if len(message.text.split()) == 1:
        await message.reply_text("Usage: /ddl [url] | [filename]")
        data.remove(data[0])
        return
    if len(data) == 1:
        await handle_tasks(message, 'url')
    else:
        await message.reply("📔 Waiting for queue...")
    await asyncio.sleep(1)


@Client.on_message(filters.command('batch'))
async def batch_encode(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)
    data.append(message)
    if len(message.text.split()) == 1:
        await message.reply_text("Usage: /batch [url]")
        data.remove(data[0])
        return
    if len(data) == 1:
        await handle_tasks(message, 'batch')
    else:
        await message.reply("📔 Waiting for queue...")
    await asyncio.sleep(1)
