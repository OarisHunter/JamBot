# SongQueue.py

import nextcord
import asyncio

from lib.helpers.Utils import Util, ConfigUtil
from lib.helpers.Embeds import Embeds
from lib.helpers.SpotifyParser import SpotifyParser
from lib.helpers.SoundCloudParser import SoundcloudParser


class SongQueue:
    """
        Song Queue class for discord music bot

        Handles control functions of server song queues
    """

    def __init__(self, bot):
        self.bot = bot
        self.utilities = Util()
        self.embeds = Embeds(self.bot)
        self.server_queues = {}

        # Get config values
        self.config_obj = ConfigUtil()
        config = self.config_obj.read_config('BOT_SETTINGS')
        self.ffmpeg_opts = config['ffmpeg_opts']
        self.default_prefix = config['default_prefix']

        # Call create server queue on creation to populate object with queues for previously connected servers
        self.create_server_queue()

    def create_server_queue(self):
        """
            Generate song queues for all servers
                Non-Queue destructive

        :return:    None
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

        :param guild_id:    guild id int
        :return:            Guild song queue list
        """
        return self.server_queues[str(guild_id)]

    def clear_queue(self, guild_id):
        """
            Clear Guilds song queue

        :param guild_id:    Discord Guild ID
        :return:            None
        """
        self.server_queues[str(guild_id)].clear()

    def add_queue(self, guild_id, song_set, queue_position=None):
        """
            Helper function
            Add song to Server Queue in Queue Dict

        :param guild_id:    guild id int
        :param song_set:    song tuple / list of song tuples
        :return:            None
        """
        if not queue_position:
            # normally, we add the song to the end of the queue
            if type(song_set) == list:
                [self.server_queues[str(guild_id)].append(i) for i in song_set]
            else:
                self.server_queues[str(guild_id)].append(song_set)
        else:
            # we can also insert the song in the queue
            if type(song_set) == list:
                self.server_queues[str(guild_id)][1:1] = song_set
            else:
                self.server_queues[str(guild_id)].insert(1, song_set)

    async def add_song_to_queue(self, ctx, song_info, from_youtube=True, queue_position=None):
        """
            Add song(s) to queue

            If a song is from youtube, its song info should added to the queue from youtube in the following format
                song = tuple:(string:title,
                              string:url,
                              string:web_page,
                              string:ctx.message.author,
                              int:duration,
                              string:thumbnail)
            If a song is from another source (Spotify, Soundcloud, etc.), the its song info
            should added to the queue from youtube in the following format:
                song = "{song title} {artist}"

                The song will then be downloaded from youtube when it is played.
                NOTE: this means the song webpage/thumbnail url will not be available until then

        :param ctx:             Command Context
        :param song_info:       song info dict from youtube dl AND youtube link
                                if link is a playlist AND youtube link
                                    list of song info dicts from youtube dl
                                if link is from a NON-youtube source
                                    list of str: [f"{song title} {artist}", ...]
        :param from_youtube:    if link was a youtube link
        :return:                None
        """
        if from_youtube:
            # If link was a playlist, loop through list of songs and add them to the queue
            if type(song_info) == list:
                song_list = [self.utilities.song_info_to_tuple(i, ctx.message.author) for i in song_info]
                self.add_queue(ctx.guild.id, song_list, queue_position)
                if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
                    await ctx.channel.send(
                        embed=self.embeds.generate_added_queue_embed(ctx, song_list),
                        delete_after=40)
            # Otherwise add the single song to the queue, display message if song was added to the queue
            else:
                # Generate song tuple
                song = self.utilities.song_info_to_tuple(song_info, ctx.message.author)

                # Display added to queue if queue is not empty
                if len(self.get_queue(ctx.guild.id)) >= 1:
                    await ctx.channel.send(
                        embed=self.embeds.generate_added_queue_embed(ctx, song),
                        delete_after=40)

                # add song to queue for playback
                self.add_queue(ctx.guild.id, song, queue_position)
        else:
            # Create song list, add songs to server queue, display message
            song_list = [i for i in song_info]
            self.add_queue(ctx.guild.id, song_list, queue_position)
            if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
                await ctx.channel.send(
                    embed=self.embeds.generate_added_queue_embed(ctx, song_list),
                    delete_after=40)

    async def play_music_(self, ctx):
        """
            Play songs in server's queue

        :param ctx:     Command Context
        :return:        None
        """
        try:
            # Get voice client
            vc = ctx.guild.voice_client
            # Get server song queue
            song_queue = self.get_queue(ctx.guild.id)

            while song_queue:
                try:
                    if vc.is_connected() and not vc.is_playing():
                        song_url = self.utilities.get_first_in_queue(song_queue)
                        # Create FFmpeg audio stream, attach to voice client
                        vc.play(nextcord.FFmpegPCMAudio(song_url, **self.ffmpeg_opts))
                        vc.source = nextcord.PCMVolumeTransformer(vc.source)
                        vc.volume = 1

                        # Display now playing message
                        await ctx.invoke(self.bot.get_command('np'))

                except nextcord.errors.ClientException:
                    print(f"ClientException: Failed to Play Song in {ctx.guild.name}")
                    break

                # Pause function while playing song, prevents rapid song switching
                while vc.is_playing():
                    await asyncio.sleep(1)

                server_settings = self.config_obj.read_config("SERVER_SETTINGS")
                # Move to next song in queue once song is finished if loop is disabled
                if song_queue and not server_settings[str(ctx.guild.id)]['loop']:
                    del song_queue[0]
                # Move current song to the end of queue if loop is enabled
                elif song_queue and server_settings[str(ctx.guild.id)]['loop']:
                    song_temp = song_queue[0]
                    song_queue.append(song_temp)
                    del song_queue[0]

            # if queue is empty and bot is not playing, timeout bot
            await asyncio.sleep(180)
            if not song_queue and not vc.is_playing():
                # Disconnect bot
                await ctx.invoke(self.bot.get_command('disconnect'))
                # Make sure queue is cleared
                self.clear_queue(ctx.guild.id)
                # Turn off song loop in guild settings
                server_settings = self.config_obj.read_config("SERVER_SETTINGS")
                server = server_settings[str(ctx.guild.id)]
                server['loop'] = False
                self.config_obj.write_config('w', 'SERVER_SETTINGS', str(ctx.guild.id), server)

        except nextcord.DiscordException:
            pass

    @staticmethod
    async def spotify_to_yt_dl(ctx, link):
        """
            Extract songs and artists from spotify playlist
            convert to song list

        :param ctx:     Command Context
        :param link:    link str
        :return:        song info from youtube if its a track
                        list of tuples if its a playlist:
                            tuple(str : "{song title} {song artist}", str : ctx.message.author)

        """
        parser = SpotifyParser(ctx.message.author)
        song_info, is_track = parser.parse_link(link)
        return song_info, is_track

    @staticmethod
    async def soundcloud_to_yt_dl(ctx, link):
        """
            Extract songs and artists from soundcloud playlist
            convert to song list

        :param ctx:     Command Context
        :param link:    link str
        :return:        song info from youtube if its a track
                        list of tuples if its a playlist:
                            tuple(str : "{song title} {song artist}", str : ctx.message.author)
        """
        parser = SoundcloudParser(ctx.message.author)
        song_info, track_flag = parser.parse_link(link)
        return song_info, track_flag

    async def extract_song_info(self, ctx, link):
        """
            Directs link to proper parse method

            Support for Apple, SoundCloud, Spotify, and YT

        :param ctx:     Command Context
        :param link:    link str
        :return:        tuple, list, flag for if info is from youtube
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
            song_info = self.utilities.download_from_yt(link)
        return song_info, from_youtube
