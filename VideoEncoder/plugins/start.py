from ..utils.common import edit_msg
from VideoEncoder import LOGGER


import os
import shutil
import time
import shlex
from os import execl as osexecl
from subprocess import run as srun
from sys import executable
from time import time

from psutil import (boot_time, cpu_count, cpu_percent, disk_usage,
                    net_io_counters, swap_memory, virtual_memory)
from pyrogram import Client, filters
from pyrogram.types import Message

from .. import botStartTime, download_dir, encode_dir
from ..utils.database.access_db import db
from ..utils.database.add_user import AddUserToDatabase
from ..utils.display_progress import TimeFormatter, humanbytes
from ..utils.helper import check_chat, delete_downloads
from ..utils.common import start_but

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

START_PIC = "https://graph.org/file/a43e51fdee6998d7074e0-c9255fe3e80803a9a9.jpg"
FORCE_PIC = "https://graph.org/file/a0947a8895736ff574666-422dfa95e7395c7142.jpg"
START_MSG = "<b>ʜᴇʏ!!, {mention} ~\n\nYou woke me up!\n\n<blockquote expandable>I was having such a great dream about world domination... err, I mean, serving you efficiently.\n\nReady to start the show? Send me a video file and let's roll!</blockquote></b>"


def uptime():
    """ returns uptime """
    return TimeFormatter(time.time() - botStartTime)


@Client.on_message(filters.command('start'))
async def start_message(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return await message.reply_photo(photo=FORCE_PIC, caption="<b>You are not authorized to use this bot!</b>", has_spoiler=True)
    await AddUserToDatabase(app, message)
    user = message.from_user
    name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    mention = f"<a href='{link}'>{name}</a>"
    await message.reply_photo(photo=START_PIC, caption=START_MSG.format(mention=mention), reply_markup=start_but, has_spoiler=True)


@Client.on_message(filters.command('help'))
async def help_message(app, message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(app, message)
    msg = """<blockquote><b>How to Translate - Step by Step Guide:</b></blockquote>
<blockquote expandable>➼ <b>Step 1: Get Groq Key</b>
[Click here to Create Groq API Key](https://console.groq.com/keys) and add it using /set_groq_api.

➼ <b>Step 2: Upload Your File</b>
Send your .ass or subtitle file directly to the bot.

➼ <b>Step 3: Select the Engine</b>
Choose the high-stability Groq engine for lightning-fast results.

➼ <b>Step 4: Wait for Processing</b>
The bot will split your file into micro-chunks to ensure high-quality Hinglish translation. Once done, you'll receive the translated file.</blockquote>

<b>Note:</b> The bot now uses an optimized Groq-Only architecture for 100% stability!"""
    await message.reply_photo(photo=START_PIC, caption=msg, reply_markup=start_but, has_spoiler=True)


@Client.on_message(filters.command('stats'))
async def show_status_count(_, event: Message):
    c = await check_chat(event, chat='Both')
    if not c:
        return
    await AddUserToDatabase(_, event)
    text = await show_status(_)
    await event.reply_text(text)


async def show_status(_):
    currentTime = TimeFormatter(time() - botStartTime)
    osUptime = TimeFormatter(time() - boot_time())
    total, used, free, disk = disk_usage('/')
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    sent = humanbytes(net_io_counters().bytes_sent)
    recv = humanbytes(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    memory = virtual_memory()
    mem_t = humanbytes(memory.total)
    mem_a = humanbytes(memory.available)
    mem_u = humanbytes(memory.used)
    total_users = await db.total_users_count()
    text = f"""<b>Uptime of</b>:
- <b>Bot:</b> {currentTime}
- <b>OS:</b> {osUptime}

<b>Disk</b>:
<b>- Total:</b> {total}
<b>- Used:</b> {used}
<b>- Free:</b> {free}

<b>UL:</b> {sent} | <b>DL:</b> {recv}
<b>CPU:</b> {cpuUsage}%

<b>Cores:</b>
<b>- Physical:</b> {p_core}
<b>- Total:</b> {t_core}
<b>- Used:</b> {swap_p}%

<b>RAM:</b> 
- <b>Total:</b> {mem_t}
- <b>Free:</b> {mem_a}
- <b>Used:</b> {mem_u}

Users: {total_users}"""
    return text


async def showw_status(_):
    currentTime = TimeFormatter(time() - botStartTime)
    total, used, free, disk = disk_usage('/')
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    cpuUsage = cpu_percent(interval=0.5)
    total_users = await db.total_users_count()

    text = f"""Uptime of Bot: {currentTime}

Disk:
- Total: {total}
- Used: {used}
- Free: {free}
CPU: {cpuUsage}%

Users: {total_users}"""
    return text


@Client.on_message(filters.command('clean'))
async def delete_files(_, message):
    c = await check_chat(message, chat='Sudo')
    if not c:
        return
    delete_downloads()
    await message.reply_text('Deleted all junk files!')


@Client.on_message(filters.command('restart'))
async def font_message(app, message):
    c = await check_chat(message, chat='Sudo')
    if not c:
        return
    await AddUserToDatabase(app, message)
    reply = await message.reply_text('Restarting...')
    textx = f"Done Restart...✅"
    await edit_msg(reply, text=textx)
    try:
        exit()
    finally:
        osexecl(executable, executable, "-m", "VideoEncoder")


@Client.on_message(filters.command('update'))
async def update_message(app, message):
    c = await check_chat(message, chat='Sudo')
    if not c:
        return
    await AddUserToDatabase(app, message)
    reply = await message.reply_text('📶 Fetching Update...')
    textx = f"✅ Bot Updated"
    await edit_msg(reply, text=textx)
    try:
        await app.stop()
    finally:
        srun("bash run.sh", shell=True)
