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


@bot.command(name= 'play', help= 'Connects bot voice')
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
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    # Call Youtube_DL to fetch song info
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # DEBUG COMMAND
        if link == "DEBUG":
            song_info = ydl.extract_info(test_song, download=False)
        else:
            song_info = ydl.extract_info(link, download=False)

    title = song_info['title']
    url = song_info["formats"][0]["url"]

    # Add song to queue
    if song_queue:
        await ctx.channel.send(f"{title} added to Queue", delete_after=20)
    song_queue.append((title, url))

    # Play song if not playing a song
    if not vc.is_playing():
        await play_music_(ctx, vc)


@bot.command(name= 'disconnect', help= 'Disconnects from voice')
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
                print(f"Now Playing {song_queue[0][0]} in {ctx.author.voice.channel.name} of {ctx.guild.name}")
                await ctx.channel.send(f"Now Playing {song_queue[0][0]}", delete_after=20)

        except discord.errors.ClientException:
            print(f"ClientException: Failed to Play Song in {ctx.guild.name}")
            break

        while vc.is_playing():
            await asyncio.sleep(1)

        song_queue.pop(0)

bot.run(TOKEN)
