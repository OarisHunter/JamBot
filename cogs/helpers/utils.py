# utils.py

"""

    Utility functions for music bot

"""
import ast
import os
import spotipy
import discord
import asyncio
import youtube_dl
import math

from configparser import ConfigParser
from spotipy import SpotifyClientCredentials
from sclib import SoundcloudAPI, Track, Playlist


class ConfigUtil:
    def get_prefix(self, client, message):
        """
            Get prefixes from config.ini
        """
        prefixes = self.read_config('PREFIXES')
        # in DM messages force default prefix
        if not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return prefixes[str(message.guild.id)]

    def read_config(self, field):
        """
            Get server options from config.ini

        :return:        Tuple with config values
        """

        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[field]
        return config_field

    def write_config(self, mode, field, key, value=None):
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete
        :param field:   Config.ini field
        :param key:     Key for value in config
        :param value:   Value for key in config
        :return:        NULL
        """
        config_object = ConfigParser()
        config_object.read("..config.ini")
        config_field = config_object[field]

        if mode == 'w':
            config_field[str(key)] = value
        elif mode == 'd':
            config_field.pop(str(key))
        else:
            print('invalid config write mode')

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)

class SongQueue:
    def __init__(self, bot):
        self.bot = bot
        self.util = Util()
        self.embeds = Embeds(self.bot)
        self.server_queues = {}
        self.soundcloud = SoundcloudAPI()
        self.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_CID'),
                                                                client_secret=os.getenv('SPOTIFY_SECRET')
                                                                ))
        config = ConfigUtil().read_config('BOT_SETTINGS')
        self.test_song = config['test_song']
        self.ydl_opts = ast.literal_eval(config['ydl_opts'])
        self.ffmpeg_opts = ast.literal_eval(config['ffmpeg_opts'])
        self.default_prefix = config['default_prefix']

        self.create_server_queue()

    def create_server_queue(self):
        """
            Generate song queues for all servers
                Non-Queue destructive
        """
        # Loop through guilds bot is in
        for guild in self.bot.guilds:
            # Get guild id
            g_id = str(guild.id)
            # Add guild id to queue dict
            if g_id not in self.server_queues:
                self.server_queues[g_id] = []

    def get_queue(self, guild_id):
        """
            Get Server Queue from Queue Dict
        """
        return self.server_queues[str(guild_id)]

    def add_queue(self, guild_id, song_set):
        """
            Add song to Server Queue in Queue Dict
        """
        if type(song_set) == list:
            [self.server_queues[str(guild_id)].append(i) for i in song_set]
        else:
            self.server_queues[str(guild_id)].append(song_set)

    async def add_song_to_queue(self, ctx, song_info, from_youtube=True):
        """
            Add song(s) to queue

            If a song is from youtube, its song info should added to the queue from youtube in the following format
                song = tuple:(string:title,
                              string:url,
                              string:web_page,
                              string:ctx.message.author,
                              int:duration,
                              string:thumbnail)
            If a song is from another source (Spotify, Soundcloud, etc.), the its song info should added to the queue from
            youtube in the following format
                song = "{song title} {artist}"

                The song will then be downloaded from youtube when it is played.
                NOTE: this means the song webpage/thumbnail url will not be available until then
        """
        if from_youtube:
            # If link was a playlist, loop through list of songs and add them to the queue
            if type(song_info) == list:
                song_list = [self.util.song_info_to_tuple(i, ctx) for i in song_info]
                self.add_queue(ctx.guild.id, song_list)
                if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
                    await ctx.channel.send(
                        embed=self.embeds.generate_added_queue_embed(ctx, song_list),
                        delete_after=40)
            # Otherwise add the single song to the queue, display message if song was added to the queue
            else:
                # Generate song tuple
                song = self.util.song_info_to_tuple(song_info, ctx)

                # Display added to queue if queue is not empty
                if len(self.get_queue(ctx.guild.id)) >= 1:
                    await ctx.channel.send(
                        embed=self.embeds.generate_added_queue_embed(ctx, song),
                        delete_after=40)

                # add song to queue for playback
                self.add_queue(ctx.guild.id, song)
        else:
            # Create song list, add songs to server queue, display message
            song_list = [i for i in song_info]
            self.add_queue(ctx.guild.id, song_list)
            if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
                await ctx.channel.send(
                    embed=self.embeds.generate_added_queue_embed(ctx, song_list),
                    delete_after=40)

    async def play_music_(self, ctx):
        """
            Play songs in server's queue
        """
        try:
            # Get voice client
            vc = ctx.guild.voice_client
            # Get server song queue
            song_queue = self.get_queue(ctx.guild.id)

            while song_queue:
                try:
                    if vc.is_connected() and not vc.is_playing():
                        # Replace yt searchable string in queue with yt_dl song info
                        if type(song_queue[0]) == str:
                            yt_dl = await self.download_from_yt(ctx, song_queue[0])
                            song_queue[0] = self.util.song_info_to_tuple(yt_dl[0], ctx)
                        song_url = song_queue[0][1]
                        # Create FFmpeg audio stream, attach to voice client
                        vc.play(discord.FFmpegPCMAudio(song_url, **self.ffmpeg_opts))
                        vc.source = discord.PCMVolumeTransformer(vc.source)
                        vc.volume = 1

                        # Display now playing message
                        await ctx.invoke(self.bot.get_command('np'))

                except discord.errors.ClientException:
                    print(f"ClientException: Failed to Play Song in {ctx.guild.name}")
                    break

                # Pause function while playing song, prevents rapid song switching
                while vc.is_playing():
                    await asyncio.sleep(1)

                # Move to next song in queue once song is finished
                if song_queue:
                    song_queue.pop(0)

            # Disconnect if queue is empty and bot is not playing
            await asyncio.sleep(180)
            if not song_queue and not vc.is_playing():
                await ctx.invoke(self.bot.get_command('disconnect'))

        except discord.DiscordException:
            pass

    async def spotify_to_yt_dl(self, ctx, link):
        """
            Extract songs and artists from spotify playlist
            convert to song list

            returns song info from youtube if its a track
                    list of strings if its a playlist:
                            "{song title} {song artist}"
        """
        song_info = None
        track_flag = True
        # Check for track or playlist link
        if 'playlist' in link:
            # Get playlist from playlist id
            playlist = self.spotify.playlist_items(link[link.find("playlist/") + 9:])
            # convert playlist tracks to list of youtube searchable strings
            song_info = [f"{i['track']['name']} {i['track']['album']['artists'][0]['name']}"
                         for i in playlist['tracks']['items']]
            track_flag = False

        elif 'track' in link:
            # Get track from track id
            track = self.spotify.track(link[link.find("track/") + 6:])
            # Download song info from yt and add to song info
            yt_dl = await self.download_from_yt(ctx, f"{track['name']} {track['album']['artists'][0]['name']}")
            song_info = yt_dl[0]

        else:
            pass
        return song_info, track_flag

    async def soundcloud_to_yt_dl(self, ctx, link):
        """
            Extract songs and artists from soundcloud playlist
            convert to song list

            returns song info from youtube if its a track
                    list of strings if its a playlist:
                            "{song title} {song artist}"
        """
        song_info = None
        track_flag = True
        sc_result = self.soundcloud.resolve(link)

        if type(sc_result) == Playlist:
            # Convert track details into searchable youtube string
            song_info = [f'{track.title} {track.artist}'
                         for track in sc_result]
            track_flag = False

        elif type(sc_result) == Track:
            # Get song info from youtube and add to song info list
            yt_dl = await self.download_from_yt(ctx, f'{sc_result.title} {sc_result.artist}')
            song_info = yt_dl[0]

        else:
            pass
        return song_info, track_flag

    async def download_from_yt(self, ctx, link):
        """
            Extracts info from yt link, adds song to server queue, plays song from queue.
        """
        # Call Youtube_DL to fetch song info
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            # DEBUG COMMAND, pass test song from config in place of link
            if link == "DEBUG":
                song_info = ydl.extract_info(self.test_song, download=False)
            else:
                song_info = ydl.extract_info(link, download=False)
        # print(song_info)  # Debug call to see youtube_dl output

        # Detect if link is a playlist
        try:
            if song_info['_type'] == 'playlist':
                # If link is a playlist set song_info to a list of songs
                song_info = song_info['entries']
            else:
                print(f"Link from {ctx.guild.name} is unsupported")
        except KeyError:
            pass

        return song_info

    async def extract_song_info(self, ctx, link):
        """
            Directs link to proper parse method

            Support for Apple, SoundCloud, Spotify, and YT

            returns song_info : Tuple, List, flag for if info is from youtube
        """
        song_info = None
        from_youtube = True
        if "https://music.apple.com" in link:
            await ctx.channel.send("**Apple Music support coming soon!**", delete_after=20)
        elif "https://open.spotify.com" in link:
            await ctx.channel.send("**Spotify Link!** This may take a moment...", delete_after=20)
            song_info, from_youtube = await self.spotify_to_yt_dl(ctx, link)
        elif "https://soundcloud.com" in link:
            await ctx.channel.send("**SoundCloud Link!** This may take a moment...", delete_after=20)
            song_info, from_youtube = await self.soundcloud_to_yt_dl(ctx, link)
        else:
            song_info = await self.download_from_yt(ctx, link)
        return song_info, from_youtube

class Util:
    def tuple_to_string(self, tup):
        """
            Converts an indeterminate length tuple to a string

        :return:    string
        """
        temp = ""
        for i in tup:
            temp += i + " "
        return temp.strip()

    def song_info_to_tuple(self, song_info, ctx):
        """
            Extract info from song_info into song tuple
            song = tuple:(string:title,
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
        return title, url, web_page, ctx.message.author, duration, thumbnail

class Embeds:
    def __init__(self, bot):
        self.bot = bot
        self.config = ConfigUtil()
        bot_settings = self.config.read_config('BOT_SETTINGS')
        self.invite_link = bot_settings['invite_link']
        self.embed_theme = int(bot_settings['embed_theme'], 0)
        self.queue_display_length = int(bot_settings['queue_display_length'])
        self.default_prefix = bot_settings['default_prefix']
        self.utilities = Util()

    def generate_np_embed(self, ctx, song: tuple):
        """
            Generates embed for "Now Playing" messages

            song: tuple (song_title, playback_url, webpage_url, author of request)
        """
        embed = discord.Embed(title="Now Playing", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_image(url=song[5])
        embed.add_field(name="Song: ",
                        value=f"[{song[0]}]({song[2]})\n"
                              f"Duration - {math.floor(song[4] / 60)}:{str(math.floor(song[4] % 60)).rjust(2, '0')}",
                        inline=False)
        embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
        return embed

    def generate_added_queue_embed(self, ctx, song):
        """
            Generates embed for "Added to Queue" messages

            song: tuple (song_title, playback_url, webpage_url, author of request)
        """
        embed = discord.Embed(title="Added to Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        if type(song) == tuple:
            embed.add_field(name="Song: ", value=f"[{song[0]}]({song[2]})", inline=False)
            embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
        else:
            overflow = False
            for count, i in enumerate(song):
                # Cap queued song display length
                if count == self.queue_display_length:
                    overflow = True
                    break
                # Embed link if song info is from youtube
                if type(i) == str:
                    embed.add_field(name=f"{count + 1}: ", value=f"{i}", inline=False)
                else:
                    embed.add_field(name=f"{count + 1}: ", value=f"[{i[0]}]({i[2]})", inline=False)
            if overflow:
                embed.set_footer(text=f"+{len(song) - self.queue_display_length} more")
            else:
                embed.set_footer(text=f"Requested by {song[0][3].name}", icon_url=song[0][3].avatar_url)
        return embed

    def generate_display_queue(self, ctx, queue):
        """
            Generates embed for "Queue" messages

            queue: Server song queue
        """
        embed = discord.Embed(title="Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        # Build message to display
        overflow = False
        for count, song in enumerate(queue):
            # Cap queue display length
            if count == self.queue_display_length:
                overflow = True
                break
            # Embed link if song info is from youtube
            if type(song) == str:
                embed.add_field(name=f"{count + 1}: ", value=f"{song}", inline=False)
            else:
                embed.add_field(name=f"{count + 1}: ", value=f"[{song[0]}]({song[2]})", inline=False)
        # Display overflow message
        if overflow:
            embed.set_footer(text=f"+{len(queue) - self.queue_display_length} more")

        # return embed
        return embed

    def generate_invite(self, ctx):
        """
            Generate invite embed
        """
        embed = discord.Embed(title="Invite Link", url=self.invite_link, color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        embed.add_field(name=f"Copyable link:", value=f"{self.invite_link}", inline=False)

        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.avatar_url)

        return embed

    def generate_help(self, ctx):
        """
            Generates help embed
        """
        embed = discord.Embed(title="Help", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        for i in self.bot.commands:
            if not i.name == 'help':
                embed.add_field(name=self.config.get_prefix(ctx, ctx) + i.name, value=i.help, inline=False)

        return embed

    def generate_new_server_embed(self, guild):
        """
            Generate new server embed
        """
        embed = discord.Embed(title="Thanks for adding Tempo!", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        embed.add_field(name="Getting Started!",
                        value="Use '~help' to get started.\n"
                              "You can change the prefix from '~' by using '~prefix <new prefix>",
                        inline=False)

        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬",
                        value='\u200b',
                        inline=False)

        embed.add_field(name="Bot is under constant development, Pardon the dust!",
                        value="Restarts are frequent, songs may cut out during a restart.",
                        inline=False)

        embed.set_image(url=self.bot.user.avatar_url)

        embed.set_footer(text=f"{self.bot.user.name} added to {guild.name}!", icon_url=guild.icon_url)

        return embed
