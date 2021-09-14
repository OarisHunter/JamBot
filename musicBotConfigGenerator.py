"""
Generates config file for musicBot

@author: Pierce Thompson
"""

from configparser import ConfigParser

config_object = ConfigParser()

config_object['BOT_SETTINGS'] = {
    "prefix": "~",
    "test_song": "https://www.youtube.com/watch?v=zHtcvQAI000"
}

with open('config.ini', 'w') as conf:
    config_object.write(conf)
