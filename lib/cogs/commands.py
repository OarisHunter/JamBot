# commands.py
import traceback
import nextcord
import random

from datetime import datetime
from typing import Tuple, Any
from nextcord import VoiceProtocol
from nextcord.ext import commands
from nextcord.ext.commands import Context, Bot
from lib.helpers.Utils import Util, ConfigUtil
from lib.helpers.Embeds import Embeds
from lib.helpers.SpotifyParser import SpotifyParser
from lib.helpers.SongQueue import SongQueue
from lib.helpers.SongSearch import SongSearch
from lib.ui import views
from lib.helpers.LyricsParser import LyricsParser
from traceback import format_exc

# Outside of class to allow config defined role names to be read by decorators
config_obj = ConfigUtil()
config = config_obj.read_config('BOT_SETTINGS')

class Commands(commands.Cog):
    """
        nextcord Cog for command handling
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.queues = SongQueue(bot)
        self.utilities = Util()
        self.embeds = Embeds(bot)

        # Get config values
        self.doom_playlist = config['doom_playlist']
        self.ydl_opts = config['ydl_opts']
        self.ffmpeg_opts = config['ffmpeg_opts']
        self.default_prefix = config['default_prefix']
        self.queue_display_length = config['queue_display_length']
        self.view_timeout = config['view_timeout']
        self.dj_role_name = config['dj_role_name']
        self.broken = config['broken']

    @commands.command(name='play',
                      help='Connects Bot to Voice',
                      aliases=['p'],
                      usage="<youtube/spotify/soundcloud song/playlist url, or keywords to search youtube>")
    @commands.has_role(config['dj_role_name'])
    async def play_(self, ctx: Context, *, link: str, song_info: Tuple[Any] = None, queue_position: int = None):
        """
            Command to connect to voice
                plays song
                    from yt link
                    from yt search
                    from yt playlist link
                    from mix search

        :param ctx:             Command context: Context
        :param link:            Given link: str
        :param song_info:       Bypass song search if song info is already available: Tuple
        :param queue_position:  Position to place song in queue: int
        :return:                None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.play | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            # Pass link to parser to determine origin
            if not song_info:
                song_info, from_youtube = await self.queues.extract_song_info(ctx, link)
            else:
                from_youtube = False

            # Check that author is in a voice channel
            if ctx.author.voice is not None:
                try:
                    # Connect to channel of author
                    vc = await ctx.author.voice.channel.connect()
                except nextcord.ClientException:
                    # Catch error if already connected
                    vc = ctx.guild.voice_client
            else:
                print(f"Play: Bot not connected to {ctx.guild.name}")
                return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

            if song_info:
                # Add song(s) to queue from song info
                await self.queues.add_song_to_queue(ctx,
                                                    song_info,
                                                    from_youtube=from_youtube,
                                                    queue_position=queue_position)

                # Play song if not playing a song
                if not vc.is_playing():
                    await self.queues.play_music_(ctx)

    @commands.command(name='playnext',
                      help="Inserts song into queue to be played next",
                      aliases=['insert'],
                      usage="<youtube/spotify/soundcloud song/playlist url, or keywords to search youtube>")
    @commands.has_role(config['dj_role_name'])
    async def play_next_(self, ctx: Context, *, link: str):
        """
            Calls play with a parameter to insert the song into the front of the queue

        :param ctx:     Discord message context: Context
        :param link:    Given link: str
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.play_next | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            await ctx.invoke(self.bot.get_command('play'), link=link, queue_position=1)

    @commands.command(name='skip',
                      help='Skips to next Song in Queue, will remove song from queue in loop mode',
                      aliases=['s'],
                      usage="[number of songs to skip]")
    @commands.has_role(config['dj_role_name'])
    async def skip_(self, ctx, num: int = 1):
        """
            Command to skip currently playing song

        :param ctx:     Command Context
        :param num:     number of songs to skip
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.skip | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            vc = ctx.guild.voice_client  # Get current voice client

            if vc is None:
                print(f"Skip: Bot not connected to {ctx.guild.name}")
                return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

            # Check that there is another song in the queue and the bot is currently playing
            song_queue = self.queues.get_queue(ctx.guild.id)
            if len(song_queue) > 1 and vc.is_playing():

                # Pop currently playing off queue
                if len(song_queue) >= num:
                    del song_queue[0:num]
                else:
                    del song_queue[0]

                # Update Voice Client source
                # Replace yt searchable string in queue with yt_dl song info
                song_url = self.utilities.get_first_in_queue(song_queue)
                # Create FFmpeg audio stream, attach to voice client
                vc.source = nextcord.FFmpegPCMAudio(song_url, **self.ffmpeg_opts)
                vc.source = nextcord.PCMVolumeTransformer(vc.source)
                vc.volume = 1

                await ctx.channel.send("**Skipped a Song!**", delete_after=10)
                await ctx.invoke(self.bot.get_command('np'))
            else:
                vc.stop()
                await ctx.channel.send("**Skipped a Song!**", delete_after=10)

    @commands.command(name='clear',
                      help='Clears the Song Queue',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def clear_(self, ctx: Context):
        """
            Command to clear server's Queue

        :param ctx:     Command context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.clear | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            # Empty the queue
            self.queues.clear_queue(ctx.guild.id)

            # Send response
            await ctx.channel.send("**Cleared the Queue!**", delete_after=20)

    @commands.command(name='queue',
                      help='Displays the Queue',
                      usage='')
    async def queue_(self, ctx: Context):
        """
            Command to display songs in server's Queue

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.queue | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            song_queue = self.queues.get_queue(ctx.guild.id)
            if song_queue:
                view = views.QueueView(self.bot, ctx, song_queue, self.view_timeout)
                await view.create_message()
                await view.wait()
            else:
                await ctx.channel.send('**Queue is empty!**', delete_after=10)

    @commands.command(name='np',
                      help='Displays the currently playing song',
                      usage='')
    async def now_playing_(self, ctx: Context):
        """
            Command to display "Now Playing" message

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.now_playing | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            vc = ctx.message.guild.voice_client
            song_queue = self.queues.get_queue(ctx.guild.id)
            if vc and vc.is_playing():
                now = datetime.now().strftime('%m/%d/%Y, %H:%M')
                print(f"({now}) --Now Playing-- \"{song_queue[0][0]}\" in guild: {ctx.guild.name}")
                await ctx.channel.send(embed=self.embeds.generate_np_embed(ctx, song_queue[0]))
            else:
                print(f'NowPlaying: Not in a Voice Channel in {ctx.guild.name}')
                await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    @commands.command(name='pause',
                      help='Pauses currently playing song',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def pause_(self, ctx: Context):
        """
            Pauses music to be resumed later

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.pause | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            vc = ctx.voice_client

            if type(vc) == VoiceProtocol:
                if vc.is_connected() and vc.is_playing():
                    vc.pause()
                    await ctx.channel.send(f'**Music Paused!**', delete_after=10)
                elif vc.is_connected() and vc.is_paused():
                    await ctx.channel.send(f'Already Paused', delete_after=10)
                elif vc.is_connected() and not vc.is_playing():
                    await ctx.channel.send(f'Not Playing Anything', delete_after=10)
            else:
                await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    @commands.command(name='resume',
                      help='Resumes currently playing song',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def resume_(self, ctx: Context):
        """
            Resumes paused music

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.resume | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            vc = ctx.guild.voice_client

            if type(vc) == VoiceProtocol:
                if vc.is_connected() and vc.is_paused():
                    vc.resume()
                    await ctx.channel.send(f'**Music Resumed!**', delete_after=10)
                elif vc.is_connected() and vc.is_playing():
                    await ctx.channel.send(f'Already Playing', delete_after=10)
                elif vc.is_connected() and not vc.is_paused():
                    await ctx.channel.send(f'Not Playing Anything', delete_after=10)
            else:
                await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    @commands.command(name='disconnect',
                      help='Disconnects from Voice',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def disconnect_(self, ctx: Context):
        """
            Command to disconnect bot from voice

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.disconnect | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            vc = ctx.guild.voice_client

            # Check that the bot is connected to voice
            if vc and vc.is_connected():
                await vc.disconnect(force=False)

            # Clear song queue
            self.queues.clear_queue(ctx.guild.id)

            # Turn off song loop in guild settings
            server_settings = config_obj.read_config("SERVER_SETTINGS")
            server = server_settings[str(ctx.guild.id)]
            server['loop'] = False
            config_obj.write_config('w', 'SERVER_SETTINGS', str(ctx.guild.id), server)

    @commands.command(name='prefix',
                      help='Displays or changes prefix for this server',
                      usage="[new prefix]")
    @commands.has_permissions(administrator=True)
    async def prefix_(self, ctx: Context, *prefix: Tuple[str]):
        """
            Command to change/display server defined prefix, maintain loop setting

        :param ctx:     Command Context: Context
        :param prefix:  User entered prefix: Tuple[str]
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.prefix | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            prefix = self.utilities.tuple_to_string(prefix)

            # If a prefix was given, change the prefix, otherwise display the current prefix
            if prefix and len(prefix) < 2:
                # Update config file
                settings = config_obj.read_config('SERVER_SETTINGS')[str(ctx.guild.id)]
                settings['prefix'] = str(''.join(prefix))
                config_obj.write_config('w', 'SERVER_SETTINGS', str(ctx.guild.id), settings)

                await ctx.channel.send(f"Prefix for {ctx.guild.name} has been changed to: "
                                       f"{config_obj.read_config('SERVER_SETTINGS')[str(ctx.guild.id)]['prefix']}",
                                       delete_after=10)
            else:
                await ctx.channel.send(f"Prefix for {ctx.guild.name} is: "
                                       f"{config_obj.read_config('SERVER_SETTINGS')[str(ctx.guild.id)]['prefix']}",
                                       delete_after=10)

    @commands.command(name='invite',
                      help='Shows invite link to add bot to your server',
                      usage='')
    async def invite_(self, ctx: Context):
        """
            Sends an embed with invite links to add bot to other servers.

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.invite | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            await ctx.channel.send(embed=self.embeds.generate_invite(ctx))

    @commands.command(name='search',
                      help=f'Searches with given keywords, displays top results',
                      usage="<keywords to search>")
    @commands.has_role(config['dj_role_name'])
    async def search(self, ctx: Context, *, keywords: str):
        """
            Searches Youtube for given keywords, displays the top 'x' results, allows user to select from list with
            button UI

            https://open.spotify.com/playlist/19SBkYmRd5KzPGKnE5djJ6?si=423e5a9f2dbc462c

        :param ctx:         Discord message context: Context
        :param keywords:    User entered string: str
        :return:            None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.search | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            search = SongSearch()
            view = views.SearchView()

            results = search.search_yt(keywords)

            message = await ctx.channel.send(embed=self.embeds.generate_search_embed(ctx, results),
                                             view=view)

            is_timeout = await view.wait()
            await message.delete()

            if not is_timeout:
                selected_song = results[view.value]
                await ctx.invoke(self.bot.get_command('play'), link=selected_song[1])

    @commands.command(name='shuffle',
                      help='Shuffles the queue',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def shuffle_(self, ctx: Context):
        """
            Shuffles the server song queue

        :param ctx:     Discord message context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.shuffle | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            song_queue = self.queues.get_queue(ctx.guild.id)
            if len(song_queue) > 1:
                # store current song
                temp_song = song_queue[0]
                del song_queue[0]

                random.shuffle(song_queue)
                song_queue.insert(0, temp_song)  # add current song back into queue

                await ctx.channel.send(f"**Shuffled the Queue!**", delete_after=10)
                await ctx.invoke(self.bot.get_command('queue'))
            else:
                await ctx.channel.send(f'Nothing in the Queue!', delete_after=10)

    @commands.command(name='remove',
                      help='Removes a specific song from the queue',
                      usage='<number of song in queue>')
    @commands.has_role(config['dj_role_name'])
    async def remove_song_(self, ctx: Context, num: int):
        """
            Removes a specific song from the queue

        :param ctx:     Discord message context: Context
        :param num:     Song index of song to delete from the queue, starts at 1: int
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.remove_song | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            song_queue = self.queues.get_queue(ctx.guild.id)
            if len(song_queue) > num - 1:
                pending_song = song_queue[num - 1]
                view = views.ConfirmView(self.view_timeout)
                message = await ctx.channel.send(embed=self.embeds.generate_remove_embed(ctx, pending_song),
                                                 view=view)
                is_timeout = await view.wait()
                if not is_timeout:
                    if view.value:
                        song_queue.pop(num - 1)
                        await ctx.channel.send("**Song Deleted!**", delete_after=10)

                    else:
                        await ctx.channel.send("**Canceled!**", delete_after=10)
                await message.delete()
                await ctx.invoke(self.bot.get_command('queue'))

    @commands.command(name='loop',
                      help='Toggles loop mode for the song queue',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def loop_(self, ctx: Context):
        """
            Toggles the loop function of the song queue,
            preventing songs from being removed from the queue

        :param ctx:     Discord Message context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.loop | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            server_settings = config_obj.read_config("SERVER_SETTINGS")
            server = server_settings[str(ctx.guild.id)]

            # Toggle server loop setting
            if server['loop']:
                server['loop'] = False

            elif not server['loop']:
                server['loop'] = True

            await ctx.channel.send(embed=self.embeds.generate_loop_embed(ctx, server['loop']), delete_after=10)
            config_obj.write_config('w', 'SERVER_SETTINGS', str(ctx.guild.id), server)

    @commands.command(name='mix',
                      help='Searches for an artist and queues their songs',
                      usage='<artist name>')
    @commands.has_role(config['dj_role_name'])
    async def mix_(self, ctx: Context, *, artist_name: str):
        """
            Builds a playlist from all available songs by an artist from spotify

        :param ctx:             Discord message context: Context
        :param artist_name:     User input of spotify artist: str
        :return:                None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.mix | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            search = SpotifyParser(ctx.message.author)

            view = views.SearchView()
            artists = search.artist_search(artist_name)
            message = await ctx.channel.send(embed=self.embeds.generate_mix_embed(ctx, artists),
                                             view=view)
            is_timeout = await view.wait()
            await message.delete()

            if not is_timeout:
                _, artist_uri = artists[view.value]
                song_info = search.get_artist_all_tracks(artist_uri)
                await ctx.invoke(self.bot.get_command('play'), link="", song_info=song_info)

    @commands.command(name='doom',
                      help='Rip and Tear, until it is done...',
                      usage='')
    @commands.has_role(config['dj_role_name'])
    async def doom_(self, ctx: Context):
        """
            Loops music from the DOOM game indefinitely

        :param ctx:     Discord message context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.doom | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            await ctx.channel.send(embed=self.embeds.doom_embed(ctx), delete_after=20)

            # Pass link to parser to determine origin
            link = self.doom_playlist
            song_info, from_youtube = await self.queues.extract_song_info(ctx, link)

            # Check that author is in a voice channel
            if ctx.author.voice is not None:
                try:
                    # Connect to channel of author
                    vc = await ctx.author.voice.channel.connect()
                except nextcord.DiscordException:
                    # Catch error if already connected
                    vc = ctx.guild.voice_client
            else:
                print(f"Play: Bot not connected to {ctx.guild.name}")
                return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

            if song_info:
                # Add song(s) to queue from song info
                await self.queues.add_song_to_queue(ctx, song_info, from_youtube=from_youtube)

                # Shuffle queue
                song_queue = self.queues.get_queue(ctx.guild.id)
                if len(song_queue) > 1:
                    random.shuffle(song_queue)

                # Toggle server loop setting
                server_settings = config_obj.read_config("SERVER_SETTINGS")
                server = server_settings[str(ctx.guild.id)]
                server['loop'] = True
                config_obj.write_config('w', 'SERVER_SETTINGS', str(ctx.guild.id), server)

                # Play song if not playing a song
                if not vc.is_playing():
                    await self.queues.play_music_(ctx)

    @commands.command(name='lyrics',
                      help="Finds the lyrics for a song",
                      usage="<song title>, <artist name>    NOTE: comma is required!")
    async def lyrics_(self, ctx: Context, *, arg):
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.lyrics | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            # split args into title and artist
            title = arg.split(',')[0].strip()
            artist = arg.split(',')[1].strip()

            parser = LyricsParser()
            lyrics = parser.get_lyrics_list(title, artist)

            view = views.LyricsView(self.bot, ctx, lyrics, title, artist, self.view_timeout)
            await view.create_message()
            await view.wait()

    @commands.command(name='help')
    async def help_(self, ctx: Context):
        """
            Custom help command

        :param ctx:     Command Context: Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            if config['debug_mode']:
                print('Commands.help | {}'.format(format_exc()))
        else:
            # Skip command if bot is broken
            if self.broken:
                await self.broken_(ctx)
                return

            view = views.HelpView(self.bot, ctx, self.view_timeout)
            await view.create_message()
            await view.wait()

    async def broken_(self, ctx):
        await ctx.channel.send(embed=self.embeds.broken_embed(), delete_after=30)

    @play_.error
    async def play_handler(self, ctx: Context, error: Exception):
        """
            Local error handler for play command

        :param ctx:     nextcord command context: Context
        :param error:   The exception raised: Exception
        :return:        None
        """
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'link':
                await ctx.channel.send("You forgot to add search keywords or a link!")
        elif isinstance(error, commands.MissingRole):
            await ctx.channel.send(f'User does not possess roles for command: {ctx.command}!')
        else:
            print(f'Ignoring exception in command {ctx.command}')
            traceback.print_exception(type(error), error, error.__traceback__)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        """
            The event triggered when an error is raised while invoking a command

        :param ctx:     nextcord message context of command
        :param error:   The exception raised
        :return:        None
        """
        ignored = ()

        # Prevents handling of commands with local handlers
        if hasattr(ctx.command, 'on_error'):
            return

        # Prevents cogs with cog_command_error being handled
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        # Check for original exceptions, if none are found, keep the current one passed to this function
        error = getattr(error, 'original', error)
        # skip ignored errors
        if isinstance(error, ignored):
            return

        # Handling common individual cases
        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f"**Command Not Found!**\nTry {ConfigUtil().get_prefix(ctx, ctx.message)}help",
                                   delete_after=10)

        elif isinstance(error, commands.DisabledCommand):
            await ctx.channel.send(f'command: {ctx.command} has been disabled!',
                                   delete_after=10)

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.channel.send(f'command: {ctx.command} can not be used in Private Messages!')
            except nextcord.HTTPException:
                if config['debug_mode']:
                    print('Commands.error | {}'.format(format_exc()))

        elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            await ctx.channel.send(f'Incorrect arguments for command: {ctx.command}!')

        elif isinstance(error, commands.MissingRole):
            await ctx.channel.send(f'User does not possess roles for command: {ctx.command}!')

        else:
            print(f'Ignoring exception in command {ctx.command}')
            traceback.print_exception(type(error), error, error.__traceback__)


def setup(bot: Bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(Commands(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")
