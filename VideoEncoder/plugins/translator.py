from ..utils.common import edit_msg
import os
import asyncio
import re
import httpx
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .. import LOGGER, download_dir
from ..utils.uploads.telegram import upload_doc
from ..utils.database.access_db import db
from ..utils.encoding import extract_subtitle, get_width_height

ANALYZER_PROMPT = (
    "Analyze the raw English subtitle lines and context. "
    "Output ONLY a JSON object with these keys: "
    "{\"gender\": \"male/female\", \"tone\": \"casual/serious\", \"context\": \"summary\"}."
)

TRANSLATOR_PROMPT = (
    "You are a professional Anime Subtitler. Use the Phase 1 analysis to translate into punchy, Street-Style Hinglish.\n\n"
    "Rules:\n"
    "- Match gender and tone from analysis.\n"
    "- Use 'Isey'/'Usey'.\n"
    "- Keep 'Oh' for reactions.\n"
    "- Use 'Abey', 'Arey', 'Yaar'.\n"
    "- Ensure flow feels natural, not robotic.\n"
    "- Keep sentences short and punchy like professional subbing styles.\n"
    "- Output ONLY the translated text string."
)

TRANSLATE_PIC = "https://graph.org/file/600586a9a49029c2e98f1-90c27ea7986142ea7a.jpg"
TRANSLATE_TEXT = """<blockquote>✨ ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ᴇɴɢɪɴᴇ ✨
ᴘʟᴇᴀsᴇ sᴇʟᴇᴄᴛ ᴀ ᴍᴏᴅᴇʟ ᴛᴏ sᴛᴀʀᴛ ʜɪɴɢʟɪsʜ ᴛʀᴀɴsʟᴀᴛɪᴏɴ.</blockquote>
<blockquote expandable>ʜᴏᴡ ᴛᴏ ᴛʀᴀɴsʟᴀᴛᴇ - sᴛᴇᴘ ʙʏ sᴛᴇᴘ ɢᴜɪᴅᴇ:
➼ sᴛᴇᴘ 1: ɢᴇᴛ ɢʀᴏǫ ᴋᴇʏ | <a href='https://console.groq.com/keys?hl=en-IN'>ᴄʟɪᴄᴋ ʜᴇʀᴇ</a> ᴛᴏ ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴀᴘɪ ᴋᴇʏ.
➼ sᴛᴇᴘ 2: ᴜᴘʟᴏᴀᴅ ʏᴏᴜʀ ғɪʟᴇ
sᴇɴᴅ ʏᴏᴜʀ .ᴀss ᴏʀ sᴜʙᴛɪᴛʟᴇ ғɪʟᴇ ᴅɪʀᴇᴄᴛʟʏ ᴛᴏ ᴛʜᴇ ʙᴏᴛ.
➼ sᴛᴇᴘ 3: sᴇʟᴇᴄᴛ ᴛʜᴇ ᴇɴɢɪɴᴇ
ᴄʜᴏᴏsᴇ ᴛʜᴇ ʜɪɢʜ-sᴛᴀʙɪʟɪᴛʏ ɢʀᴏǫ ᴇɴɢɪɴᴇ ғᴏʀ ʟɪɢʜᴛɴɪɴɢ-ғᴀsᴛ ʀᴇsᴜʟᴛs.
➼ sᴛᴇᴘ 4: ᴡᴀɪᴛ ғᴏʀ ᴘʀᴏᴄᴇssɪɴɢ
ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ sᴘʟɪᴛ ʏᴏᴜʀ ғɪʟᴇ ɪɴᴛᴏ ᴍɪᴄʀᴏ-ᴄʜᴜɴᴋs ᴛᴏ ᴇɴsᴜʀᴇ ʜɪɢʜ-ǫᴜᴀʟɪᴛʏ ʜɪɴɢʟɪsʜ ᴛʀᴀɴsʟᴀᴛɪᴏɴ.</blockquote>
ɴᴏᴛᴇ: ᴛʜᴇ ʙᴏᴛ ɴᴏᴡ ᴜsᴇs ᴀɴ ᴏᴘᴛɪᴍɪᴢᴇᴅ ɢʀᴏǫ-ᴏɴʟʏ ᴀʀᴄʜɪᴛᴇᴄᴛᴜʀᴇ ғᴏʀ 100% sᴛᴀʙɪʟɪᴛʏ!"""

# Temporary storage for file metadata linked to message ID
translation_data = {}

TRANSLATE_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("ʟʟᴀᴍᴀ 𝟹.𝟹 𝟽𝟶ʙ 🚀", callback_data="trans_llama33_groq"),
        InlineKeyboardButton("❌ Cancel", callback_data="close_btn")
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


async def call_groq(system_prompt, user_content, api_key):
    if not user_content.strip(): return user_content
    model_name = "llama-3.3-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}], "temperature": 0.2}

    async with httpx.AsyncClient() as client:
        for attempt in range(2):
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                if response.status_code == 200:
                    data = response.json(); translated_text = data['choices'][0]['message']['content'].strip()
                    print(f"DEBUG Groq Response: {translated_text}")
                    translated_text = translated_text.replace('```json', '').replace('```', '').strip()
                    if translated_text.strip() == user_content.strip():
                        return "RETRY_REQUIRED"
                    await asyncio.sleep(2); return translated_text
                elif response.status_code in [429, 503]:
                    return str(response.status_code)
                else: return f"❌ Groq Error: {response.status_code} - {response.text}"
            except Exception as e:
                if attempt == 0: await asyncio.sleep(2); continue
                return f"❌ Groq Error: {str(e)}"

async def translate_subtitle_chunks(chunk_queue, to_translate, api_pool, status_msg):
    translated_texts = []
    idx = 0
    while idx < len(chunk_queue):
        original_lines = to_translate[idx*10 : (idx+1)*10]
        chunk = chunk_queue[idx]

        success = False
        while not success:
            # Phase 1: The Analyst (Key 1 ONLY)
            api_key_1 = api_pool[0]
            await edit_msg(status_msg, f"⏳ [𝐀𝐧𝐚𝐥𝐲𝐬𝐭] : Analyzing chunk {idx+1}/{len(chunk_queue)}...")
            analysis_res = await call_groq(ANALYZER_PROMPT, chunk, api_key_1)

            if analysis_res in ["RETRY_REQUIRED", "429", "503"] or analysis_res.startswith("❌"):
                # For Analyst, if it fails we just use a default context to not block forever,
                # but following strict logic, we should probably retry.
                # The instructions don't specify analyst failover, so we'll try once more then default.
                await asyncio.sleep(5)
                analysis_res = await call_groq(ANALYZER_PROMPT, chunk, api_key_1)
                if analysis_res in ["RETRY_REQUIRED", "429", "503"] or analysis_res.startswith("❌"):
                    analysis_res = '{"gender": "neutral", "tone": "casual", "context": "general anime scene"}'

            # Phase 2: The Translator (Primary: Key 4, Failover: Key 5)
            api_key_4 = api_pool[3] if len(api_pool) > 3 else api_pool[0]
            api_key_5 = api_pool[4] if len(api_pool) > 4 else (api_pool[3] if len(api_pool) > 3 else api_pool[0])

            await edit_msg(status_msg, f"⏳ [𝐓𝐫𝐚𝐧𝐬𝐥𝐚𝐭𝐨𝐫] : Translating chunk {idx+1}/{len(chunk_queue)}...")
            res = await call_groq(TRANSLATOR_PROMPT, f"Analysis:\n{analysis_res}\n\nLines to Translate:\n{chunk}", api_key_4)

            if res in ["RETRY_REQUIRED", "429", "503"] or res.startswith("❌"):
                # Phase 3: Failover
                await edit_msg(status_msg, f"⏳ Key 4 failed. Switching to Key 5 in 5-10s...")
                await asyncio.sleep(7)

                res = await call_groq(TRANSLATOR_PROMPT, f"Analysis:\n{analysis_res}\n\nLines to Translate:\n{chunk}", api_key_5)

                if res in ["RETRY_REQUIRED", "429", "503"] or res.startswith("❌"):
                    await edit_msg(status_msg, f"⏳ Key 5 failed. Pausing 30 seconds before full retry...")
                    await asyncio.sleep(30)
                    continue # Restart the full cycle from Phase 1
                else:
                    success = True
            else:
                success = True

        # Process the successful translation
        res_lines = res.strip().split('\n')
        for i, line in enumerate(original_lines):
            if i < len(res_lines):
                trans_line = res_lines[i].strip()
                trans_line = re.sub(r'^\[.*?\]:\s*', '', trans_line).strip()
                translated_texts.append(trans_line)
            else:
                translated_texts.append(line)
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
        if len(api_pool) < 5:
            await cb.answer("❌ You need at least 5 Groq API Keys for Studio Flow!", show_alert=True)
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
    status_msg = await bot.send_message(user_id, "⏳ [𝐒𝐭𝐮𝐝𝐢𝐨 𝐅𝐥𝐨𝐰] : 𝐈𝐧𝐢𝐭𝐢𝐚𝐥𝐢𝐳𝐢𝐧𝐠 𝐀𝐫𝐜𝐡𝐢𝐭𝐞𝐜𝐭𝐮𝐫𝐞...")

    file_path = await bot.download_media(
        message=file_id,
        file_name=os.path.join(download_dir, file_name)
    )

    if file_data and file_data.get('is_video'):
        await edit_msg(status_msg, "⏳ [𝐒𝐭𝐮𝐝𝐢𝐨 𝐅𝐥𝐨𝐰] : Extracting subtitles from video...")
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

            # Send 10 lines at once for context
            chunk_queue = []
            for i in range(0, len(to_translate), 10):
                lines_with_names = []
                for j in range(i, min(i+10, len(to_translate))):
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

            # Send 10 lines at once for context
            chunk_queue = []
            for i in range(0, len(to_translate), 10):
                lines_with_names = []
                for j in range(i, min(i+10, len(to_translate))):
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
            InlineKeyboardButton("🔙 Back to Home", callback_data="back_start"),
            InlineKeyboardButton("❌ Close", callback_data="close_btn")
        ]])

        await upload_doc(target_msg, status_msg, 0, output_filename, output_path, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        LOGGER.error(f"Translation Error: {e}")
        await edit_msg(status_msg, f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if 'output_path' in locals() and os.path.exists(output_path): os.remove(output_path)
