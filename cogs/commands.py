"""

    Bot commands cog

"""

import asyncio
import discord
from discord.ext import commands

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='play', help='Connects Bot to Voice')
    async def play_(self, ctx, *link):
        """
            Command to connect to voice
                plays song
                    from yt link
                    from yt search
                    from yt playlist link
        """
        await ctx.message.delete(delay=5)

        # Check that author is in a voice channel
        if ctx.author.voice is None:
            return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

        # Convert command args to string
        # allows for multi word song searches
        link = tuple_to_string(link)

        # Pass link to parser to determine origin
        song_info, from_youtube = await self.extract_song_info(ctx, link)

        # Check that author is in a voice channel
        if ctx.author.voice is not None:
            try:
                # Connect to channel of author
                vc = await ctx.author.voice.channel.connect()
            except discord.DiscordException:
                # Catch error if already connected
                vc = ctx.guild.voice_client
        else:
            print(f"Play: Bot not connected to {ctx.guild.name}")
            return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

        if song_info:
            # Add song(s) to queue from song info
            await add_song_to_queue(ctx, song_info, from_youtube=from_youtube)

            # Play song if not playing a song
            if not vc.is_playing():
                await play_music_(ctx)