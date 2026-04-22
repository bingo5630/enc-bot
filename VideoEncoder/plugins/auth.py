from VideoEncoder import LOGGER


from pyrogram import Client, filters

from .. import everyone, sudo_users
from ..utils.database.access_db import db
from ..utils.helper import check_chat, output


@Client.on_message(filters.command(['addchat', 'add_chat']))
async def addchat(client, message):
    c = await check_chat(message, chat='Owner')
    if not c:
        return
    user_id = get_id(message)
    try:
        user_id = int(user_id)
    except:
        return await message.reply_text("Invalid User ID!")

    auth = await db.get_chat()
    auth_list = auth.split()

    if str(user_id) in auth_list or user_id in everyone:
        await reply_already_auth(message)
        return
    else:
        auth_list.append(str(user_id))
        await db.set_chat(" ".join(auth_list))
        await message.reply_text('Added to auth chats! ID: <code>{}</code>'.format(user_id))


@Client.on_message(filters.command(['addsudo', 'add_sudo']))
async def addsudo(client, message):
    c = await check_chat(message, chat='Owner')
    if not c:
        return
    user_id = get_id(message)
    try:
        user_id = int(user_id)
    except:
        return await message.reply_text("Invalid User ID!")

    auth = await db.get_sudo()
    sudo_list = auth.split()

    if str(user_id) in sudo_list or user_id in sudo_users:
        await reply_already_auth(message)
        return
    else:
        sudo_list.append(str(user_id))
        await db.set_sudo(" ".join(sudo_list))
        await message.reply_text('Added to sudo chats! ID: <code>{}</code>'.format(user_id))


@Client.on_message(filters.command(['rmchat', 'rem_chat']))
async def rmchat(client, message):
    c = await check_chat(message, chat='Owner')
    if not c:
        return
    user_id = get_id(message)
    try:
        user_id = int(user_id)
    except:
        return await message.reply_text("Invalid User ID!")

    check = await db.get_chat()
    auth_list = check.split()

    if str(user_id) in auth_list:
        auth_list.remove(str(user_id))
        await db.set_chat(" ".join(auth_list))
        await message.reply_text('Removed from auth chats! ID: <code>{}</code>'.format(user_id))
        return
    elif user_id in everyone:
        await message.reply_text('Config auth removal not supported (To Do)!')
        return
    else:
        await message.reply_text('Chat is not auth yet!')


@Client.on_message(filters.command(['rmsudo', 'rem_sudo']))
async def rmsudo(client, message):
    c = await check_chat(message, chat='Owner')
    if not c:
        return
    user_id = get_id(message)
    try:
        user_id = int(user_id)
    except:
        return await message.reply_text("Invalid User ID!")

    check = await db.get_sudo()
    sudo_list = check.split()

    if str(user_id) in sudo_list:
        sudo_list.remove(str(user_id))
        await db.set_sudo(" ".join(sudo_list))
        await message.reply_text('Removed from sudo chats! ID: <code>{}</code>'.format(user_id))
        return
    elif user_id in sudo_users:
        await message.reply_text('Config sudo removal not supported (To Do)!')
        return
    else:
        await message.reply_text('Chat is not auth yet!')


async def reply_already_auth(message):
    if message.reply_to_message:
        await message.reply(text='They are already in auth users...')
        return
    elif not message.reply_to_message and len(message.command) != 1:
        await message.reply(text='They are already in auth users/group...')
        return
    else:
        await message.reply(text='This chat is already in auth users/groups...')
        return


def get_id(message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif not message.reply_to_message and len(message.command) != 1:
        user_id = message.text.split(None, 1)[1]
    else:
        user_id = message.chat.id
    return user_id
