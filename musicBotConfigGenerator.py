# musicBotConfigGenerator.py

"""
    Generates config file for musicBot

    @author: Pierce Thompson
"""

from configparser import ConfigParser

config_object = ConfigParser()

config_object['BOT_SETTINGS'] = {
    "invite_link": "https://discord.com/api/oauth2/authorize?client_id=887369663724519444&permissions=8&scope=bot",
    "doom_playlist": "https://www.youtube.com/playlist?list=PLg8__X57j6ugI1FOZbBvO-T3gBIwRS7GX",
    "ydl_opts": "{'format': 'bestaudio/best', 'restrictfilenames': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'cookiefile': 'cookies.txt', 'default_search': 'auto', 'source_address': '0.0.0.0', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',}],}",
    "ffmpeg_opts": "{'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}",
    "embed_theme": "0xc27c0e",
    "queue_display_length": 5,
    "default_prefix": "~",
    "view_timeout": 60,
    "broken": False
}

config_object['PREFIXES'] = {
    "138622532248010752": {'prefix': '!', 'loop': False}
}

if __name__ == '__main__':
    with open('config.ini', 'w') as conf:
        config_object.write(conf)
