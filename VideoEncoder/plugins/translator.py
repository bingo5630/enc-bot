
import os
import asyncio
import re
import google.generativeai as genai
from pyrogram import Client, filters
from pyrogram.types import Message
from .. import LOGGER, download_dir
from ..utils.uploads.telegram import upload_doc

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini
if Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

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

async def translate_batch(batch_texts):
    """Translates a batch of texts using Gemini AI."""
    if not batch_texts:
        return []

    print("Calling Gemini")
    numbered_text = "\n".join([f"{i+1}: {text}" for i, text in enumerate(batch_texts)])
    prompt = (
        "You are a professional Anime/Manhwa translator. Translate the following numbered segments into natural Hinglish. "
        "Keep the original vibe and all formatting like {\\pos(x,y)}. "
        "Preserve the numbering format 'n: translated_text'. Output ONLY the translated segments.\n\n"
        f"{numbered_text}"
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        lines = response.text.strip().splitlines()
        translated = []
        for line in lines:
            match = re.match(r'^\d+:\s*(.*)', line.strip())
            if match:
                translated.append(match.group(1))

        # Fallback if AI output is slightly misformatted
        if len(translated) != len(batch_texts):
            LOGGER.warning(f"Batch mismatch: {len(translated)} vs {len(batch_texts)}")
            if len(translated) > len(batch_texts):
                return translated[:len(batch_texts)]
            else:
                return translated + batch_texts[len(translated):]
        return translated
    except Exception as e:
        LOGGER.error(f"Gemini API Error: {e}")
        return None

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
        translatable = []

        if is_srt:
            parsed_data = parse_srt(content)
            for item in parsed_data:
                if 'text' in item and item['text'].strip():
                    translatable.append(item)
        else:
            header, parsed_data = parse_ass(content)
            for item in parsed_data:
                if 'text' in item and item['text'].strip():
                    translatable.append(item)

        if not translatable:
            await status_msg.edit("❌ No translatable text found.")
            return

        # Processing in batches
        batch_size = 10
        for i in range(0, len(translatable), batch_size):
            batch = translatable[i : i + batch_size]
            batch_texts = [item['text'] for item in batch]

            translated_texts = await translate_batch(batch_texts)
            if translated_texts is None:
                await status_msg.edit("❌ Gemini API Failure during translation.")
                return

            for j, t_text in enumerate(translated_texts):
                batch[j]['text'] = t_text

        # Reconstruct content
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
