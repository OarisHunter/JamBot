# musicBot.py

"""
Music Bot

    Plays youtube linked videos in discord voice channel

@author: Pierce Thompson
"""

import os
import discord
import asyncio
import youtube_dl

from discord.ext import commands
from dotenv import load_dotenv
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
bot_settings = config_object["BOT_SETTINGS"]
bot_prefix = bot_settings["prefix"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=bot_prefix, intents=intents)


TEMP_LINK = "https://www.youtube.com/watch?v=zHtcvQAI000"

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
async def play_(ctx):
    if ctx.author.voice is not None:
        try:
            vc = await ctx.author.voice.channel.connect()
        except discord.DiscordException:
            vc = ctx.guild.voice_client
    else:
        await ctx.message.delete()
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    await ctx.message.delete()

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    ffmpeg_options = {
        'options': '-vn',
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        song_info = ydl.extract_info(TEMP_LINK, download=False)

    # print(song_info)

    vc.play(discord.FFmpegPCMAudio(song_info["formats"][0]["url"], **ffmpeg_options))
    vc.source = discord.PCMVolumeTransformer(vc.source)
    vc.volume = 1

    while vc.is_playing():
        await asyncio.sleep(1)


@bot.command(name= 'disconnect', help= 'Disconnects from voice')
async def disconnect_(ctx):
    vc = ctx.guild.voice_client

    if vc.is_connected():
        await vc.disconnect()
        vc = None

    await ctx.message.delete()

bot.run(TOKEN)
