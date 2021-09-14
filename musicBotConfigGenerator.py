"""
Generates config file for musicBot

@author: Pierce Thompson
"""

from configparser import ConfigParser

config_object = ConfigParser()

config_object['BOT_SETTINGS'] = {
    "prefix": "~"
}

with open('config.ini', 'w') as conf:
    config_object.write(conf)
