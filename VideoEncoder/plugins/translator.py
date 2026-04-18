
import os
import asyncio
import re
import google.generativeai as genai
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.enums import ParseMode
from .. import ASSETS_DIR, LOGGER, download_dir
from ..utils.database.add_user import AddUserToDatabase
from ..utils.helper import check_chat
from ..utils.uploads.telegram import upload_doc

# Setup Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
else:
    model = None

# user_id: True if waiting for subtitle file, "CANCELLED" if cancelled during process, "PROCESSING" when active
translator_sessions = {}

def get_translator_menu():
    img_url = "https://graph.org/file/3b3e573290ea2f1ab272e-d0521dd8d5a1359e41.jpg"
    text = "🌐 𝖠𝖨 𝖲𝖴𝖳𝖨𝖳𝖫𝖤 𝖳𝖱𝖠𝖭𝖲𝖫𝖠𝖳𝖮𝖱\n<blockquote expandable>➤ ᴛʀᴀɴsʟᴀᴛᴇ ʏᴏᴜʀ ᴀɴɪᴍᴇ/ᴍᴀɴʜᴡᴀ sᴜʙᴛɪᴛʟᴇs ᴜsɪɴɢ ᴀᴅᴠᴀɴᴄᴇᴅ ɢᴇᴍɪɴɪ ᴀɪ. ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ.</blockquote>"

    buttons = [
        [
            InlineKeyboardButton("ʜɪɴɢʟɪsʜ", callback_data="hinglish_trigger"),
            InlineKeyboardButton("ʜᴇʟᴘ", callback_data="translator_help")
        ],
        [
            InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="closeMeh")
        ]
    ]
    return img_url, text, InlineKeyboardMarkup(buttons)

def parse_srt(content):
    blocks = re.split(r'\n\s*\n', content.strip())
    parsed_blocks = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text = "\n".join(lines[2:])
            parsed_blocks.append({'index': index, 'timestamp': timestamp, 'text': text})
        else:
            parsed_blocks.append({'raw': block})
    return parsed_blocks

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
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) == 10:
                    events.append({'prefix': parts[0:9], 'text': parts[9]})
                else:
                    events.append({'raw': line})
            else:
                events.append({'raw': line})
    return header, events

async def translate_batch(batch_texts):
    if not batch_texts:
        return []

    numbered_text = "\n".join([f"{i+1}: {text}" for i, text in enumerate(batch_texts)])
    prompt = (
        "You are a professional Anime/Manhwa translator. Translate the following numbered segments into natural Hinglish. "
        "Professional tone. Keep the original vibe and all formatting like {\\pos(x,y)}. "
        "Preserve the numbering format 'n: translated_text'. Output ONLY the translated segments.\n\n"
        f"{numbered_text}"
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        lines = response.text.strip().splitlines()
        translated_segments = []
        for line in lines:
            match = re.match(r'^\d+:\s*(.*)', line.strip())
            if match:
                translated_segments.append(match.group(1))

        if len(translated_segments) != len(batch_texts):
             LOGGER.warning(f"Batch translation mismatch: {len(translated_segments)} vs {len(batch_texts)}")
             if len(translated_segments) > len(batch_texts):
                 return translated_segments[:len(batch_texts)]
             else:
                 return translated_segments + batch_texts[len(translated_segments):]

        return translated_segments
    except Exception as e:
        LOGGER.error(f"Gemini API Error: {e}")
        return None

def get_progress_bar(percentage):
    completed = int(percentage / 10)
    remaining = 10 - completed
    return "▰" * completed + "▱" * remaining

@Client.on_message(filters.command("translator") & filters.private)
async def translator_cmd(bot: Client, message: Message):
    c = await check_chat(message, chat='Both')
    if not c:
        return
    await AddUserToDatabase(bot, message)

    img_url, text, markup = get_translator_menu()

    await message.reply_photo(
        photo=img_url,
        caption=text,
        has_spoiler=True,
        reply_markup=markup
    )

@Client.on_message(filters.document & filters.private, group=-1)
async def translator_file_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in translator_sessions or translator_sessions[user_id] == "CANCELLED":
        return

    if not message.document or not (message.document.file_name.lower().endswith(".ass") or message.document.file_name.lower().endswith(".srt")):
        return

    message.stop_propagation()
    translator_sessions[user_id] = "PROCESSING"

    msg = await message.reply_text("<code>Downloading file... ⏳</code>")

    file_path = await message.download(file_name=os.path.join(download_dir, message.document.file_name))

    try:
        if not model:
            await msg.edit("❌ <b>Gemini API Key not found!</b> Please set <code>GEMINI_API_KEY</code> in config.")
            return

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        is_srt = file_path.lower().endswith(".srt")

        translatable_items = []
        if is_srt:
            parsed_data = parse_srt(content)
            for item in parsed_data:
                if 'text' in item:
                    translatable_items.append(item)
        else:
            header, parsed_data = parse_ass(content)
            for item in parsed_data:
                if 'text' in item:
                    translatable_items.append(item)

        total_lines = len(translatable_items)
        if total_lines == 0:
            await msg.edit("❌ <b>No translatable lines found in the file!</b>")
            return

        batch_size = 10
        for i in range(0, total_lines, batch_size):
            if translator_sessions.get(user_id) == "CANCELLED":
                await msg.edit("🚦 <b>Translation Cancelled by User!</b>")
                return

            batch = translatable_items[i : i + batch_size]
            batch_texts = [item['text'] for item in batch]

            percentage = min(100, int((i / total_lines) * 100))
            bar = get_progress_bar(percentage)

            progress_text = (
                "‣ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐀𝐈 𝐓𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐢𝐧𝐠...\n"
                f"[{bar}] {percentage}%\n"
                f"‣ 𝐋𝐢𝐧𝐞𝐬 : {i} / {total_lines}\n"
                "‣ 𝐄𝐧𝐠𝐢𝐧𝐞 : 𝐆𝐞𝐦𝐢𝐧𝐢 𝟏.𝟓 𝐏𝐫𝐨"
            )

            buttons = [[InlineKeyboardButton("[ ᴄᴀɴᴄᴇʟ ]", callback_data="translator_cancel_ongoing")]]
            try:
                await msg.edit(progress_text, reply_markup=InlineKeyboardMarkup(buttons))
            except:
                pass

            translated = await translate_batch(batch_texts)

            if translated is None:
                 await msg.edit("❌ <b>Gemini API Failure!</b> Translation stopped.")
                 return

            for j, translated_text in enumerate(translated):
                if j < len(batch):
                    batch[j]['text'] = translated_text

        # 100% Progress
        bar = get_progress_bar(100)
        progress_text = (
            "‣ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐀𝐈 𝐓𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐢𝐧𝐠...\n"
            f"[{bar}] 100%\n"
            f"‣ 𝐋𝐢𝐧𝐞𝐬 : {total_lines} / {total_lines}\n"
            "‣ 𝐄𝐧𝐠𝐢𝐧𝐞 : 𝐆𝐞𝐦𝐢𝐧𝐢 𝟏.𝟓 𝐏𝐫𝐨"
        )
        await msg.edit(progress_text)

        if is_srt:
            translated_content = ""
            for item in parsed_data:
                if 'raw' in item:
                    translated_content += item['raw'] + "\n\n"
                else:
                    translated_content += f"{item['index']}\n{item['timestamp']}\n{item['text']}\n\n"
        else:
            lines = list(header)
            for item in parsed_data:
                if 'raw' in item:
                    lines.append(item['raw'])
                else:
                    lines.append(",".join(item['prefix']) + "," + item['text'])
            translated_content = "\n".join(lines)

        output_filename = os.path.splitext(message.document.file_name)[0] + "_Hinglish" + os.path.splitext(message.document.file_name)[1]
        output_path = os.path.join(download_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        caption = (
            "> ✅ 𝖳𝖱𝖠𝖭𝖲𝖫𝖠𝖳𝖨𝖮𝖭 𝖢𝖮𝖬𝖯𝖫𝖤𝖳𝖤\n"
            "> ➤ ʏᴏᴜʀ sᴜʙᴛɪᴛʟᴇs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇ-ᴍᴀsᴛᴇʀᴇᴅ ᴡɪᴛʜ ᴀɪ ᴘʀᴇᴄɪsɪᴏɴ. ᴇɴᴊᴏʏ ᴛʜᴇ ᴀᴜᴛʜᴇɴᴛɪᴄ ᴀɴɪᴍᴇ ᴠɪʙᴇ ɪɴ ʜɪɴɢʟɪsʜ!\n"
            "ᴍᴀᴅᴇ ᴡɪᴛʜ 💙 ʙʏ 𝐆𝐨𝐣𝐨."
        )
        await upload_doc(message, msg, 0, output_filename, output_path, caption=caption)

    except Exception as e:
        LOGGER.error(f"Error during translation: {e}")
        await msg.edit(f"❌ <b>An error occurred during translation:</b>\n<code>{e}</code>")
    finally:
        if user_id in translator_sessions:
            del translator_sessions[user_id]
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
        if 'output_path' in locals() and os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass
