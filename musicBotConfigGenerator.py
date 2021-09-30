# musicBotConfigGenerator.py

"""
    Generates config file for musicBot

    @author: Pierce Thompson
"""

from configparser import ConfigParser

config_object = ConfigParser()

config_object['BOT_SETTINGS'] = {
    "invite_link": "https://discord.com/api/oauth2/authorize?client_id=887369663724519444&permissions=8&scope=bot",
    "test_song": "https://www.youtube.com/watch?v=zHtcvQAI000",
    "ydl_opts": "{'format': 'bestaudio/best', 'restrictfilenames': True, 'nocheckcertificate': True, 'ignoreerrors': True, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',}],}",
    "ffmpeg_opts": "{'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}",
    "embed_theme": "discord.Color.dark_gold()",
    "queue_display_length": "5",
    "default_prefix": "~"
}

config_object['PREFIXES'] = {
    "138622532248010752": '~'
}

with open('config.ini', 'w') as conf:
    config_object.write(conf)
