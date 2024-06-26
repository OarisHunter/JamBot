# Utils.py

import math
import ast
import yt_dlp as youtube_dl
import asyncio
import random

from typing import Any, Union, List, Iterable
from nextcord import Client, Message, Member
from configparser import ConfigParser
from traceback import format_exc


class ConfigUtil:
    """
        Config Utility functions for music bot
    """

    def __init__(self):
        self.invalid_config_message = """Config file is invalid
        likely due to a missing starting guild id or an invalid invite link"""

    def get_prefix(self, client: Client, message: Message) -> str:
        """
            Get prefixes from config.ini

        :param client:      nextcord.Client object, automatically passed: Client
        :param message:     nextcord.Message object: Message
        :return:            guild prefix str from config: str
        """
        server_config = self.read_config('SERVER_SETTINGS')
        # in DM messages force default prefix
        if not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return server_config[str(message.guild.id)]['prefix']

    @staticmethod
    def read_config(field: str) -> dict:
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
            config_dict["invite_link"] = str(config_field['invite_link'])
            config_dict["doom_playlist"] = str(config_field['doom_playlist'])
            config_dict['ydl_opts'] = ast.literal_eval(config_field['ydl_opts'])
            config_dict['ffmpeg_opts'] = ast.literal_eval(config_field['ffmpeg_opts'])
            config_dict['embed_theme'] = int(config_field['embed_theme'], 0)
            config_dict['queue_display_length'] = int(config_field['queue_display_length'])
            config_dict['default_prefix'] = str(config_field['default_prefix'])
            config_dict['view_timeout'] = int(config_field['view_timeout'])
            config_dict['djRoleName'] = str(config_field['djRoleName'])
            config_dict['broken'] = config_field.getboolean('broken')
            config_dict['debug_mode'] = config_field.getboolean('debug_mode')
        elif field == 'SERVER_SETTINGS':
            for i in config_field.keys():
                temp = ast.literal_eval(config_field[i])
                config_dict[i] = {'prefix': temp['prefix'], 'loop': bool(temp['loop'])}
        else:
            print("Bad field passed to read_config")
        return config_dict

    @staticmethod
    def write_config(mode: str, field: str, key: str, value: Any = None) -> None:
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete: str
        :param field:   Config.ini field: str
        :param key:     Key for value in config: str
        :param value:   Value for key in config: Any
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

    def validate_config(self) -> bool:
        """
            Checks for a valid default guild id and invite link, set in config.ini

        :return: validity of config file : bool
        """
        guild_id_length = 18

        settings = self.read_config('BOT_SETTINGS')
        servers = self.read_config('SERVER_SETTINGS')

        # Check link
        link_checks = ['https://discord.com', 'oauth', 'client_id', 'bot', 'applications.commands', 'permissions=8']
        is_link_valid = True if False not in [check in settings['invite_link'] for check in link_checks] else False

        # Check start guild id
        is_guild_valid = True if len(str(list(servers.keys())[0])) == guild_id_length else False

        if is_link_valid and is_guild_valid:
            print("-*-*-*-*-*-*-*-* Tempo is Ready! *-*-*-*-*-*-*-*-*-*-")
            print("\tRead from config!")
        else:
            print(self.invalid_config_message)
            print("Bot running in restricted mode, please update config and restart")

        return True if is_link_valid and is_guild_valid else False


class Util:
    """
        Utility functions for music bot
    """

    def __init__(self):
        config_obj = ConfigUtil()
        self.config = config_obj.read_config('BOT_SETTINGS')
        self.ydl_opts = self.config['ydl_opts']

    @staticmethod
    def tuple_to_string(tup: tuple) -> str:
        """
            Converts an indeterminate length tuple to a string

        :return:    string
        """
        temp = ""
        for i in tup:
            temp += i + " "
        return temp.strip()

    @staticmethod
    def song_info_to_tuple(song_info: dict, author: Member) -> tuple:
        """
            Extract info from song_info into song tuple

        :param song_info:   dict from youtube_dl download: dict
        :param author:      ctx.message.author: Member
        :return:            (title: str,
                                url: str,
                                web_page: str,
                                ctx.message.author: Member,
                                duration: int,
                                thumbnail: str): tuple
        """
        title = song_info['title']
        # url = song_info['formats'][0]['url']
        url = song_info['url']
        web_page = song_info['webpage_url']
        duration = song_info['duration']
        thumbnail = song_info["thumbnails"][-1]['url']
        # print(title, url, web_page, author, duration, thumbnail)
        return title, url, web_page, author, duration, thumbnail

    def download_from_yt(self, link: str) -> Union[dict, List[dict]]:
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
                    if self.config['debug_mode']:
                        print('Util.download_from_yt | {}'.format(format_exc()))
        # print(song_info)  # Debug call to see youtube_dl output
        return song_info

    async def repopulate_queue(self, server_queue: list) -> None:
        """
            Iterates through server song queue and repopulates non-youtube sourced songs with youtube dl song info
                NOTE: In-place modification

        :param server_queue:   Server Song Queue: list
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
                if self.config['debug_mode']:
                    print('Util.repopulate_queue | {}'.format(format_exc()))

    def get_first_in_queue(self, queue: list) -> str:
        """
            Gets first song in the queue, download info if necessary

        :param queue:   Server song queue: list
        :return:        playback url of first song in queue: str
        """
        if len(queue[0]) == 2:
            song_title, message_author = queue[0]
            yt_dl = self.download_from_yt(song_title)
            queue[0] = self.song_info_to_tuple(yt_dl[0], message_author)
        return queue[0][1]

    @staticmethod
    def calculate_duration(queue: list) -> str:
        """
            Calculate duration of Song Queue

        :param queue:   Server Song Queue: list
        :return:        "???" or Queue Duration: str
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
    def scrub_song_title(title: str) -> str:
        """
            Removes invalid characters from song title strings

        :param title:   Song Title string: str
        :return:        Scrubed song title string: str
        """
        return ''.join(c for c in title if (c.isalnum() or c == ' '))

    @staticmethod
    def display_table(data: Iterable[Iterable[Any]], labels: List[Any]) -> None:
        """
            Displays a formatted table to be displayed

        :param data: the data to be displayed: List[List[Any]]
        :param labels: column labels for data, will be displayed in order given: List[Any]
        :return: None
        """
        column_widths = [max(map(len, list(map(str, col)) + [labels[i]])) + 1 for i, col in enumerate(zip(*data))]
        print(' ', '---'.join(label[:column_widths[i] - 1].rjust(column_widths[i], '-')
                              for i, label in enumerate(labels)))
        for row in data:
            print(' ', ' | '.join(str(element).rjust(column_widths[i]) for i, element in enumerate(row)))


if __name__ == '__main__':
    data = [(138622532248010752, 'House of Tots', 'oarishunter', '!', False),
     (148647867588935682, 'Chimp Central Station', 'trip7106', '~', False),
     (393178185631662121, 'TKE', 'higs369', '!', False),
     (703375435278450708, 'Moms Basement', 'theorussel', '!', False),
     (776839514643628032, "lil' Cream", 'creamiers', '~', False),
     (861611800336531456, 'Daddy’s Girls', 'dominantdaddy5219', '~', False),
     (886120224267575317, "Cream's Catgirls", 'creamiers', '~', False),
     (894627296118468649, 'Nerd Lounge', 'slamminsamwich', '~', False),
     (951664798444191798, 'Viberz', 'creamiers', '~', False),
     (1001944063664197752, 'Sea of Siege', 'daveycrasterbaby', '~', False),
     (1052106711713988639, 'Teke freaks', 'nf914', '~', False)]
    labels = ['Guild ID', 'Guild Name', 'Guild Owner', 'Prefix', 'Loop']

    Util.display_table(data, labels)
