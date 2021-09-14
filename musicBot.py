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


@bot.command(name= 'disconnect', help= 'Disconnects from voice')
async def disconnect_(ctx):
    vc = ctx.guild.voice_client

    if vc.is_connected():
        await vc.disconnect()
        vc = None

    await ctx.message.delete()

bot.run(TOKEN)
