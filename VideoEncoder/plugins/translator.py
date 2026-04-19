
import os
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from .. import LOGGER, download_dir
from ..utils.uploads.telegram import upload_doc

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

import google.generativeai as genai
# 1. Force use stable v1 API
genai.configure(api_key=Config.GEMINI_API_KEY)
# 2. Use the standard model name without 'models/' prefix
model = genai.GenerativeModel('gemini-1.5-flash')
# 3. Test the connection immediately
try:
    response = model.generate_content('test')
    print("DEBUG: API Connection Successful")
except Exception as e:
    print(f"DEBUG: Critical API Error: {e}")

def parse_srt(content):
    """Simple SRT parser that returns list of blocks."""
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
    """Simple ASS parser that returns header and list of event blocks."""
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

async def translate_chunk(chunk_text):
    """Translates a chunk of text using Gemini AI with retry logic."""
    if not chunk_text.strip():
        return chunk_text

    for attempt in range(2):
        try:
            response = await asyncio.to_thread(model.generate_content, chunk_text)
            return response.text.strip()
        except Exception as e:
            error_msg = f'❌ Gemini Error: {e.message if hasattr(e, "message") else str(e)}'
            LOGGER.error(error_msg)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            return error_msg

@Client.on_message(filters.command("translate") & filters.private)
async def translate_cmd_handler(bot: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a .ass or .srt file with /translate")
        return

    replied = message.reply_to_message
    if not (replied.document and replied.document.file_name and replied.document.file_name.lower().endswith((".ass", ".srt"))):
        await message.reply_text("❌ Please reply to a valid .ass or .srt file.")
        return

    if not Config.GEMINI_API_KEY:
        await message.reply_text("❌ Error: Gemini API Key not found in Config.")
        return

    status_msg = await message.reply_text("⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠] : 𝐑𝐞𝐚𝐝𝐢𝐧𝐠 𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐬𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐭𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐢𝐨𝐧...")

    print("Reading File")
    file_name = replied.document.file_name
    file_path = await replied.download(file_name=os.path.join(download_dir, file_name))

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        is_srt = file_path.lower().endswith(".srt")
        translated_content = ""

        if is_srt:
            blocks = re.split(r'\n\s*\n', content.strip())
            total_chunks = (len(blocks) + 24) // 25
            translated_blocks = []

            for i in range(0, len(blocks), 25):
                current_chunk = (i // 25) + 1
                await status_msg.edit(f"⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠] : Translating chunk {current_chunk}/{total_chunks}...")

                chunk = blocks[i : i + 25]
                chunk_text = "\n\n".join(chunk)

                translated_chunk_text = await translate_chunk(chunk_text)
                if translated_chunk_text.startswith("❌ Gemini Error:"):
                    await status_msg.edit(translated_chunk_text)
                    return

                translated_blocks.append(translated_chunk_text)

            translated_content = "\n\n".join(translated_blocks)
        else:
            header, events = parse_ass(content)

            # This simple ASS chunking assumes Dialogue: lines are sequential at the end or we just process all Dialogue: lines together
            # To be safe and preserve order, we'll process chunks of events.
            total_chunks = (len(events) + 79) // 80
            final_events = []

            for i in range(0, len(events), 80):
                current_chunk = (i // 80) + 1
                await status_msg.edit(f"⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠] : Translating chunk {current_chunk}/{total_chunks}...")

                chunk = events[i : i + 80]
                # Prepare text for Gemini: only Dialogue lines
                chunk_lines = []
                for item in chunk:
                    if 'text' in item:
                        chunk_lines.append(",".join(item['prefix']) + "," + item['text'])
                    else:
                        chunk_lines.append(item['raw'])

                chunk_text = "\n".join(chunk_lines)
                translated_chunk_text = await translate_chunk(chunk_text)
                if translated_chunk_text.startswith("❌ Gemini Error:"):
                    await status_msg.edit(translated_chunk_text)
                    return

                # Reassemble: we expect the same number of lines
                translated_lines = translated_chunk_text.splitlines()
                if len(translated_lines) != len(chunk_lines):
                    # Fallback if AI didn't return exact number of lines, though unlikely with the new prompt
                    LOGGER.warning(f"ASS Chunk mismatch: {len(translated_lines)} vs {len(chunk_lines)}")

                final_events.append(translated_chunk_text)

            translated_content = "\n".join(header) + "\n" + "\n".join(final_events)

        output_filename = os.path.splitext(file_name)[0] + "_Hinglish" + os.path.splitext(file_name)[1]
        output_path = os.path.join(download_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        print("Success")
        caption = f"✅ Translated by AI (Hinglish)\nFile: <code>{output_filename}</code>"
        await upload_doc(message, status_msg, 0, output_filename, output_path, caption=caption)

    except Exception as e:
        LOGGER.error(f"Translation logic error: {e}")
        await status_msg.edit(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
