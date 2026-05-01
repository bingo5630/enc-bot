

import datetime
import asyncio
import motor.motor_asyncio
from VideoEncoder import LOGGER


class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.col2 = self.db.status

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            extensions='MKV',
            hevc=False,
            aspect=False,
            cabac=False,
            reframe='pass',
            tune=True,
            frame='source',
            audio='aac',
            sample='source',
            bitrate='source',
            bits=False,
            channels='source',
            drive=False,
            preset='sf',
            metadata=True,
            hardsub=False,
            watermark=False,
            subtitles=True,
            resolution='OG',
            upload_as_doc=False,
            crf=22,
            resize=False,
            metadata_on=False,
            metadata_title="By: @Anime_Fury",
            metadata_author="By: @Anime_Fury",
            metadata_artist="By: @Anime_Fury",
            metadata_audio="By: @Anime_Fury",
            metadata_subtitle="By: @Anime_Fury",
            metadata_video="By: @Anime_Fury",
            user_font='Roboto-Bold',
            user_font_size=0,
            groq_api_pool=[],
            translation_engine='groq',
            deepseek_token=None
        )

    async def add_user(self, id):
        try:
            if not await self.is_user_exist(id):
                user = self.new_user(id)
                await asyncio.wait_for(self.col.insert_one(user), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in add_user: {e}")

    async def is_user_exist(self, id):
        try:
            user = await asyncio.wait_for(self.col.find_one({'id': int(id)}), timeout=5.0)
            return True if user else False
        except Exception as e:
            LOGGER.error(f"Error in is_user_exist: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await asyncio.wait_for(self.col.count_documents({}), timeout=5.0)
            return count
        except Exception as e:
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            return []

    async def delete_user(self, user_id):
        try:
            await asyncio.wait_for(self.col.delete_many({'id': int(user_id)}), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in delete_user: {e}")

    async def _get_user(self, id):
        try:
            user = await asyncio.wait_for(self.col.find_one({'id': int(id)}), timeout=5.0)
            if not user:
                await self.add_user(int(id))
                user = await asyncio.wait_for(self.col.find_one({'id': int(id)}), timeout=5.0)
            return user or self.new_user(id)
        except Exception as e:
            return self.new_user(id)

    async def get_user_data(self, id):
        return await self._get_user(id)

    # Telegram Related

    # Upload As Doc
    async def set_upload_as_doc(self, id, upload_as_doc):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'upload_as_doc': upload_as_doc}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_upload_as_doc: {e}")

    async def get_upload_as_doc(self, id):
        user = await self._get_user(id)
        return user.get('upload_as_doc', False)

    # Encoding Settings

    # Resize
    async def set_resize(self, id, resize):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'resize': resize}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_resize: {e}")

    async def get_resize(self, id):
        user = await self._get_user(id)
        return user.get('resize', 'resize')

    # Frame
    async def set_frame(self, id, frame):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'frame': frame}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_frame: {e}")

    async def get_frame(self, id):
        user = await self._get_user(id)
        return user.get('frame', 'source')

    # Convert To 720p
    async def set_resolution(self, id, resolution):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'resolution': resolution}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_resolution: {e}")

    async def get_resolution(self, id):
        user = await self._get_user(id)
        return user.get('resolution', 'OG')

    # Video Bits
    async def set_bits(self, id, bits):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'bits': bits}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_bits: {e}")

    async def get_bits(self, id):
        user = await self._get_user(id)
        return user.get('bits', False)

    # Copy Subtitles
    async def set_subtitles(self, id, subtitles):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'subtitles': subtitles}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_subtitles: {e}")

    async def get_subtitles(self, id):
        user = await self._get_user(id)
        return user.get('subtitles', False)

    # Sample rate
    async def set_samplerate(self, id, sample):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'sample': sample}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_samplerate: {e}")

    async def get_samplerate(self, id):
        user = await self._get_user(id)
        return user.get('sample', '44.1K')

    # Extensions
    async def set_extensions(self, id, extensions):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'extensions': extensions}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_extensions: {e}")

    async def get_extensions(self, id):
        user = await self._get_user(id)
        return user.get('extensions', 'MP4')

    # Bit rate
    async def set_bitrate(self, id, bitrate):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'bitrate': bitrate}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_bitrate: {e}")

    async def get_bitrate(self, id):
        user = await self._get_user(id)
        return user.get('bitrate', '128')

    # Reframe
    async def set_reframe(self, id, reframe):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'reframe': reframe}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_reframe: {e}")

    async def get_reframe(self, id):
        user = await self._get_user(id)
        return user.get('reframe', 'pass')

    # Audio Codec
    async def set_audio(self, id, audio):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'audio': audio}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_audio: {e}")

    async def get_audio(self, id):
        user = await self._get_user(id)
        return user.get('audio', 'dd')

    # Audio Channels
    async def set_channels(self, id, channels):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'channels': channels}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_channels: {e}")

    async def get_channels(self, id):
        user = await self._get_user(id)
        return user.get('channels', 'source')

    # Metadata Watermark
    async def set_metadata_w(self, id, metadata):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata': metadata}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_w: {e}")

    async def get_metadata_w(self, id):
        user = await self._get_user(id)
        return user.get('metadata', False)

    # Watermark
    async def set_watermark(self, id, watermark):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'watermark': watermark}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_watermark: {e}")

    async def get_watermark(self, id):
        user = await self._get_user(id)
        return user.get('watermark', False)

    # Preset
    async def set_preset(self, id, preset):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'preset': preset}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_preset: {e}")

    async def get_preset(self, id):
        user = await self._get_user(id)
        return user.get('preset', 'sf')

    # Hard Sub
    async def set_hardsub(self, id, hardsub):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'hardsub': hardsub}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_hardsub: {e}")

    async def get_hardsub(self, id):
        user = await self._get_user(id)
        return user.get('hardsub', False)

    # HEVC
    async def set_hevc(self, id, hevc):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'hevc': hevc}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_hevc: {e}")

    async def get_hevc(self, id):
        user = await self._get_user(id)
        return user.get('hevc', False)

    # Tune
    async def set_tune(self, id, tune):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'tune': tune}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_tune: {e}")

    async def get_tune(self, id):
        user = await self._get_user(id)
        return user.get('tune', False)

    # CABAC
    async def set_cabac(self, id, cabac):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'cabac': cabac}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_cabac: {e}")

    async def get_cabac(self, id):
        user = await self._get_user(id)
        return user.get('cabac', False)

    # Aspect ratio
    async def set_aspect(self, id, aspect):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'aspect': aspect}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_aspect: {e}")

    async def get_aspect(self, id):
        user = await self._get_user(id)
        return user.get('aspect', False)

    # Google Drive
    async def set_drive(self, id, drive):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'drive': drive}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_drive: {e}")

    async def get_drive(self, id):
        user = await self._get_user(id)
        return user.get('drive', False)

    # CRF
    async def get_crf(self, id):
        user = await self._get_user(id)
        return user.get('crf', 18)

    async def set_crf(self, id, crf):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'crf': crf}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_crf: {e}")

    # Process killed status
    async def get_killed_status(self):
        status = await self.col2.find_one({'id': 'killed'})
        if not status:
            await self.col2.insert_one({'id': 'killed', 'status': False})
            return False
        else:
            return status.get('status')

    async def set_killed_status(self, status):
        try:
            await asyncio.wait_for(self.col2.update_one({'id': 'killed'}, {'$set': {'status': status}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_killed_status: {e}")

    # Auth Chat
    async def get_chat(self):
        status = await self.col2.find_one({'id': 'auth'})
        if not status:
            await self.col2.insert_one({'id': 'auth', 'chat': '5217257368'})
            return '5217257368'
        else:
            return status.get('chat')

    async def set_chat(self, chat):
        try:
            await asyncio.wait_for(self.col2.update_one({'id': 'auth'}, {'$set': {'chat': chat}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_chat: {e}")

    # Auth Sudo
    async def get_sudo(self):
        status = await self.col2.find_one({'id': 'sudo'})
        if not status:
            await self.col2.insert_one({'id': 'sudo', 'sudo_': '5217257368'})
            return '5217257368'
        else:
            return status.get('sudo_')

    async def set_sudo(self, sudo):
        try:
            await asyncio.wait_for(self.col2.update_one({'id': 'sudo'}, {'$set': {'sudo_': sudo}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_sudo: {e}")


    # Metadata Settings
    async def set_metadata_on(self, id, metadata_on):
        try:
            # Update both metadata_on and legacy metadata field for reliability
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_on': metadata_on, 'metadata': metadata_on}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_on: {e}")

    async def get_metadata_on(self, id):
        user = await self._get_user(id)
        return user.get('metadata_on', False)

    async def set_metadata_title(self, id, metadata_title):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_title': metadata_title}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_title: {e}")

    async def get_metadata_title(self, id):
        user = await self._get_user(id)
        return user.get('metadata_title', "By: @Anime_Fury")

    async def set_metadata_author(self, id, metadata_author):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_author': metadata_author}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_author: {e}")

    async def get_metadata_author(self, id):
        user = await self._get_user(id)
        return user.get('metadata_author', "By: @Anime_Fury")

    async def set_metadata_artist(self, id, metadata_artist):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_artist': metadata_artist}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_artist: {e}")

    async def get_metadata_artist(self, id):
        user = await self._get_user(id)
        return user.get('metadata_artist', "By: @Anime_Fury")

    async def set_metadata_audio(self, id, metadata_audio):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_audio': metadata_audio}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_audio: {e}")

    async def get_metadata_audio(self, id):
        user = await self._get_user(id)
        return user.get('metadata_audio', "By: @Anime_Fury")

    async def set_metadata_subtitle(self, id, metadata_subtitle):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_subtitle': metadata_subtitle}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_subtitle: {e}")

    async def get_metadata_subtitle(self, id):
        user = await self._get_user(id)
        return user.get('metadata_subtitle', "By: @Anime_Fury")

    async def set_metadata_video(self, id, metadata_video):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'metadata_video': metadata_video}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_metadata_video: {e}")

    async def get_metadata_video(self, id):
        user = await self._get_user(id)
        return user.get('metadata_video', "By: @Anime_Fury")

    async def set_user_font(self, id, font):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'user_font': font}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_user_font: {e}")

    async def get_user_font(self, id):
        user = await self._get_user(id)
        return user.get('user_font', 'Arial')

    async def set_user_font_size(self, id, size):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'user_font_size': size}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_user_font_size: {e}")

    async def get_user_font_size(self, id):
        user = await self._get_user(id)
        return user.get('user_font_size', 0)

    async def add_groq_api_key(self, id, key):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$addToSet': {'groq_api_pool': key}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in add_groq_api_key: {e}")

    async def get_groq_api_pool(self, id):
        user = await self._get_user(id)
        return user.get('groq_api_pool', [])

    async def clear_groq_api_pool(self, id):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'groq_api_pool': []}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in clear_groq_api_pool: {e}")

    async def set_translation_engine(self, id, engine):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'translation_engine': engine}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_translation_engine: {e}")

    async def get_translation_engine(self, id):
        user = await self._get_user(id)
        return user.get('translation_engine', 'groq')

    async def set_deepseek_token(self, id, token):
        try:
            await asyncio.wait_for(self.col.update_one({'id': id}, {'$set': {'deepseek_token': token}}, upsert=True), timeout=5.0)
        except Exception as e:
            LOGGER.error(f"Error in set_deepseek_token: {e}")

    async def get_deepseek_token(self, id):
        user = await self._get_user(id)
        return user.get('deepseek_token', None)
