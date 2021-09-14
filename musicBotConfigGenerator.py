"""
Generates config file for musicBot

@author: Pierce Thompson
"""

from configparser import ConfigParser

config_object = ConfigParser()

config_object['BOT_SETTINGS'] = {
    "prefix": "~",
    "test_song": "https://www.youtube.com/watch?v=zHtcvQAI000",
    "ydl_opts": "{'format': 'bestaudio/best', 'restrictfilenames': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',}],}",
    "ffmpeg_opts": "{'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}"
}

with open('config.ini', 'w') as conf:
    config_object.write(conf)
