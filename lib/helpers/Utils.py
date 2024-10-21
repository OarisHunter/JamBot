# Utils.py

import math
import yt_dlp as youtube_dl
import asyncio
import random

from rebel import Database, PgsqlDriver
from json import load
from typing import Any, Union, List, Iterable
from nextcord import Client, Message, Member
from traceback import format_exc


class ConfigUtil:
    """
        Config Utility functions for music bot
    """

    def __init__(self):
        self.invalid_config_message = """Config file is invalid
        likely due to a missing starting guild id or an invalid invite link"""

    @staticmethod
    def db_connect():
        driver = None
        with open('app-settings.json') as f:
            json_data = load(f)
            if json_data.get('DBConnection'):
                driver = PgsqlDriver(
                    host=json_data['DBConnection']['host'],
                    port=json_data['DBConnection']['port'],
                    database=json_data['DBConnection']['database'],
                    user=json_data['DBConnection']['user'],
                    password=json_data['DBConnection']['password']
                )
        if driver is None:
            print("Failed to connect to DB")
        return Database(driver)

    def get_prefix(self, client: Client, message: Message) -> str:
        """
            Get prefixes from config.ini

        :param client:      nextcord.Client object, automatically passed: Client
        :param message:     nextcord.Message object: Message
        :return:            guild prefix str from config: str
        """
        server_config = self.read_config('SERVER_SETTINGS')
        # in DM messages force default prefix
        if message is None or not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return server_config[str(message.guild.id)]['prefix']

    @staticmethod
    def read_config(field: str) -> dict:
        """
            Collects DB information based on "field" - outdated concept from config.ini

        :param field:   config.ini field to read and return values from (valid are 'BOT_SETTINGS' & 'SERVER_SETTINGS'
        :return:        Tuple with config values
        """
        db = ConfigUtil.db_connect()
        if db is None:
            return {}

        if field == 'BOT_SETTINGS':
            return db.query_one("""
                SELECT 
                    invite_link,
                    doom_playlist,
                    ydl_opts,
                    ffmpeg_opts,
                    embed_theme,
                    queue_display_length,
                    default_prefix,
                    view_timeout,
                    dj_role_name,
                    broken,
                    debug_mode
                FROM public."primary-config"
                WHERE active = true
            """)
        elif field == 'SERVER_SETTINGS':
            q_data = db.query("""
                SELECT
                    guild_id,
                    prefix,
                    loop
                FROM public."server-settings"
            """)
            return {i['guild_id']: {
                "prefix": i['prefix'],
                "loop": i['loop']
            } for i in q_data}
        else:
            print("invalid table queried!")

        return {}

    @staticmethod
    def write_config(mode: str, field: str, key: str, value: Any = None) -> bool:
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete: str
        :param field:   Config.ini field: str
        :param key:     Key for value in config: str
        :param value:   Value for key in config: Any
        :return:        success: bool
        """
        db = ConfigUtil.db_connect()
        if db is None:
            return False

        if mode == 'w':
            db.execute("""
                INSERT INTO public."server-settings"(
                    guild_id, prefix, loop)
                VALUES (?, ?, ?);
            """, key, value.get('prefix'), value.get('loop'))
        elif mode == 'd':
            db.execute("""
                DELETE FROM public."server-settings"
                    WHERE guild_id = ?;
            """, key)
        else:
            print('invalid config write mode')
            return False
        return True

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
    data = ConfigUtil().read_config("BOT_SETTINGS")
    print(data)

    data = ConfigUtil().read_config("SERVER_SETTINGS")
    print(data)

    data = ConfigUtil().get_prefix(None, None)
    print(data)

    print(f"\nConfig is valid - {ConfigUtil().validate_config()}\n")

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
