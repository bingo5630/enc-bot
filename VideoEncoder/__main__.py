
import dns.resolver
from pyrogram import idle

from . import app, log

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = [
    '8.8.8.8']  # this is a google public dns


async def main():
    await app.start()
    await app.send_message(chat_id=log, text='<b>ʜᴏsᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴀʙᴇʏ ✅</b>')
    await idle()
    await app.stop()

app.loop.run_until_complete(main())
