import os
import asyncio
import re
import httpx
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .. import LOGGER, download_dir
from ..utils.uploads.telegram import upload_doc
from ..utils.database.access_db import db

# 1. Setup the low-level client for Gemini v1beta
from google.ai import generativelanguage_v1beta as glossar
from google.api_core import client_options
from google.auth.credentials import AnonymousCredentials

client_opts = client_options.ClientOptions(api_endpoint="generativelanguage.googleapis.com")
gemini_client = glossar.GenerativeServiceClient(
    client_options=client_opts,
    credentials=AnonymousCredentials()
)

SYSTEM_PROMPT = "You are a professional Anime/Manhwa translator. Read the English text from the file and translate it into Normal Hinglish (Hindi + English). Rule: Don't change any tags, timing, or symbols. Just change the English words into natural, easy-to-read Hinglish (like we talk in daily life). Format: Keep the same line-by-line structure as the original file. Do not add any explanations, only return the translated content."

TRANSLATE_PIC = "https://graph.org/file/600586a9a49029c2e98f1-90c27ea7986142ea7a.jpg"
TRANSLATE_TEXT = "✨ ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ᴇɴɢɪɴᴇ ✨\nᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ᴀ ᴍᴏᴅᴇʟ ᴛᴏ sᴛᴀʀᴛ ʜɪɴɢʟɪsʜ ᴛʀᴀɴsʟᴀᴛɪᴏɴ."

# Temporary storage for file metadata linked to message ID
translation_data = {}

SETUP_GUIDE_TEXT = (
    "✨ ʜᴏᴡ ᴛᴏ sᴇᴛ ᴜᴘ ʏᴏᴜʀ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ᴇɴɢɪɴᴇ ✨\n"
    "𝟷️⃣ [ᴄʟɪᴄᴋ ʜᴇʀᴇ ғᴏʀ ɢᴇᴍɪɴɪ ᴋᴇʏ](https://aistudio.google.com/app/apikey)\n"
    "𝟸️⃣ [ᴄʟɪᴄᴋ ʜᴇʀᴇ ғᴏʀ ɢʀᴏǫ ᴋᴇʏ](https://console.groq.com/keys)\n\n"
    "👉 sᴇɴᴅ ʏᴏᴜʀ ᴋᴇʏs ᴜsɪɴɢ /set_gemini ᴏʀ /set_groq."
)

SETUP_GUIDE_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_translator")]
])

TRANSLATE_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("ɢᴇᴍɪɴɪ ᴘʀᴏ 💎", callback_data="trans_gemini_pro"),
        InlineKeyboardButton("ɢᴇᴍɪɴɪ ғʟᴀsʜ ⚡", callback_data="trans_gemini_flash")
    ],
    [
        InlineKeyboardButton("ʟʟᴀᴍᴀ-𝟹.𝟹 (ɢʀᴏǫ) 🚀", callback_data="trans_llama3_groq"),
        InlineKeyboardButton("ᴍɪxᴛʀᴀʟ-𝟾x𝟽ʙ (ɢʀᴏǫ) 🌀", callback_data="trans_mixtral_groq")
    ],
    [
        InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ᴛʀᴀɴsʟᴀᴛᴇ? ❓", callback_data="how_to_translate")
    ]
])

def parse_srt(content):
    blocks = re.split(r'\n\s*\n', content.strip())
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            parsed.append({
                'index': lines[0],
                'timestamp': lines[1],
                'text': '\n'.join(lines[2:])
            })
        else:
            parsed.append({'raw': block})
    return parsed

def parse_ass(content):
    lines = content.splitlines()
    header = []
    events = []
    in_events = False
    for line in lines:
        if line.strip().lower().startswith('[events]'):
            in_events = True
            header.append(line)
            continue
        if not in_events:
            header.append(line)
        else:
            if line.strip().startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) == 10:
                    events.append({'prefix': parts[0:9], 'text': parts[9]})
                else:
                    events.append({'raw': line})
            else:
                events.append({'raw': line})
    return header, events

async def translate_gemini(chunk_text, api_key, model_name):
    if not chunk_text.strip():
        return chunk_text

    # Ensure model_name doesn't have "models/" prefix for latest SDK compliance
    if model_name.startswith("models/"):
        model_name = model_name.replace("models/", "")

    prompt_text = f"{SYSTEM_PROMPT}\n\nCONTENT TO TRANSLATE:\n{chunk_text}"
    request = glossar.GenerateContentRequest(
        model=model_name,
        contents=[glossar.Content(parts=[glossar.Part(text=prompt_text)])]
    )

    for attempt in range(2):
        try:
            response = await asyncio.to_thread(
                gemini_client.generate_content,
                request=request,
                metadata=[('x-goog-api-key', api_key)]
            )
            if response.candidates and response.candidates[0].content.parts:
                translated_text = response.candidates[0].content.parts[0].text.strip()
                translated_text = re.sub(r'```[a-z]*\n|```', '', translated_text)
                return translated_text
            return "❌ Gemini Error: No response candidates found."
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            return f"❌ Gemini Error: {str(e)}"

async def translate_groq(chunk_text, api_key, model_name):
    if not chunk_text.strip():
        return chunk_text

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk_text}
        ],
        "temperature": 0.2
    }

    async with httpx.AsyncClient() as client:
        for attempt in range(2):
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                if response.status_code == 200:
                    data = response.json()
                    translated_text = data['choices'][0]['message']['content'].strip()
                    translated_text = re.sub(r'```[a-z]*\n|```', '', translated_text)
                    return translated_text
                else:
                    return f"❌ Groq Error: {response.status_code} - {response.text}"
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                return f"❌ Groq Error: {str(e)}"

@Client.on_message(filters.command("translate") & filters.private)
async def translate_cmd_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a .ass or .srt file with /translate")
        return

    replied = message.reply_to_message
    if not (replied.document and replied.document.file_name and replied.document.file_name.lower().endswith((".ass", ".srt"))):
        await message.reply_text("❌ Please reply to a valid .ass or .srt file.")
        return

    # Check for API Keys
    gemini_key = await db.get_gemini_api_key(user_id)
    groq_key = await db.get_groq_api_key(user_id)

    if not gemini_key and not groq_key:
        await message.reply_photo(
            photo=TRANSLATE_PIC,
            caption=SETUP_GUIDE_TEXT,
            reply_markup=SETUP_GUIDE_BUTTONS,
            has_spoiler=True
        )
        return

    sent_msg = await message.reply_photo(
        photo=TRANSLATE_PIC,
        caption=TRANSLATE_TEXT,
        reply_markup=TRANSLATE_BUTTONS,
        has_spoiler=True
    )

    # Store file metadata indexed by a unique chat_message key to prevent collisions
    unique_key = f"{replied.chat.id}_{sent_msg.id}"
    translation_data[unique_key] = {
        'file_id': replied.document.file_id,
        'file_name': replied.document.file_name,
        'chat_id': replied.chat.id,
        'message_id': replied.id,
        'user_id': user_id
    }

@Client.on_message(filters.command("set_gemini") & filters.private)
async def set_gemini_handler(bot: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /set_gemini YOUR_KEY_HERE")
        return
    api_key = message.command[1]
    await db.set_gemini_api_key(message.from_user.id, api_key)
    await message.reply_text("✅ Gemini API Key saved successfully!")

@Client.on_message(filters.command("set_groq") & filters.private)
async def set_groq_handler(bot: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /set_groq YOUR_KEY_HERE")
        return
    api_key = message.command[1]
    await db.set_groq_api_key(message.from_user.id, api_key)
    await message.reply_text("✅ Groq API Key saved successfully!")

@Client.on_message(filters.command("clear_api") & filters.private)
async def clear_api_handler(bot: Client, message: Message):
    await db.set_gemini_api_key(message.from_user.id, None)
    await db.set_groq_api_key(message.from_user.id, None)
    await message.reply_text("✅ All API Keys cleared successfully!")

async def process_translation(bot, cb, model_type, model_name):
    # This will be called from callbacks_.py
    user_id = cb.from_user.id

    if model_type == "gemini":
        api_key = await db.get_gemini_api_key(user_id)
        translate_func = translate_gemini
    else:
        api_key = await db.get_groq_api_key(user_id)
        translate_func = translate_groq

    if not api_key:
        await cb.answer(f"❌ {model_type.capitalize()} API Key Missing!", show_alert=True)
        return

    # 1. Try to get file info from temporary storage (Fixes "File Not Found")
    unique_key = f"{cb.message.chat.id}_{cb.message.id}"
    file_data = translation_data.get(unique_key)
    replied = None

    if file_data:
        file_id = file_data['file_id']
        file_name = file_data['file_name']
        try:
            replied = await bot.get_messages(file_data['chat_id'], file_data['message_id'])
        except Exception as e:
            LOGGER.error(f"Error fetching message from translation_data: {e}")
            replied = None
    else:
        # 2. Fallback to reply-chain logic
        cmd_msg = cb.message.reply_to_message
        if cmd_msg and cmd_msg.reply_to_message:
            replied = cmd_msg.reply_to_message
            if replied.document and replied.document.file_name and replied.document.file_name.lower().endswith((".ass", ".srt")):
                file_id = replied.document.file_id
                file_name = replied.document.file_name
            else:
                await cb.answer("❌ Please reply to a valid .ass or .srt file.", show_alert=True)
                return
        else:
            await cb.answer("❌ Original file not found. Please try /translate again.", show_alert=True)
            return

    await cb.message.delete()
    status_msg = await bot.send_message(user_id, "⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜ᴇ𝐬𝐬ɪɴ𝐠] : 𝐑𝐞𝐚𝐝𝐢𝐧𝐠 𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐬𝐭ᴀ𝐫ᴛɪ𝐧𝐠 ᴛ𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐢𝐨𝐧...")

    file_path = await bot.download_media(
        message=file_id,
        file_name=os.path.join(download_dir, file_name)
    )

    # Clean up storage
    if unique_key in translation_data:
        del translation_data[unique_key]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        is_srt = file_path.lower().endswith(".srt")
        translated_content = ""

        if is_srt:
            blocks = re.split(r'\n\s*\n', content.strip())
            total_chunks = (len(blocks) + 19) // 20
            translated_blocks = []
            for i in range(0, len(blocks), 20):
                await status_msg.edit(f"⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠] : Translating chunk {(i//20)+1}/{total_chunks}...")
                chunk = "\n\n".join(blocks[i : i + 20])
                res = await translate_func(chunk, api_key, model_name)
                if res.startswith("❌"):
                    await status_msg.edit(res)
                    return
                translated_blocks.append(res)
                if model_type == "groq" and (i + 20) < len(blocks):
                    await asyncio.sleep(2)
            translated_content = "\n\n".join(translated_blocks)
        else:
            header, events = parse_ass(content)
            total_chunks = (len(events) + 19) // 20
            final_events = []
            for i in range(0, len(events), 20):
                await status_msg.edit(f"⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠] : Translating chunk {(i//20)+1}/{total_chunks}...")
                chunk_lines = []
                for item in events[i : i + 20]:
                    if 'text' in item:
                        chunk_lines.append(",".join(item['prefix']) + "," + item['text'])
                    else:
                        chunk_lines.append(item['raw'])
                res = await translate_func("\n".join(chunk_lines), api_key, model_name)
                if res.startswith("❌"):
                    await status_msg.edit(res)
                    return
                final_events.append(res)
                if model_type == "groq" and (i + 20) < len(events):
                    await asyncio.sleep(2)
            translated_content = "\n".join(header) + "\n" + "\n".join(final_events)

        output_filename = os.path.splitext(file_name)[0] + "_Hinglish" + os.path.splitext(file_name)[1]
        output_path = os.path.join(download_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        caption = f"✅ Translated by AI (Hinglish)\nFile: <code>{output_filename}</code>"
        # If replied is still None (fallback failed), use cb.message as a last resort to send the file
        target_msg = replied if replied else cb.message
        await upload_doc(target_msg, status_msg, 0, output_filename, output_path, caption=caption)
    except Exception as e:
        LOGGER.error(f"Translation Error: {e}")
        await status_msg.edit(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if 'output_path' in locals() and os.path.exists(output_path): os.remove(output_path)
