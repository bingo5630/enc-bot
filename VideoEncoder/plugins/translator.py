from ..utils.common import edit_msg
import os
import asyncio
import re
import httpx
from difflib import SequenceMatcher
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .. import LOGGER, download_dir
from ..utils.uploads.telegram import upload_doc
from ..utils.database.access_db import db
from ..utils.encoding import extract_subtitle, get_width_height

ANALYZER_PROMPT = (
    "Analyze the following anime subtitle lines and provide a simple 'Style Guide' for this batch.\n"
    "Identify:\n"
    "1. Gender of speakers (Eri is female, Ogino is male).\n"
    "2. Tone (Informal/Tu or Formal/Tum).\n"
    "Instructions for Style Guide: Output a simple line like: 'Gender: Male, Tone: Informal/Tu, Avoid Shuddh Hindi, Keep it conversational'."
)

TRANSLATOR_PROMPT = (
    "You are a professional Anime Subtitle Translator. Use the provided Style Guide to translate lines into short, cool Hinglish (Anime Fury Style).\n\n"
    "CORE RULE: Use colloquial Hinglish. 'Mujhe khed hai' is forbidden—use 'Sorry bhai'. 'Anumati' is forbidden—use 'Permission'. Casual youth slang only.\n\n"
    "LINGUISTIC RULES:\n"
    "- SHORT & PUNCHY: Keep it simple. Translate the 'vibe'.\n"
    "- NO SHUDDH HINDI: Avoid formal Hindi words. Use Hinglish equivalents.\n"
    "- NO ENGLISH SENTENCES: Ensure it's Hinglish, not just plain English.\n"
    "- SPELLING: Use 'isey' (never ise), 'usey' (never use), 'arey' (never are), 'jaa' (never ja).\n"
    "- GENDER: Eri is female (feminine verbs: rahi hai/kiya), Ogino is male (masculine: raha hai/kiya).\n"
    "- TU/TERA: Use 'Tu/Tujhe/Tera' for casual. 'Tum' only if formal.\n\n"
    "PROTECTION:\n"
    "- Do NOT modify ASS tags like {\\an8}, {\\pos} or line breaks \\N.\n\n"
    "OUTPUT: UTF-8 plain text only. One translated line per input line. No extra text, no Markdown, no JSON."
)

TRANSLATE_PIC = "https://graph.org/file/600586a9a49029c2e98f1-90c27ea7986142ea7a.jpg"
TRANSLATE_TEXT = "✨ ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ᴇɴɢɪɴᴇ ✨\nᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ᴀ ᴍᴏᴅᴇʟ ᴛᴏ sᴛᴀʀᴛ ʜɪɴɢʟɪsʜ ᴛʀᴀɴsʟᴀᴛɪᴏɴ."

# Temporary storage for file metadata linked to message ID
translation_data = {}

SETUP_GUIDE_TEXT = (
    "✨ ʜᴏᴡ ᴛᴏ sᴇᴛ ᴜᴘ ʏᴏᴜʀ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ᴇɴɢɪɴᴇ ✨\n\n"
    "𝟷️⃣ [ᴄʟɪᴄᴋ ʜᴇʀᴇ ғᴏʀ ɢʀᴏǫ ᴋᴇʏ](https://console.groq.com/keys)\n"
    "👉 sᴇɴᴅ ʏᴏᴜʀ ᴋᴇʏ ᴜsɪɴɢ /set_groq_api ᴛᴏ ᴀᴅᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ ᴀᴘɪ ᴘᴏᴏʟ.\n\n"
    "<blockquote expandable>➼ <b>Step 1: Get Groq Key</b>\n"
    "Visit Groq Console and create an API Key.\n\n"
    "➼ <b>Step 2: Add to Pool</b>\n"
    "Use /set_groq_api [key] to add keys to your pool.\n\n"
    "➼ <b>Step 3: Reply to Subtitle</b>\n"
    "Reply to any .ass or .srt file with /translate.\n\n"
    "➼ <b>Step 4: Select Model</b>\n"
    "Choose Llama 3.3 70B and wait for the AI to work its magic!</blockquote>"
)

SETUP_GUIDE_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Back to Home", callback_data="backToStart"),
        InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_translator")
    ]
])

TRANSLATE_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("ʟʟᴀᴍᴀ 𝟹.𝟹 𝟽𝟶ʙ 🚀", callback_data="trans_llama33_groq"),
        InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ᴛʀᴀɴsʟᴀᴛᴇ? ❓", callback_data="how_to_translate")
    ]
])

def parse_srt(content):
    content = content.replace('\r\n', '\n')
    blocks = re.split(r'\n\s*\n', content.strip())
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3 and (lines[0].isdigit() or '-->' in lines[1]):
            parsed.append({
                'index': lines[0],
                'timestamp': lines[1],
                'text': '\n'.join(lines[2:])
            })
        else:
            parsed.append({'raw': block})
    return parsed

def protect_tags(text, is_ass=True):
    """Protects override tags from being translated by the AI."""
    placeholders = []
    if is_ass:
        # Protect {\...} tags
        tags = re.findall(r'\{[^\}]+\}', text)
        for i, tag in enumerate(tags):
            placeholder = f"__TAG_{i}__"
            text = text.replace(tag, placeholder, 1)
            placeholders.append(tag)
    else:
        # Protect <i>...</i> tags etc for SRT
        tags = re.findall(r'<[^>]+>', text)
        for i, tag in enumerate(tags):
            placeholder = f"__TAG_{i}__"
            text = text.replace(tag, placeholder, 1)
            placeholders.append(tag)
    return text, placeholders

def restore_tags(text, placeholders):
    """Restores protected tags back into the translated text."""
    for i, tag in enumerate(placeholders):
        placeholder = f"__TAG_{i}__"
        text = text.replace(placeholder, tag, 1)
    return text

def parse_ass(content):
    lines = content.replace('\r\n', '\n').split('\n')
    header = []
    events = []
    in_events = False
    playresx, playresy = 640, 360 # Locked resolution

    for line in lines:
        if line.strip().startswith('PlayResX:'):
            header.append(f"PlayResX: {playresx}")
            continue
        if line.strip().startswith('PlayResY:'):
            header.append(f"PlayResY: {playresy}")
            continue

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
                    events.append({'prefix': ",".join(parts[0:9]) + ",", 'text': parts[9], 'name': parts[4].strip()})
                else:
                    events.append({'raw': line})
            else:
                events.append({'raw': line})
    return header, events, playresx, playresy


async def call_groq(system_prompt, user_content, api_key, temperature=0.2):
    if not user_content.strip(): return user_content
    model_name = "llama-3.3-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}], "temperature": temperature}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            if response.status_code == 200:
                data = response.json(); translated_text = data['choices'][0]['message']['content'].strip()
                translated_text = translated_text.replace('```json', '').replace('```', '').strip()
                if translated_text.strip() == user_content.strip():
                    return "RETRY_REQUIRED"
                return translated_text
            elif response.status_code in [429, 503]:
                return str(response.status_code)
            else: return f"❌ Groq Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"❌ Groq Error: {str(e)}"

async def translate_subtitle_chunks(chunk_queue, to_translate, api_pool, status_msg):
    translated_texts = []
    # Local pool for round-robin rotation
    pool = list(api_pool)
    idx = 0

    while idx < len(chunk_queue):
        original_lines = to_translate[idx*20 : (idx+1)*20]
        chunk = chunk_queue[idx]
        style_guide = ""

        # STAGE 1: THE ANALYZER
        keys_tried = 0
        while not style_guide:
            api_key = pool[0]
            await edit_msg(status_msg, f"⏳ [𝐒𝐭𝐚𝐠𝐞 𝟏: 𝐀𝐧𝐚𝐥𝐲𝐳𝐞𝐫] : Batch {idx+1}/{len(chunk_queue)} (Key: {api_key[:6]}...)")
            res = await call_groq(ANALYZER_PROMPT, chunk, api_key)

            if res in ["429", "503", "RETRY_REQUIRED"]:
                # Always rotate on rate limit or retry req
                pool.append(pool.pop(0))
                keys_tried += 1
                if keys_tried >= len(pool):
                    await edit_msg(status_msg, f"⚠️ All {len(pool)} keys rate-limited. Sleeping 10s... (Batch {idx+1}/{len(chunk_queue)})")
                    await asyncio.sleep(10)
                    keys_tried = 0
                continue

            if res.startswith("❌"): return res, None

            style_guide = res
            # Success - Rotate anyway for Stage 2 to load balance
            pool.append(pool.pop(0))
            keys_tried = 0

        # STAGE 2: THE TRANSLATOR
        translated_chunk_lines = []
        temp = 0.2
        keys_tried = 0
        while not translated_chunk_lines:
            api_key = pool[0]
            await edit_msg(status_msg, f"⏳ [𝐒𝐭𝐚𝐠𝐞 𝟐: 𝐓𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐨𝐫] : Batch {idx+1}/{len(chunk_queue)} (Key: {api_key[:6]}..., Temp: {temp})")
            res = await call_groq(TRANSLATOR_PROMPT, f"Style Guide:\n{style_guide}\n\nLines to Translate:\n{chunk}", api_key, temperature=temp)

            if res in ["429", "503", "RETRY_REQUIRED"]:
                pool.append(pool.pop(0))
                keys_tried += 1
                if keys_tried >= len(pool):
                    await edit_msg(status_msg, f"⚠️ All {len(pool)} keys rate-limited. Sleeping 10s... (Batch {idx+1}/{len(chunk_queue)})")
                    await asyncio.sleep(10)
                    keys_tried = 0
                continue

            if res.startswith("❌"): return res, None

            # Anti-Lazy Shield & Cleanup
            res_lines = [l.strip() for l in res.strip().split('\n') if l.strip()]
            is_failing = False

            # Check length: if output is significantly shorter than input
            if len(res_lines) < len(original_lines) * 0.7:
                is_failing = True

            temp_lines = []
            for i, line in enumerate(original_lines):
                if i < len(res_lines):
                    trans_line = re.sub(r'^\s*\[.*?\]:\s*', '', res_lines[i]).strip()
                    # Similarity check (Anti-Lazy Shield)
                    if SequenceMatcher(None, line.lower(), trans_line.lower()).ratio() >= 0.8:
                        is_failing = True
                        break
                    temp_lines.append(trans_line)
                else:
                    # Pad missing lines if not completely failing
                    temp_lines.append(line)

            if is_failing:
                pool.append(pool.pop(0))
                keys_tried += 1
                temp = min(temp + 0.2, 1.0) # Increase creativity on failure
                await edit_msg(status_msg, f"🔄 Lazy response detected. Retrying batch {idx+1} with temp {temp}...")
                if keys_tried >= len(pool):
                    await asyncio.sleep(5)
                    keys_tried = 0
                continue

            translated_chunk_lines = temp_lines
            # Success - Rotate anyway for next chunk
            pool.append(pool.pop(0))
            keys_tried = 0

        translated_texts.extend(translated_chunk_lines)
        idx += 1

    return None, translated_texts

@Client.on_message(filters.command("translate") & filters.private)
async def translate_cmd_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a video, .ass, or .srt file with /translate")
        return

    replied = message.reply_to_message
    is_video = (replied.video or (replied.document and replied.document.mime_type and replied.document.mime_type.startswith("video/")))
    is_subtitle = (replied.document and replied.document.file_name and replied.document.file_name.lower().endswith((".ass", ".srt")))

    if not (is_video or is_subtitle):
        await message.reply_text("❌ Please reply to a valid video, .ass, or .srt file.")
        return

    sent_msg = await message.reply_photo(
        photo=TRANSLATE_PIC,
        caption=TRANSLATE_TEXT,
        reply_markup=TRANSLATE_BUTTONS,
        has_spoiler=True
    )

    unique_key = f"{replied.chat.id}_{sent_msg.id}"
    translation_data[unique_key] = {
        'file_id': replied.document.file_id if replied.document else replied.video.file_id,
        'file_name': replied.document.file_name if replied.document else (replied.video.file_name or "video.mp4"),
        'chat_id': replied.chat.id,
        'message_id': replied.id,
        'user_id': user_id,
        'is_video': is_video
    }

@Client.on_message(filters.command("set_groq_api") & filters.private)
async def set_groq_handler(bot: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /set_groq_api YOUR_KEY_HERE")
        return
    api_key = message.command[1]
    await db.add_groq_api_key(message.from_user.id, api_key)
    await message.reply_text("✅ Groq API Key added to pool successfully!")

@Client.on_message(filters.command("view_api") & filters.private)
async def view_api_handler(bot: Client, message: Message):
    api_pool = await db.get_groq_api_pool(message.from_user.id)
    if not api_pool:
        await message.reply_text("❌ Your API Pool is empty.")
        return

    text = "📂 **Your Groq API Pool:**\n\n"
    for i, key in enumerate(api_pool, 1):
        masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
        text += f"{i}. <code>{masked_key}</code>\n"

    await message.reply_text(text)

@Client.on_message(filters.command("clear_api") & filters.private)
async def clear_api_handler(bot: Client, message: Message):
    await db.clear_groq_api_pool(message.from_user.id)
    await message.reply_text("✅ All Groq API Keys cleared from pool!")


async def process_translation(bot, cb, model_type, model_name):
    # This will be called from callbacks_.py
    user_id = cb.from_user.id

    if model_type == "groq":
        api_pool = await db.get_groq_api_pool(user_id)
        if not api_pool:
            await cb.answer("❌ Groq API Pool is Empty!", show_alert=True)
            return
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
    status_msg = await bot.send_message(user_id, "⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜ᴇ𝐬𝐬ɪ𝐧𝐠] : 𝐑𝐞𝐚𝐝𝐢𝐧𝐠 𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐬𝐭ᴀ𝐫ᴛɪ𝐧𝐠 ᴛ𝐫𝐚𝐧𝐬𝐥𝐚ᴛɪ𝐨𝐧...")

    file_path = await bot.download_media(
        message=file_id,
        file_name=os.path.join(download_dir, file_name)
    )

    if file_data and file_data.get('is_video'):
        await edit_msg(status_msg, "⏳ [𝐀𝐈 𝐏𝐫𝐨𝐜ᴇ𝐬𝐬ɪ𝐧𝐠] : Extracting subtitles from video...")
        extracted = await extract_subtitle(file_path)
        if not os.path.exists(extracted):
            await edit_msg(status_msg, f"❌ Subtitle extraction failed: {extracted}")
            if os.path.exists(file_path): os.remove(file_path)
            return
        video_path = file_path # Keep track of video to get resolution later
        file_path = extracted
        file_name = os.path.basename(file_path)
    else:
        video_path = None

    # Clean up storage
    if unique_key in translation_data:
        del translation_data[unique_key]

    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()

        is_srt = file_path.lower().endswith(".srt")
        translated_content = ""

        if is_srt:
            parsed_blocks = parse_srt(content)
            to_translate = []
            tags_map = []
            names = []
            for b in parsed_blocks:
                if 'text' in b:
                    protected, placeholders = protect_tags(b['text'].replace('\n', '\\N'), is_ass=False)
                    to_translate.append(protected)
                    tags_map.append(placeholders)
                    names.append("") # SRT doesn't have speaker info in header

            # Send 20 lines at once for context
            chunk_queue = []
            for i in range(0, len(to_translate), 20):
                lines_with_names = []
                for j in range(i, min(i+20, len(to_translate))):
                    name_prefix = f"[{names[j]}]: " if names[j] else ""
                    lines_with_names.append(f"{name_prefix}{to_translate[j]}")
                chunk_queue.append("\n".join(lines_with_names))

            err, translated_texts = await translate_subtitle_chunks(chunk_queue, to_translate, api_pool, status_msg)
            if err:
                await edit_msg(status_msg, err)
                return

            final_srt = []
            trans_idx = 0
            for i, b in enumerate(parsed_blocks):
                if 'text' in b:
                    if trans_idx < len(translated_texts):
                        translated_text = restore_tags(translated_texts[trans_idx], tags_map[trans_idx])
                        translated_text = translated_text.replace('\\N', '\n').replace('\\n', '\n')
                        final_srt.append(f"{b['index']}\n{b['timestamp']}\n{translated_text}")
                        trans_idx += 1
                    else: final_srt.append(f"{b['index']}\n{b['timestamp']}\n{b['text']}")
                else: final_srt.append(b['raw'])
            translated_content = "\n\n".join(final_srt)
        else:
            header, events, playresx, playresy = parse_ass(content)

            to_translate = []
            tags_map = []
            names = []
            for item in events:
                if 'text' in item:
                    protected, placeholders = protect_tags(item['text'], is_ass=True)
                    to_translate.append(protected)
                    tags_map.append(placeholders)
                    names.append(item.get('name', ''))

            # Send 20 lines at once for context
            chunk_queue = []
            for i in range(0, len(to_translate), 20):
                lines_with_names = []
                for j in range(i, min(i+20, len(to_translate))):
                    name_prefix = f"[{names[j]}]: " if names[j] else ""
                    lines_with_names.append(f"{name_prefix}{to_translate[j]}")
                chunk_queue.append("\n".join(lines_with_names))

            err, translated_texts = await translate_subtitle_chunks(chunk_queue, to_translate, api_pool, status_msg)
            if err:
                await edit_msg(status_msg, err)
                return

            final_events = []
            trans_idx = 0
            for i, item in enumerate(events):
                if 'text' in item:
                    if trans_idx < len(translated_texts):
                        # Restore tags in the translated text
                        restored = restore_tags(translated_texts[trans_idx], tags_map[trans_idx])
                        # Recombine with original prefix
                        final_events.append(item['prefix'] + restored)
                        trans_idx += 1
                    else: final_events.append(item['prefix'] + item['text'])
                else: final_events.append(item['raw'])
            translated_content = "\n".join(header) + "\n" + "\n".join(final_events)
        output_filename = os.path.splitext(file_name)[0] + "_Hinglish" + os.path.splitext(file_name)[1]
        output_path = os.path.join(download_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        caption = f"✅ Translated by AI (Hinglish)\nFile: <code>{output_filename}</code>"
        # If replied is still None (fallback failed), use cb.message as a last resort to send the file
        target_msg = replied if replied else cb.message

        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Home", callback_data="backToStart"),
            InlineKeyboardButton("❌ Close", callback_data="closeMeh")
        ]])

        await upload_doc(target_msg, status_msg, 0, output_filename, output_path, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        LOGGER.error(f"Translation Error: {e}")
        await edit_msg(status_msg, f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if 'output_path' in locals() and os.path.exists(output_path): os.remove(output_path)
