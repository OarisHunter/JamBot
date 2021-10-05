# commands.py

import nextcord
import random

from nextcord.ext import commands
from lib.helpers import SongQueue, Utils, SongSearch
from lib.ui import views


class Commands(commands.Cog):
    """
        nextcord Cog for command handling
    """
    def __init__(self, bot):
        self.bot = bot
        self.queues = SongQueue.SongQueue(bot)
        self.utilities = Utils.Util()
        self.embeds = Utils.Embeds(bot)

        # Get config values
        config = Utils.ConfigUtil().read_config('BOT_SETTINGS')
        self.test_song = config['test_song']
        self.ydl_opts = config['ydl_opts']
        self.ffmpeg_opts = config['ffmpeg_opts']
        self.default_prefix = config['default_prefix']
        self.queue_display_length = config['queue_display_length']

    @commands.command(name='play', aliases=['p'], help='Connects Bot to Voice')
    async def play_(self, ctx, *, link):
        """
            Command to connect to voice
                plays song
                    from yt link
                    from yt search
                    from yt playlist link

        :param ctx:     Command context
        :param link:    Given link :tuple
        :return:        None
        """
        await ctx.message.delete(delay=5)

        # Check that author is in a voice channel
        if ctx.author.voice is None:
            return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

        # Pass link to parser to determine origin
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

            # Play song if not playing a song
            if not vc.is_playing():
                await self.queues.play_music_(ctx)

    @commands.command(name='skip', help='Skips to next Song in Queue')
    async def skip_(self, ctx, num: int = 1):
        """
            Command to skip currently playing song

        :param ctx:     Command Context
        :param num:     number of songs to skip
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

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
                if type(song_queue[0]) == str:
                    yt_dl = await self.queues.download_from_yt(ctx, song_queue[0])
                    song_queue[0] = self.utilities.song_info_to_tuple(yt_dl[0], ctx)
                song_url = song_queue[0][1]
                # Create FFmpeg audio stream, attach to voice client
                vc.source = nextcord.FFmpegPCMAudio(song_url, **self.ffmpeg_opts)
                vc.source = nextcord.PCMVolumeTransformer(vc.source)
                vc.volume = 1

                await ctx.channel.send("**Skipped a Song!**", delete_after=10)
                await ctx.invoke(self.bot.get_command('np'))
            else:
                vc.stop()
                await ctx.channel.send("**Skipped a Song!**", delete_after=10)

        except nextcord.DiscordException:
            pass

    @commands.command(name='clear', help='Clears the Song Queue')
    async def clear_(self, ctx):
        """
            Command to clear server's Queue

        :param ctx:     Command context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

            # Empty the queue
            self.queues.get_queue(ctx.guild.id).clear()

            # Send response
            await ctx.channel.send("**Cleared the Queue!**", delete_after=20)

        except nextcord.DiscordException:
            pass

    @commands.command(name='queue', help='Displays the Queue')
    async def queue_(self, ctx):
        """
            Command to display songs in server's Queue

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

            song_queue = self.queues.get_queue(ctx.guild.id)
            if song_queue:
                embed = self.embeds.generate_display_queue(ctx, song_queue)

                await ctx.channel.send(embed=embed, delete_after=60)
            else:
                await ctx.channel.send("**Queue is empty!**", delete_after=10)

        except nextcord.DiscordException:
            pass

    @commands.command(name='np', help='Displays the currently playing song')
    async def nowPlaying_(self, ctx):
        """
            Command to display "Now Playing" message

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

            vc = ctx.message.guild.voice_client
            song_queue = self.queues.get_queue(ctx.guild.id)
            if vc and vc.is_playing():
                print(f"Now Playing {song_queue[0][0]} in {ctx.author.voice.channel.name} of {ctx.guild.name}")
                await ctx.channel.send(embed=self.embeds.generate_np_embed(ctx, song_queue[0]))
            else:
                print(f'NowPlaying: Not in a Voice Channel in {ctx.guild.name}')
                await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

        except nextcord.DiscordException:
            pass

    @commands.command(name='pause', help='Pauses currently playing song')
    async def pause_(self, ctx):
        """
            Pauses music to be resumed later

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

            vc = ctx.guild.voice_client

            if vc.is_connected() and vc.is_playing():
                vc.pause()
                await ctx.channel.send(f'**Music Paused!**', delete_after=10)
            elif vc.is_connected() and vc.is_paused():
                await ctx.channel.send(f'Already Paused', delete_after=10)
            elif vc.is_connected() and not vc.is_playing():
                await ctx.channel.send(f'Not Playing Anything', delete_after=10)
            else:
                await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

        except nextcord.DiscordException:
            pass

    @commands.command(name='resume', help='Resumes currently playing song')
    async def resume_(self, ctx):
        """
            Resumes paused music

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            pass

        vc = ctx.guild.voice_client

        if vc.is_connected() and vc.is_paused():
            vc.resume()
            await ctx.channel.send(f'**Music Resumed!**', delete_after=10)
        elif vc.is_connected() and vc.is_playing():
            await ctx.channel.send(f'Already Playing', delete_after=10)
        elif vc.is_connected() and not vc.is_paused():
            await ctx.channel.send(f'Not Playing Anything', delete_after=10)
        else:
            await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    @commands.command(name='disconnect', help='Disconnects from Voice')
    async def disconnect_(self, ctx):
        """
            Command to disconnect bot from voice

        :param ctx:     Command Context
        :return:        None
        """
        try:
            vc = ctx.guild.voice_client

            # Check that the bot is connected to voice
            if vc and vc.is_connected():
                await vc.disconnect()

            await ctx.message.delete()

        except nextcord.DiscordException:
            pass

    @commands.command(name='prefix', help='Changes prefix for this server')
    @commands.has_permissions(administrator=True)
    async def prefix_(self, ctx, *, prefix):
        """
            Command to change/display server defined prefix

        :param ctx:     Command Context
        :param prefix:  User entered prefix: tuple
        :return:        None
        """
        config = Utils.ConfigUtil()

        # If a prefix was given, change the prefix, otherwise display the current prefix
        if prefix and len(prefix) < 2:
            # Update config file
            config.write_config('w', 'PREFIXES', str(ctx.guild.id), str(''.join(prefix)))

            await ctx.channel.send(f"Prefix for {ctx.guild.name} has been changed to: "
                                   f"{config.read_config('PREFIXES')[str(ctx.guild.id)]}",
                                   delete_after=10)
        else:
            await ctx.channel.send(f"Prefix for {ctx.guild.name} is: "
                                   f"{config.read_config('PREFIXES')[str(ctx.guild.id)]}",
                                   delete_after=10)

    @commands.command(name='invite', help='Shows invite link to add bot to your server')
    async def invite_(self, ctx):
        """
            Sends an embed with invite links to add bot to other servers.

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            pass

        await ctx.channel.send(embed=self.embeds.generate_invite(ctx))

    @commands.command(name='search', help=f'Searches with given keywords, displays top results')
    async def search(self, ctx, *, keywords):
        """
            Searches Youtube for given keywords, displays the top 'x' results, allows user to select from list with
            button UI

            https://open.spotify.com/playlist/19SBkYmRd5KzPGKnE5djJ6?si=423e5a9f2dbc462c

        :param ctx:         Discord message context
        :param keywords:    User entered string
        :return:            None
        """
        search = SongSearch.SongSearch()
        view = views.SearchView()

        results = search.search_yt(keywords)

        message = await ctx.channel.send(embed=self.embeds.generate_search_embed(ctx, results),
                                         view=view)

        isTimeout = await view.wait()
        await message.delete()

        if not isTimeout:
            selected_song = results[view.value]
            await ctx.invoke(self.bot.get_command('play'), link=selected_song[1])

    @commands.command(name='shuffle', help='Shuffles the queue')
    async def shuffle_(self, ctx):
        """
            Shuffles the server song queue

        :param ctx:     Discord message context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)

            song_queue = self.queues.get_queue(ctx.guild.id)
            if song_queue:
                random.shuffle(song_queue)
                await ctx.channel.send(f"**Shuffled the Queue!**", delete_after=10)
                await ctx.invoke(self.bot.get_command('queue'))
            else:
                await ctx.channel.send(f'Nothing in the Queue!', delete_after=10)
        except nextcord.DiscordException:
            pass

    @commands.command(name='help')
    async def help_(self, ctx):
        """
            Custom help command

        :param ctx:     Command Context
        :return:        None
        """
        try:
            await ctx.message.delete(delay=5)
        except nextcord.DiscordException:
            pass
        embed, num_pages = self.embeds.generate_help(ctx, 0)
        view = views.HelpView(num_pages)
        current_page = view.current_page
        message = await ctx.channel.send(embed=embed, view=view)

        while not view.is_finished():
            if not view.current_page == current_page:
                print("test")
                current_page = view.current_page
                embed, _ = self.embeds.generate_help(ctx, current_page)
                await message.edit(embed=embed, view=view)

def setup(bot):
    # Required Function for Cog loading
    bot.add_cog(Commands(bot))
