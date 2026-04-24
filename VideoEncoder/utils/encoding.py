

import asyncio
import json
import math
import os
import re
import shutil
import shlex
import subprocess
import time

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .. import LOGGER, download_dir, encode_dir, ASSETS_DIR
from .database.access_db import db
from .display_progress import TimeFormatter


def get_codec(filepath, channel='v:0'):
    try:
        output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                                          '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                                          'default=nokey=1:noprint_wrappers=1', filepath])
        return output.decode('utf-8').split()
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"ffprobe failed for {filepath}: {e}")
        return []
    except Exception as e:
        LOGGER.error(f"ffprobe exception for {filepath}: {e}")
        return []

def get_media_streams(filepath):
    try:
        cmd = ['ffprobe', '-hide_banner', '-print_format', 'json', '-show_streams', filepath]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return json.loads(output.decode('utf-8')).get('streams', [])
    except Exception as e:
        LOGGER.error(f"Failed to get media streams: {e}")
        return []

async def extract_subtitle(filepath):
    streams = get_media_streams(filepath)
    sub_stream = None
    sub_index = -1

    # Text-based subtitle codecs FFmpeg can extract to SRT or ASS
    text_codecs = ['srt', 'ass', 'ssa', 'mov_text', 'text', 'subrip', 'webvtt']

    for i, stream in enumerate(streams):
        if stream.get('codec_type') == 'subtitle':
            codec = stream.get('codec_name', '').lower()
            if codec in text_codecs:
                sub_stream = stream
                # We need to find the subtitle stream index among subtitle streams,
                # but FFmpeg -map 0:s:N refers to the Nth subtitle stream.
                # Let's count subtitle streams to find the correct N.
                sub_count = 0
                for s in streams[:i]:
                    if s.get('codec_type') == 'subtitle':
                        sub_count += 1
                sub_index = sub_count
                break

    if not sub_stream:
        # Check if there are any subtitles at all, even if image-based
        any_sub = any(s.get('codec_type') == 'subtitle' for s in streams)
        if any_sub:
            return "No text-based subtitle tracks found. Image-based subtitles (PGS/DVD) cannot be extracted."
        return "No Subtitle Track Found"

    codec_name = sub_stream.get('codec_name', 'srt').lower()

    # Determine extension
    if codec_name in ['ass', 'ssa']:
        ext = '.ass'
    else:
        ext = '.srt'

    path, _ = os.path.splitext(filepath)
    output = f"{path}{ext}"

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-copyts', '-i', filepath, '-map', f'0:s:{sub_index}', output]

    proc = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        return f"FFmpeg error: {stderr.decode().strip()}"

    if os.path.isfile(output) and os.path.getsize(output) > 0:
        return output
    else:
        return "Extraction failed: Output file not created or empty."


async def extract_subs(filepath, msg, user_id):

    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)
    check = get_codec(filepath, channel='s:0')
    if check == []:
        return None
    elif check == 'pgs':
        return None
    else:
        output = os.path.join(encode_dir, str(msg.id) + '.ass')

    try:
        subprocess.call(['ffmpeg', '-y', '-copyts', '-i', filepath, '-map', 's:0', output])
        # mkvextract might not be in PATH on Windows, handle gracefully
        try:
            subprocess.call(['mkvextract', 'attachments', filepath, '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16',
                            '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40'])
        except FileNotFoundError:
            LOGGER.warning("mkvextract not found, skipping attachments extraction.")
        except Exception as e:
            LOGGER.error(f"mkvextract failed: {e}")

        # Moving fonts is Linux specific and dangerous on Windows to assume /usr/share/fonts/
        # We will only attempt this on Linux-like environments or skip if it fails
        try:
            if os.name != 'nt':
                subprocess.run([f"mv -f *.JFPROJ *.FNT *.PFA *.ETX *.WOFF *.FOT *.TTF *.SFD *.VLW *.VFB *.PFB *.OTF *.GXF *.WOFF2 *.ODTTF *.BF *.CHR *.TTC *.BDF *.FON *.GF *.PMT *.AMFM  *.MF *.PFM *.COMPOSITEFONT *.PF2 *.GDR *.ABF *.VNF *.PCF *.SFP *.MXF *.DFONT *.UFO *.PFR *.TFM *.GLIF *.XFN *.AFM *.TTE *.XFT *.ACFM *.EOT *.FFIL *.PK *.SUIT *.NFTR *.EUF *.TXF *.CHA *.LWFN *.T65 *.MCF *.YTF *.F3F *.FEA *.SFT *.PFT {shlex.quote('/usr/share/fonts/')}"], shell=True)
                subprocess.run([f"mv -f *.jfproj *.fnt *.pfa *.etx *.woff *.fot *.ttf *.sfd *.vlw *.vfb *.pfb *.otf *.gxf *.woff2 *.odttf *.bf *.chr *.ttc *.bdf *.fon *.gf *.pmt *.amfm  *.mf *.pfm *.compositefont *.pf2 *.gdr *.abf *.vnf *.pcf *.sfp *.mxf *.dfont *.ufo *.pfr *.tfm *.glif *.xfn *.afm *.tte *.xft *.acfm *.eot *.ffil *.pk *.suit *.nftr *.euf *.txf *.cha *.lwfn *.t65 *.mcf *.ytf *.f3f *.fea *.sft *.pft {shlex.quote('/usr/share/fonts/')} && fc-cache -f"], shell=True)
        except Exception as e:
            LOGGER.warning(f"Font moving failed (likely not supported on this OS): {e}")

        return output
    except Exception as e:
        LOGGER.error(f"Extract subs failed: {e}")
        return None


async def get_metadata_flags(user_id):
    if not await db.get_metadata_on(user_id):
        return []

    title = await db.get_metadata_title(user_id)
    author = await db.get_metadata_author(user_id)
    artist = await db.get_metadata_artist(user_id)
    audio = await db.get_metadata_audio(user_id)
    subtitle = await db.get_metadata_subtitle(user_id)
    video = await db.get_metadata_video(user_id)

    flags = []
    if title:
        flags.extend(['-metadata', f'title={title}'])
    if author:
        flags.extend(['-metadata', f'author={author}'])
    if artist:
        flags.extend(['-metadata', f'artist={artist}'])
    if audio:
        flags.extend(['-metadata:s:a', f'title={audio}'])
    if subtitle:
        flags.extend(['-metadata:s:s', f'title={subtitle}'])
    if video:
        flags.extend(['-metadata:s:v', f'title={video}'])

    return flags

async def encode(filepath, message, msg, audio_map=None, quality=None, custom_name=None):
    filepath = os.path.abspath(filepath)
    ex = await db.get_extensions(message.from_user.id)
    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)

    if custom_name:
        output_filepathh = os.path.join(encode_dir, custom_name)
    elif ex == 'MP4':
        output_filepathh = os.path.join(encode_dir, name + '.mp4')
    elif ex == 'AVI':
        output_filepathh = os.path.join(encode_dir, name + '.avi')
    else:
        output_filepathh = os.path.join(encode_dir, name + '.mkv')

    output_filepath = output_filepathh
    subtitles_path = os.path.join(encode_dir, str(msg.id) + '.ass')

    assert(output_filepath != filepath)

    # Check Path
    if os.path.isfile(output_filepath):
        LOGGER.warning(f'"{output_filepath}": file already exists')
    else:
        LOGGER.info(filepath)

    # HEVC Encode
    x265 = await db.get_hevc(message.from_user.id)
    video_i = get_codec(filepath, channel='v:0')
    if video_i == []:
        codec = ''
    else:
        if x265:
            codec = '-c:v libx265'
        else:
            codec = '-c:v libx264'

    # Tune Encode
    tune = await db.get_tune(message.from_user.id)
    if tune:
        tunevideo = '-tune animation'
    else:
        tunevideo = '-tune film'

    # CABAC
    cbb = await db.get_cabac(message.from_user.id)
    if cbb:
        cabac = '-coder 1'
    else:
        cabac = '-coder 0'

    # Reframe
    rf = await db.get_reframe(message.from_user.id)
    if rf == '4':
        reframe = '-refs 4'
    elif rf == '8':
        reframe = '-refs 8'
    elif rf == '16':
        reframe = '-refs 16'
    else:
        reframe = ''

    # Bits
    b = await db.get_bits(message.from_user.id)
    if not b:
        codec += ' -pix_fmt yuv420p'
    else:
        codec += ' -pix_fmt yuv420p10le'

    # CRF
    crf = await db.get_crf(message.from_user.id)
    if quality == '480p':
        Crf = '-crf 28'
    elif quality == '720p':
        Crf = '-crf 24'
    elif quality == '1080p':
        Crf = '-crf 22'
    elif crf:
        Crf = f'-crf {crf}'
    else:
        await db.set_crf(message.from_user.id, crf=26)
        Crf = '-crf 26'

    # Frame
    fr = await db.get_frame(message.from_user.id)
    if fr == 'ntsc':
        frame = '-r ntsc'
    elif fr == 'pal':
        frame = '-r pal'
    elif fr == 'film':
        frame = '-r film'
    elif fr == '23.976':
        frame = '-r 24000/1001'
    elif fr == '30':
        frame = '-r 30'
    elif fr == '60':
        frame = '-r 60'
    else:
        frame = '-r 24000/1001'

    # Aspect ratio
    ap = await db.get_aspect(message.from_user.id)
    if ap:
        aspect = '-aspect 16:9'
    else:
        aspect = ''

    # Preset
    p = await db.get_preset(message.from_user.id)
    if p == 'uf':
        preset = '-preset ultrafast'
    elif p == 'sf':
        preset = '-preset superfast'
    elif p == 'vf':
        preset = '-preset veryfast'
    elif p == 'f':
        preset = '-preset fast'
    elif p == 'm':
        preset = '-preset medium'
    else:
        preset = '-preset superfast'

    # Some Optional Things
    x265 = await db.get_hevc(message.from_user.id)
    if x265:
        video_opts = f'-profile:v main -map 0:v:0 -map_chapters 0 -map_metadata 0'
    else:
        video_opts = f'{cabac} {reframe} -profile:v main -map 0:v:0 -map_chapters 0 -map_metadata 0'

    # Metadata Watermark
    m = await db.get_metadata_w(message.from_user.id)
    if m:
        metadata = '-metadata title=Cantarellabots -metadata:s:v title=Cantarellabots -metadata:s:a title=Cantarellabots'
    else:
        metadata = ''

    # Advanced Metadata
    adv_metadata = await get_metadata_flags(message.from_user.id)

    # Copy Subtitles
    h = await db.get_hardsub(message.from_user.id)
    s = await db.get_subtitles(message.from_user.id)
    subs_i = get_codec(filepath, channel='s:0')
    if subs_i == []:
        subtitles = ''
    else:
        if s:
            if h:
                subtitles = ''
            else:
                if ex == 'MP4':
                    subtitles = '-c:s mov_text -c:t copy -map 0:t?'
                elif ex == 'AVI':
                    subtitles = ''
                else:
                    subtitles = '-c:s copy -c:t copy -map 0:t?'
        else:
            subtitles = ''


#    ffmpeg_filter = ':'.join([
#        'drawtext=fontfile=/app/bot/utils/watermark/font.ttf',
#        f"text='Cantarellabots'",
#        f'fontcolor=white',
#        'fontsize=main_h/20',
#        f'x=40:y=40'
#    ])

    # Font Selection - Locked to Roboto-Bold
    selected_font = 'Roboto-Bold'

    # Font Size override or calculation based on resolution
    user_size = await db.get_user_font_size(message.from_user.id)
    if user_size > 0:
        font_size = user_size
    elif quality == '480p':
        font_size = 30
    elif quality == '720p':
        font_size = 50
    elif quality == '1080p':
        font_size = 24
    else:
        # Check resolution setting
        r_db = await db.get_resolution(message.from_user.id)
        if r_db == '1080':
            font_size = 24
        elif r_db == '720':
            font_size = 50
        elif r_db in ['480', '576']:
            font_size = 30
        elif r_db == 'OG':
            # Analyze resolution
            _, height = get_width_height(filepath)
            if height >= 1080:
                font_size = 24
            elif height >= 720:
                font_size = 50
            else:
                font_size = 30
        else:
            font_size = 50

    # Watermark and Resolution
    r = await db.get_resolution(message.from_user.id)
    # Physical Watermark check
    user_id = message.from_user.id
    watermark_file = os.path.join(ASSETS_DIR, f'watermark_{user_id}.png')
    has_watermark = os.path.exists(watermark_file)

    vf_list = []
    if quality == '480p':
        vf_list.append('scale=854:480')
    elif quality == '720p':
        vf_list.append('scale=1280:720')
    elif quality == '1080p':
        vf_list.append('scale=1920:1080')
    elif r == 'OG':
        pass
    elif r == '1080':
        vf_list.append('scale=1920:1080')
    elif r == '720':
        vf_list.append('scale=1280:720')
    elif r == '576':
        vf_list.append('scale=768:576')
    else:
        vf_list.append('scale=852:480')

    if has_watermark:
        # We'll use filter_complex for watermark, so we don't add it to vf_list here if we use filter_complex
        # However, it's easier to chain them if we know how many inputs we have.
        pass

    # Hard Subs
    if h:
        # Ensure path is absolute and correctly escaped for FFmpeg subtitles filter
        subtitles_path = os.path.abspath(subtitles_path)
        escaped_sub_path = subtitles_path.replace(":", "\\:")
        # Ensure selected_font is used and fallback to system font if it fails (handled by FFmpeg usually, but we set it)
        vf_list.append(f"subtitles='{escaped_sub_path}':force_style='FontName={selected_font},FontSize={font_size},Outline=2,Shadow=1'")

    if vf_list:
        watermark = "-vf " + ",".join(vf_list)
    else:
        watermark = ""

    # Sample rate
    sr = await db.get_samplerate(message.from_user.id)
    if sr == '44.1K':
        sample = '-ar 44100'
    elif sr == '48K':
        sample = '-ar 48000'
    else:
        sample = ''

    # bit rate
    bit = await db.get_bitrate(message.from_user.id)

    # Video Bitrate logic for quality commands (approximate as bitrate usually refers to audio in this bot's settings)
    # The requirement says Bitrate ~800k for 480p etc.
    v_bitrate = ""
    if quality == '480p':
        v_bitrate = "-b:v 800k"
    elif quality == '720p':
        v_bitrate = "-b:v 1.5M"
    elif quality == '1080p':
        v_bitrate = "-b:v 3M"

    if bit == '400':
        bitrate = '-b:a 400k'
    elif bit == '320':
        bitrate = '-b:a 320k'
    elif bit == '256':
        bitrate = '-b:a 256k'
    elif bit == '224':
        bitrate = '-b:a 224k'
    elif bit == '192':
        bitrate = '-b:a 192k'
    elif bit == '160':
        bitrate = '-b:a 160k'
    elif bit == '128':
        bitrate = '-b:a 128k'
    else:
        bitrate = ''

    # Audio
    a = await db.get_audio(message.from_user.id)
    a_i = get_codec(filepath, channel='a:0')
    if a_i == []:
        audio_opts = ''
    else:
        if a == 'dd':
            audio_opts = f'-c:a ac3 {sample} {bitrate}'
        elif a == 'aac':
            audio_opts = f'-c:a aac {sample} {bitrate}'
        elif a == 'vorbis':
            audio_opts = f'-c:a libvorbis {sample} {bitrate}'
        elif a == 'alac':
            audio_opts = f'-c:a alac {sample} {bitrate}'
        elif a == 'opus':
            audio_opts = f'-c:a libopus -vbr on {sample} {bitrate}'
        else:
            audio_opts = '-c:a copy'

        if audio_map:
            # If audio_map is provided (e.g. [0:1, 0:2]), we use it to map audio streams.
            # We need to make sure we map all audio streams in the desired order.
            # The audio_opts above sets the codec for all audio streams.
            # We need to construct the map part.
            # Note: The previous code had `-map 0:a?` attached to audio_opts.
            # If we have specific mapping, we shouldn't use generic `-map 0:a?`.

            # The `audio_map` contains indices of audio streams in the original file.
            # e.g. [1, 2] means map 0:1 then map 0:2.

            map_opts = ""
            for idx in audio_map:
                map_opts += f" -map 0:{idx}"

            # Explicitly set the default disposition for the first audio stream in the new order
            # This ensures the first audio track in the list is the default one
            disposition_opts = " -disposition:a:0 default"

            audio_opts = f"{audio_opts} {map_opts} {disposition_opts}"
        else:
             audio_opts += " -map 0:a:0"


    # Audio Channel
    c = await db.get_channels(message.from_user.id)
    if '-c:a copy' in audio_opts:
        channels = ''
    elif c == '1.0':
        channels = '-rematrix_maxval 1.0 -ac 1'
    elif c == '2.0':
        channels = '-rematrix_maxval 1.0 -ac 2'
    elif c == '2.1':
        channels = '-rematrix_maxval 1.0 -ac 3'
    elif c == '5.1':
        channels = '-rematrix_maxval 1.0 -ac 6'
    elif c == '7.1':
        channels = '-rematrix_maxval 1.0 -ac 8'
    else:
        channels = ''

    finish = '-threads 8'

    # Thumbnail injection
    user_id = message.from_user.id
    thumb_path = os.path.abspath(os.path.join(ASSETS_DIR, f'thumb_{user_id}.jpg'))
    if not os.path.exists(thumb_path) or os.path.getsize(thumb_path) == 0:
        thumb_path = None

    # Finally
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        await message.reply("❌ FFmpeg not found on VPS. Please install it.")
        return None, "FFmpeg not found"
    print(f"DEBUG: Input: {filepath}, Output: {output_filepath}")

    # Build Input list
    # Input 0: Video
    # Input 1: Thumbnail (Optional)
    # Input 2: Watermark (Optional)
    command = ['ffmpeg', '-hide_banner', '-hwaccel', 'auto', '-y', '-copyts', '-sub_charenc', 'UTF-8', '-i', filepath]

    if thumb_path:
        command.extend(['-i', thumb_path])
    if has_watermark:
        command.extend(['-i', watermark_file])

    # Video Filter Logic
    if has_watermark:
        w_idx = 2 if thumb_path else 1
        if vf_list:
            filter_str = f"[0:v]{','.join(vf_list)}[vbase];[{w_idx}:v]colorkey=0x000000:0.1:0.1,scale=iw*0.15:-1[wm];[vbase][wm]overlay=W-w-10:10[v_out]"
        else:
            filter_str = f"[{w_idx}:v]colorkey=0x000000:0.1:0.1,scale=iw*0.15:-1[wm];[0:v][wm]overlay=W-w-10:10[v_out]"
        command.extend(['-filter_complex', filter_str])
        video_map_arg = ['-map', '[v_out]']
    elif vf_list:
        command.extend(['-vf', ",".join(vf_list)])
        video_map_arg = ['-map', '0:v:0']
    else:
        video_map_arg = ['-map', '0:v:0']

    # Remove duplicate mappings
    video_opts = video_opts.replace('-map 0:v:0', '')

    # Combine mapping
    command.extend(video_map_arg)
    command.extend(codec.split())
    command.extend(preset.split())
    command.extend(frame.split())
    command.extend(tunevideo.split())
    command.extend(aspect.split())
    command.extend(video_opts.split())
    command.extend(Crf.split())

    if v_bitrate:
        command.extend(v_bitrate.split())

    command.extend(metadata.split())
    command.extend(adv_metadata)
    command.extend(subtitles.split())
    command.extend(audio_opts.split())
    command.extend(channels.split())

    # Determine subtitle mapping based on hardsub setting
    subtitle_map = ['-map', '0:s?'] if not h else []

    if thumb_path:
        # Simplified mapping: -map 0 -map 1 -c copy -c:v:1 mjpeg -disposition:v:1 attached_pic
        command.extend(['-map', '0:a?', '-map', '0:s?'])
        command.extend(['-map', '1:v', '-c:v:1', 'mjpeg', '-disposition:v:1', 'attached_pic'])
    else:
        command.extend(['-map', '0:a?', '-map', '0:s?'])

    command.extend(finish.split())

    print(f"FFMPEG COMMAND: {' '.join(command + [output_filepath])}")

    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    # Progress Bar
    stderr_log = await handle_progress(proc, msg, message, filepath)
    # Wait for the subprocess to finish
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        e_response = stderr.decode().strip()
        LOGGER.error(f"FFmpeg failed with exit code {proc.returncode}. Error: {e_response}")
        if os.path.isfile(output_filepath):
            os.remove(output_filepath)
        return None, stderr_log

    if not os.path.isfile(output_filepath) or os.path.getsize(output_filepath) == 0:
        LOGGER.error(f"Encoding failed: {output_filepath} not created or is 0 bytes.")
        if os.path.isfile(output_filepath):
            os.remove(output_filepath)
        return None, stderr_log

    return output_filepath, stderr_log


async def hard_sub(filepath, subtitles_path, message, msg, quality=None):
    filepath = os.path.abspath(filepath)
    subtitles_path = os.path.abspath(subtitles_path)
    ex = await db.get_extensions(message.from_user.id)
    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)

    if ex == 'MP4':
        output_filepath = os.path.join(encode_dir, name + '.mp4')
    else:
        output_filepath = os.path.join(encode_dir, name + '.mkv')

    adv_metadata = await get_metadata_flags(message.from_user.id)

    # Font Selection - Locked to Roboto-Bold
    selected_font = 'Roboto-Bold'

    # Quality logic for hard_sub
    vf_list = []
    crf = '22'
    v_bitrate = []

    # Font Size override
    user_size = await db.get_user_font_size(message.from_user.id)

    # Analyze resolution for font size and scaling if quality is not provided
    if not quality:
        r_db = await db.get_resolution(message.from_user.id)
        if r_db == '1080':
            font_size = 24
        elif r_db == '720':
            font_size = 50
        elif r_db in ['480', '576']:
            font_size = 30
        else:
            _, height = get_width_height(filepath)
            if height >= 1080:
                font_size = 24
            elif height >= 720:
                font_size = 50
            else:
                font_size = 30
    else:
        if quality == '480p':
            vf_list.append('scale=854:480')
            crf = '28'
            v_bitrate = ['-b:v', '800k']
            font_size = 30
        elif quality == '720p':
            vf_list.append('scale=1280:720')
            crf = '24'
            v_bitrate = ['-b:v', '1.5M']
            font_size = 50
        elif quality == '1080p':
            vf_list.append('scale=1920:1080')
            crf = '22'
            v_bitrate = ['-b:v', '3M']
            font_size = 24
        else:
            font_size = 50

    if user_size > 0:
        font_size = user_size

    # Ensure path is absolute and correctly escaped for FFmpeg subtitles filter
    subtitles_path = os.path.abspath(subtitles_path)
    escaped_sub_path = subtitles_path.replace(":", "\\:")
    vf_list.append(f"subtitles='{escaped_sub_path}':force_style='FontName={selected_font},FontSize={font_size},Outline=2,Shadow=1'")

    # Thumbnail injection
    user_id = message.from_user.id
    thumb_path = os.path.abspath(os.path.join(ASSETS_DIR, f'thumb_{user_id}.jpg'))
    if not (os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0):
        thumb_path = None

    # Watermark check
    watermark_file = os.path.join(ASSETS_DIR, f'watermark_{user_id}.png')
    has_watermark = os.path.exists(watermark_file)

    # Hardcode subtitles - requires re-encoding video
    # Using libx264 for speed
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        await message.reply("❌ FFmpeg not found on VPS. Please install it.")
        return None, "FFmpeg not found"
    print(f"DEBUG: Input: {filepath}, Output: {output_filepath}")

    # Build Input list
    # Input 0: Video
    # Input 1: Thumbnail (Optional)
    # Input 2: Watermark (Optional)
    command = [
        'ffmpeg', '-hide_banner',
        '-hwaccel', 'auto', '-y', '-copyts',
        '-sub_charenc', 'UTF-8', '-i', filepath
    ]

    if thumb_path:
        command.extend(['-i', thumb_path])
        thumb_input_index = 1
    else:
        thumb_input_index = -1

    if has_watermark:
        command.extend(['-i', watermark_file])
        watermark_input_index = 2 if thumb_path else 1
    else:
        watermark_input_index = -1

    # Filter & Mapping
    if has_watermark:
        filter_str = f"[0:v:0]{','.join(vf_list)}[vbase];"
        filter_str += f"[{watermark_input_index}:v]colorkey=0x000000:0.1:0.1,scale=iw*0.15:-1[wm];"
        filter_str += f"[vbase][wm]overlay=W-w-10:10[v_out]"
        command.extend(['-filter_complex', filter_str, '-map', '[v_out]'])
    else:
        command.extend(['-vf', ",".join(vf_list), '-map', '0:v:0'])

    command.extend([
        '-c:v', 'libx264', '-preset', 'superfast', '-crf', crf, '-r', '24000/1001'
    ])
    command.extend(v_bitrate)
    command.extend(['-c:a', 'copy'])

    if thumb_path:
        # User requested mapping logic: -map 0 -map 1 -c:v:1 mjpeg -disposition:v:1 attached_pic
        # Input 0: Video, Input 1: Thumbnail
        command.extend(['-map', '0:a?', '-map', '1:v', '-c:v:1', 'mjpeg', '-disposition:v:1', 'attached_pic'])
    else:
        command.extend(['-map', '0:a?'])
    command.extend(adv_metadata)

    print(f"FFMPEG COMMAND (hard_sub): {' '.join(command + [output_filepath])}")

    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stderr_log = await handle_progress(proc, msg, message, filepath)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        LOGGER.error(f"FFmpeg hard_sub failed with exit code {proc.returncode}. Error: {stderr.decode().strip()}")
        return None, stderr_log

    if not os.path.isfile(output_filepath) or os.path.getsize(output_filepath) == 0:
        return None, stderr_log
    return output_filepath, stderr_log


async def soft_code(filepath, subtitles_path, message, msg, quality=None):
    filepath = os.path.abspath(filepath)
    subtitles_path = os.path.abspath(subtitles_path)
    ex = await db.get_extensions(message.from_user.id)
    path, extension = os.path.splitext(filepath)
    name = os.path.basename(path)

    # Soft coding usually works best with MKV
    output_filepath = os.path.join(encode_dir, name + '.mkv')

    adv_metadata = await get_metadata_flags(message.from_user.id)

    # Thumbnail injection
    user_id = message.from_user.id
    thumb_path = os.path.abspath(os.path.join(ASSETS_DIR, f'thumb_{user_id}.jpg'))
    if not (os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0):
        thumb_path = None

    # Watermark check
    watermark_file = os.path.join(ASSETS_DIR, f'watermark_{user_id}.png')
    has_watermark = os.path.exists(watermark_file)

    # Merge subtitle and video - no re-encoding (mostly)
    # However, if quality is set or watermark exists, we HAVE to re-encode to scale/overlay.
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        await message.reply("❌ FFmpeg not found on VPS. Please install it.")
        return None, "FFmpeg not found"
    print(f"DEBUG: Input: {filepath}, Output: {output_filepath}")

    if quality or has_watermark:
        vf_list = []
        crf = '22'
        v_bitrate = []
        if quality == '480p':
            vf_list.append("scale=854:480")
            crf = '28'
            v_bitrate = ['-b:v', '800k']
        elif quality == '720p':
            vf_list.append("scale=1280:720")
            crf = '24'
            v_bitrate = ['-b:v', '1.5M']
        elif quality == '1080p':
            vf_list.append("scale=1920:1080")
            crf = '22'
            v_bitrate = ['-b:v', '3M']

        # Inputs: 0: Video, 1: Subtitle, 2: Thumbnail (Optional), 3: Watermark (Optional)
        command = [
            'ffmpeg', '-hide_banner',
            '-y', '-copyts', '-i', filepath,
            '-fix_sub_duration', '-sub_charenc', 'UTF-8', '-i', subtitles_path
        ]

        if thumb_path:
            command.extend(['-i', thumb_path])
            thumb_input_index = 2
        else:
            thumb_input_index = -1

        if has_watermark:
            command.extend(['-i', watermark_file])
            watermark_input_index = 3 if thumb_path else 2
        else:
            watermark_input_index = -1

        if has_watermark:
            filter_str = ""
            if vf_list:
                filter_str += f"[0:v:0]{','.join(vf_list)}[vbase];"
                filter_str += f"[{watermark_input_index}:v]colorkey=0x000000:0.1:0.1,scale=iw*0.15:-1[wm];"
                filter_str += f"[vbase][wm]overlay=W-w-10:10[v_out]"
            else:
                filter_str += f"[{watermark_input_index}:v]colorkey=0x000000:0.1:0.1,scale=iw*0.15:-1[wm];"
                filter_str += f"[0:v:0][wm]overlay=W-w-10:10[v_out]"
            command.extend(['-filter_complex', filter_str, '-map', '[v_out]'])
        else:
            command.extend(['-vf', ",".join(vf_list), '-map', '0:v:0'])

        command.extend([
            '-c:v', 'libx264', '-preset', 'superfast', '-crf', crf, '-r', '24000/1001'
        ])
        command.extend(v_bitrate)
        command.extend(['-c:a', 'copy', '-c:s', 'copy'])

        if thumb_path:
            command.extend(['-map', '0:a?', '-map', '1:s', '-map', '2:v', '-c:v:1', 'mjpeg', '-disposition:v:1', 'attached_pic'])
        else:
            command.extend(['-map', '0:a?', '-map', '1:s'])
    else:
        command = [
            'ffmpeg', '-hide_banner',
            '-y', '-copyts', '-i', filepath,
            '-fix_sub_duration', '-sub_charenc', 'UTF-8', '-i', subtitles_path
        ]

        if thumb_path:
            command.extend(['-i', thumb_path])
            thumb_input_index = 2
        else:
            thumb_input_index = -1

        if thumb_path:
            command.extend([
                '-map', '0:v:0', '-map', '0:a?', '-map', '1:s', '-map', '2:v',
                '-c', 'copy', '-c:v:1', 'mjpeg', '-disposition:v:1', 'attached_pic'
            ])
        else:
            command.extend([
                '-map', '0:v:0', '-map', '0:a?', '-map', '1:s',
                '-c', 'copy'
            ])

    # If output is MP4, convert subtitle to mov_text
    if ex == 'MP4':
        output_filepath = os.path.join(encode_dir, name + '.mp4')
        command.extend(['-c:s', 'mov_text'])

    command.extend(adv_metadata)

    print(f"FFMPEG COMMAND (soft_code): {' '.join(command + [output_filepath])}")

    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stderr_log = await handle_progress(proc, msg, message, filepath)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        LOGGER.error(f"FFmpeg soft_code failed with exit code {proc.returncode}. Error: {stderr.decode().strip()}")
        return None, stderr_log

    if not os.path.isfile(output_filepath) or os.path.getsize(output_filepath) == 0:
        return None, stderr_log
    return output_filepath, stderr_log




def get_duration(filepath):
    try:
        # Try using ffprobe first
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', filepath
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        return int(float(output))
    except Exception as e:
        LOGGER.warning(f"ffprobe duration failed: {e}, falling back to hachoir")
        try:
            metadata = extractMetadata(createParser(filepath))
            if metadata and metadata.has("duration"):
                return metadata.get('duration').seconds
        except Exception as e:
            LOGGER.error(f"hachoir duration failed: {e}")
    return 0


async def is_font_available(font_name):
    try:
        # Check if the font family exists
        proc = await asyncio.create_subprocess_exec(
            'fc-list', f":family={font_name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return font_name.lower() in stdout.decode().lower()
    except Exception as e:
        LOGGER.error(f"Error checking font {font_name}: {e}")
        return False


def get_width_height(filepath):
    try:
        # Try using ffprobe first
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of',
            'csv=s=x:p=0', filepath
        ]
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        width, height = map(int, output.split('x'))
        return width, height
    except Exception as e:
        LOGGER.warning(f"ffprobe width/height failed: {e}, falling back to hachoir")
        try:
            metadata = extractMetadata(createParser(filepath))
            if metadata and metadata.has("width") and metadata.has("height"):
                return metadata.get("width"), metadata.get("height")
        except Exception as e:
            LOGGER.error(f"hachoir width/height failed: {e}")
    return (1280, 720)


async def media_info(saved_file_path):
    process = subprocess.Popen(
        [
            'ffmpeg',
            "-hide_banner",
            '-i',
            saved_file_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    stdout, stderr = process.communicate()
    output = stdout.decode().strip()
    duration = re.search(r"Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]", output)
    bitrates = re.search(r"bitrate:\s*(\d+)[\s\w*$]", output)

    if duration is not None:
        hours = int(duration.group(1))
        minutes = int(duration.group(2))
        seconds = math.floor(float(duration.group(3)))
        total_seconds = (hours * 60 * 60) + (minutes * 60) + seconds
    else:
        total_seconds = None
    if bitrates is not None:
        bitrate = bitrates.group(1)
    else:
        bitrate = None
    return total_seconds, bitrate


async def handle_progress(proc, msg, message, filepath):
    name = os.path.basename(filepath)
    COMPRESSION_START_TIME = time.time()
    total_time = get_duration(filepath)
    if not total_time:
        total_time = 1

    status_file = os.path.join(download_dir, "status.json")
    with open(status_file, 'w') as f:
        statusMsg = {
            'running': True,
            'message': msg.id,
            'user': message.from_user.id,
            'pid': proc.pid
        }
        json.dump(statusMsg, f, indent=2)

    last_update_time = 0
    stderr_buffer = ""

    while True:
        try:
            chunk = await asyncio.wait_for(proc.stderr.read(1024), timeout=1.0)
            if chunk:
                stderr_buffer += chunk.decode('utf-8', errors='replace')
                if len(stderr_buffer) > 50000:
                    stderr_buffer = stderr_buffer[-50000:]
            elif proc.returncode is not None:
                break
        except asyncio.TimeoutError:
            if proc.returncode is not None:
                break
        except Exception:
            break

        try:
            with open(status_file, 'r') as f:
                s_msg = json.load(f)
                if not s_msg.get('running', True):
                    proc.kill()
                    return stderr_buffer
        except:
            pass

        now = time.time()
        if now - last_update_time >= 3:
            times = re.findall(r"time=\s*(\d{2}:\d{2}:\d{2}(?:\.\d+)?)", stderr_buffer)
            sizes = re.findall(r"size=\s*(\d+)\s*(\w+)", stderr_buffer)

            if times and sizes:
                last_time_str = times[-1]
                t_parts = last_time_str.split(':')
                current_seconds = int(t_parts[0])*3600 + int(t_parts[1])*60 + float(t_parts[2])

                last_size_val, unit = sizes[-1]
                current_size_val = int(last_size_val)
                unit = unit.lower()
                if 'kb' in unit:
                    current_size_mb = current_size_val / 1024
                elif 'mb' in unit:
                    current_size_mb = current_size_val
                elif 'gb' in unit:
                    current_size_mb = current_size_val * 1024
                else:
                    current_size_mb = current_size_val / (1024*1024)

                percentage = min(100, (current_seconds * 100 / total_time)) if total_time > 0 else 0
                est_total_size_mb = (current_size_mb / (percentage / 100)) if percentage > 0 else 0

                elapsed = now - COMPRESSION_START_TIME
                speed_mb_s = current_size_mb / elapsed if elapsed > 0 else 0

                bar_count = int(percentage / 10)
                bar = '█' * bar_count + '░' * (10 - bar_count)

                status_text = (
                    f"‣ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐄𝐧𝐜𝐨𝐝𝐢𝐧𝐠\n"
                    f"   [{bar}] {round(percentage, 2)}%\n"
                    f"   ‣ 𝐒𝐢𝐳𝐞 : {round(current_size_mb, 2)} MB ᴏᴜᴛ ᴏғ ~ {round(est_total_size_mb, 2)} MB\n"
                    f"   ‣ 𝐒𝐩𝐞𝐞𝐝 : {round(speed_mb_s, 2)} MB/s"
                )

                try:
                    await msg.edit(
                        text=status_text,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton('ᴄᴀɴᴄᴇʟ', callback_data='cancel'),
                            InlineKeyboardButton('sᴛᴀᴛs', callback_data='stats')
                        ]])
                    )
                    last_update_time = now
                except:
                    pass

    return stderr_buffer
