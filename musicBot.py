# musicBot.py

"""
Music Bot

    Plays youtube linked videos in discord voice channel

@author: Pierce Thompson
"""

import ast
import os
import discord
import asyncio
import youtube_dl

from discord.ext import commands
from dotenv import load_dotenv
from configparser import ConfigParser

# Parse Config ini
config_object = ConfigParser()
config_object.read("config.ini")
bot_settings = config_object["BOT_SETTINGS"]
bot_prefix = bot_settings["prefix"]
test_song = bot_settings["test_song"]
ydl_opts = ast.literal_eval(bot_settings["ydl_opts"])
ffmpeg_opts = ast.literal_eval(bot_settings["ffmpeg_opts"])

# Create member vars
song_queue = []

# Create Bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=bot_prefix, intents=intents)


@bot.event
async def on_ready():
    try:
        print("Music Bot is Ready!")

        for guild in bot.guilds:
            print(f"\t{bot.user.name} has connected to {guild.owner.name}'s server | {guild.name} |")

    except discord.DiscordException:
        print("on_ready event failed.")

# -------------- Commands ------------- #


@bot.command(name= 'play', help= 'Connects Bot to Voice')
async def play_(ctx, link):
    await ctx.message.delete()

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

    # Call Youtube_DL to fetch song info
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # DEBUG COMMAND
        if link == "DEBUG":
            song_info = ydl.extract_info(test_song, download=False)
        else:
            song_info = ydl.extract_info(link, download=False)
    # print(song_info)

    # Detect if link is a playlist
    try:
        if song_info['_type'] == 'playlist':
            # If link is a playlist set song_info to a list of songs
            song_info = song_info['entries']
        else:
            print(f"Link from {ctx.guild.name} is unsupported")
    except KeyError:
        pass

    # If link was a playlist, loop through list of songs and add them to the queue
    if type(song_info) == list:
        await ctx.channel.send("**Added Playlist to Queue**", delete_after=20)
        for i in song_info:
            title = i['title']
            url = i["formats"][0]["url"]
            song_queue.append((title, url))
    # Otherwise add the single song to the queue, display message if song was added to the queue
    else:
        title = song_info['title']
        url = song_info["formats"][0]["url"]
        if song_queue:
            await ctx.channel.send(f"**Added to the Queue**\n\n{title}", delete_after=20)
        song_queue.append((title, url))

    # Play song if not playing a song
    if not vc.is_playing():
        await play_music_(ctx, vc)


@bot.command(name= 'skip', help= 'Skips to next Song in Queue')
async def skip_(ctx):
    await ctx.message.delete()

    vc = ctx.guild.voice_client  # Get current voice client
    if vc is None:
        print(f"Skip: Bot not connected to {ctx.guild.name}")
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    # Check that there is another song in the queue and the bot is currently playing
    if len(song_queue) > 1 and vc.is_playing():
        # Pop currently playing off queue
        song_queue.pop(0)

        # Update Voice Client source
        try:
            vc.source = discord.FFmpegPCMAudio(song_queue[0][1], **ffmpeg_opts)
            vc.source = discord.PCMVolumeTransformer(vc.source)
            vc.volume = 1
        except discord.errors.ClientException:
            print(f"ClientException: Failed to Play Song in {ctx.guild.name}")

        # Display now playing message
        await nowPlaying_(ctx)


@bot.command(name= 'clear', help= 'Clears the Song Queue')
async def clear_(ctx):
    await ctx.message.delete()

    # Empty the queue
    global song_queue
    song_queue = []

    # Send response
    await ctx.channel.send("**Cleared the Queue!**", delete_after=20)


@bot.command(name= 'queue', help= 'Displays the Queue')
async def queue_(ctx):
    await ctx.message.delete()

    if song_queue:
        # Build message to display
        queue_message = "**Queue:**\n\n```"
        for count, val in enumerate(song_queue):
            if count < 10:
                queue_message += f"0{count}"
            else:
                queue_message += f"{count}"
            queue_message += f" | {val[0]}\n"
        queue_message += "```"

        # Send response
        await ctx.channel.send(queue_message, delete_after=60)
    else:
        await ctx.channel.send("**Queue is empty!**", delete_after=10)


@bot.command(name= 'np', help= 'Displays the currently playing song')
async def nowPlaying_(ctx):
    try:
        await ctx.message.delete()
    except discord.DiscordException:
        pass

    vc = ctx.message.guild.voice_client
    if vc and vc.is_playing():
        print(f"Now Playing {song_queue[0][0]} in {ctx.author.voice.channel.name} of {ctx.guild.name}")
        await ctx.channel.send(f'**Now Playing**\n\n{song_queue[0][0]}', delete_after=10)
    else:
        print(f'NowPlaying: Not in a Voice Channel in {ctx.guild.name}')
        await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)


@bot.command(name= 'disconnect', help= 'Disconnects from Voice')
async def disconnect_(ctx):
    vc = ctx.guild.voice_client

    # Check that the bot is connected to voice
    if vc.is_connected():
        await vc.disconnect()
        vc = None

    await ctx.message.delete()


# -------------- Functions ------------- #
async def play_music_(ctx, vc):
    while song_queue:
        try:
            if vc.is_connected() and not vc.is_playing():
                # Create FFmpeg audio stream, attach to voice client
                vc.play(discord.FFmpegPCMAudio(song_queue[0][1], **ffmpeg_opts))
                vc.source = discord.PCMVolumeTransformer(vc.source)
                vc.volume = 1

                # Display now playing message
                await nowPlaying_(ctx)

        except discord.errors.ClientException:
            print(f"ClientException: Failed to Play Song in {ctx.guild.name}")
            break

        while vc.is_playing():
            await asyncio.sleep(1)

        if song_queue:
            song_queue.pop(0)

bot.run(TOKEN)
