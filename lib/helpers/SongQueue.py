# SongQueue.py

import os
import spotipy
import nextcord
import asyncio

from spotipy import SpotifyClientCredentials
from sclib import SoundcloudAPI, Track, Playlist
from lib.helpers.Utils import Util, Embeds, ConfigUtil


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

        # Create API objects
        self.soundcloud = SoundcloudAPI()
        self.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_CID'),
                                                                client_secret=os.getenv('SPOTIFY_SECRET')
                                                                )
        )

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

    def add_queue(self, guild_id, song_set):
        """
            Helper function
            Add song to Server Queue in Queue Dict

        :param guild_id:    guild id int
        :param song_set:    song tuple / list of song tuples
        :return:            None
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
                self.add_queue(ctx.guild.id, song_list)
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

            # Disconnect if queue is empty and bot is not playing
            await asyncio.sleep(180)
            if not song_queue and not vc.is_playing():
                await ctx.invoke(self.bot.get_command('disconnect'))

        except nextcord.DiscordException:
            pass

    async def spotify_to_yt_dl(self, ctx, link):
        """
            Extract songs and artists from spotify playlist
            convert to song list

        :param ctx:     Command Context
        :param link:    link str
        :return:        song info from youtube if its a track
                        list of tuples if its a playlist:
                            tuple(str : "{song title} {song artist}", str : ctx.message.author)

        """
        song_info = None
        track_flag = True
        # Check for track or playlist link
        if 'playlist' in link:
            # Get playlist from playlist id
            playlist = self.spotify.playlist_items(link[link.find("playlist/") + 9:])
            # convert playlist tracks to list of youtube searchable strings
            song_info = [(f"{i['track']['name']} {i['track']['album']['artists'][0]['name']}", ctx.message.author)
                         for i in playlist['tracks']['items']]
            track_flag = False

        elif 'album' in link:
            # Get album from album id
            album = self.spotify.album(link[link.find("album/") + 6:])
            # convert album tracks to list of youtube searchable strings
            song_info = [(f"{i['name']} {i['artists'][0]['name']}", ctx.message.author)
                         for i in album['tracks']['items']]
            track_flag = False

        elif 'track' in link:
            # Get track from track id
            track = self.spotify.track(link[link.find("track/") + 6:])
            # Download song info from yt and add to song info
            yt_dl = self.utilities.download_from_yt(f"{track['name']} {track['album']['artists'][0]['name']}")
            song_info = yt_dl[0]

        else:
            pass
        return song_info, track_flag

    async def soundcloud_to_yt_dl(self, ctx, link):
        """
            Extract songs and artists from soundcloud playlist
            convert to song list

        :param ctx:     Command Context
        :param link:    link str
        :return:        song info from youtube if its a track
                        list of tuples if its a playlist:
                            tuple(str : "{song title} {song artist}", str : ctx.message.author)
        """
        song_info = None
        track_flag = True
        sc_result = self.soundcloud.resolve(link)

        if type(sc_result) == Playlist:
            # Convert track details into searchable youtube string
            song_info = [(f'{track.title} {track.artist}', ctx.message.author)
                         for track in sc_result]
            track_flag = False

        elif type(sc_result) == Track:
            # Get song info from youtube and add to song info list
            yt_dl = self.utilities.download_from_yt(f'{sc_result.title} {sc_result.artist}')
            song_info = yt_dl[0]

        else:
            pass
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
