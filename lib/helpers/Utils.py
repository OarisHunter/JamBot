# Utils.py

import nextcord
import math
import ast
import youtube_dl
import asyncio
import spotipy
import os
import random

from sclib import SoundcloudAPI, Track, Playlist
from spotipy import SpotifyClientCredentials
from configparser import ConfigParser


class ConfigUtil:
    """
        Config Utility functions for music bot
    """

    def get_prefix(self, client, message):
        """
            Get prefixes from config.ini

        :param client:      nextcord.Client object, automatically passed
        :param message:     nextcord.Message object
        :return:            guild prefix str from config
        """
        server_config = self.read_config('SERVER_SETTINGS')
        # in DM messages force default prefix
        if not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return server_config[str(message.guild.id)]['prefix']

    @staticmethod
    def read_config(field):
        """
            Get server options from config.ini

            Convert to proper types here (default is str)

        :param field:   config.ini field to read and return values from
        :return:        Tuple with config values
        """
        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[field]

        config_dict = {}
        if field == 'BOT_SETTINGS':
            config_dict["invite_link"] = config_field['invite_link']
            config_dict["doom_playlist"] = config_field['doom_playlist']
            config_dict['ydl_opts'] = ast.literal_eval(config_field['ydl_opts'])
            config_dict['ffmpeg_opts'] = ast.literal_eval(config_field['ffmpeg_opts'])
            config_dict['embed_theme'] = int(config_field['embed_theme'], 0)
            config_dict['queue_display_length'] = int(config_field['queue_display_length'])
            config_dict['default_prefix'] = config_field['default_prefix']
            config_dict['view_timeout'] = int(config_field['view_timeout'])
            config_dict['broken'] = bool(config_field['broken'])
        elif field == 'SERVER_SETTINGS':
            for i in config_field.keys():
                temp = ast.literal_eval(config_field[i])
                config_dict[i] = {'prefix': temp['prefix'], 'loop': bool(temp['loop'])}
        else:
            print("Bad field passed to read_config")
        return config_dict

    @staticmethod
    def write_config(mode, field, key, value=None):
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete
        :param field:   Config.ini field
        :param key:     Key for value in config
        :param value:   Value for key in config
        :return:        None
        """
        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[str(field)]

        if mode == 'w':
            config_field[str(key)] = str(value)
        elif mode == 'd':
            config_field.pop(str(key))
        else:
            print('invalid config write mode')

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)


class Util:
    """
        Utility functions for music bot
    """

    def __init__(self):
        config_obj = ConfigUtil()
        config = config_obj.read_config('BOT_SETTINGS')
        self.ydl_opts = config['ydl_opts']

    @staticmethod
    def tuple_to_string(tup):
        """
            Converts an indeterminate length tuple to a string

        :return:    string
        """
        temp = ""
        for i in tup:
            temp += i + " "
        return temp.strip()

    @staticmethod
    def song_info_to_tuple(song_info, author):
        """
            Extract info from song_info into song tuple

        :param song_info:   dict from youtube_dl download
        :param author:      string:ctx.message.author
        :return:            tuple:(string:title,
                                    string:url,
                                    string:web_page,
                                    string:ctx.message.author,
                                    int:duration,
                                    string:thumbnail)
        """
        title = song_info['title']
        url = song_info["formats"][0]["url"]
        web_page = song_info['webpage_url']
        duration = song_info['duration']
        thumbnail = song_info["thumbnails"][-1]['url']
        return title, url, web_page, author, duration, thumbnail

    def download_from_yt(self, link):
        """
            Extracts info from yt link, adds song to server queue, plays song from queue.

        :param link:    link str
        :return:        song info dict
                        list of song info dicts if link is a playlist
        """
        # Call Youtube_DL to fetch song info
        song_info = None
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            while not song_info:
                song_info = ydl.extract_info(link, download=False)
                # Detect if link is a playlist
                try:
                    if song_info and song_info['_type'] == 'playlist':
                        # If link is a playlist set song_info to a list of songs
                        song_info = song_info['entries']
                except KeyError:
                    pass
        # print(song_info)  # Debug call to see youtube_dl output

        return song_info

    async def repopulate_queue(self, server_queue):
        """
            Iterates through server song queue and repopulates non-youtube sourced songs with youtube dl song info
                NOTE: In-place modification

        :param server_queue:   Server Song Queue
        :return:               None
        """

        loop = asyncio.get_event_loop()
        for i in range(len(server_queue)):
            try:
                if len(server_queue[i]) == 2:
                    old_song = server_queue[i]
                    song_info = await loop.run_in_executor(None, lambda: self.download_from_yt(old_song[0]))
                    new_song = self.song_info_to_tuple(song_info[0], old_song[1])

                    song_index = server_queue.index(old_song)
                    server_queue[song_index] = new_song
            except IndexError or ValueError:
                pass

    def get_first_in_queue(self, queue):
        """
            Gets first song in the queue, download info if necessary

        :param queue:   Server song queue
        :return:        First song in queue
        """
        if len(queue[0]) == 2:
            song_title, message_author = queue[0]
            yt_dl = self.download_from_yt(song_title)
            queue[0] = self.song_info_to_tuple(yt_dl[0], message_author)
        return queue[0][1]

    @staticmethod
    def calculate_duration(queue):
        """
            Calculate duration of Song Queue

        :param queue:   Server Song Queue
        :return:        str: "???" or Queue Duration
        """
        duration = 0
        flag = False
        for song in queue:
            if not len(song) == 2:
                duration += song[4]
            else:
                # 3min = 180, 5min = 300
                duration += random.randint(180, 260)
                flag = True

        if duration < 3660:  # 1 hour
            duration = f"{math.floor(duration / 60)}min {str(math.floor(duration % 60)).rjust(2, '0')}sec"
        else:
            duration = f"{math.floor(duration / 3600)}hr {str(math.floor((duration / 60) % 60)).rjust(2, '0')}min"
        return f'Approx. {duration.split(" ")[0]}' if flag else duration

    @staticmethod
    def scrub_song_title(title):
        """
            Removes invalid characters from song title strings

        :param title:   Song Title string
        :return:        Scrubed song title string
        """
        return ''.join(c for c in title if (c.isalnum() or c == ' '))
