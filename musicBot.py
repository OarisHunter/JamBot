# musicBot.py

"""
Music Bot
    Plays YouTube linked videos in discord voice channel

    @author: Pierce Thompson
"""

import os
import nextcord

from nextcord.ext import commands
from dotenv import load_dotenv
from lib.helpers.Utils import ConfigUtil

# Create member vars
TEST_MODE = False
config = ConfigUtil()
extensions = [
    'lib.cogs.commands',
    'lib.cogs.events'
]

# Create Bot
load_dotenv()
if TEST_MODE:
    TOKEN = os.getenv('TEST_TOKEN')
    intents = nextcord.Intents.all()
    bot = commands.Bot(command_prefix="`", intents=intents, help_command=None)
else:
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = nextcord.Intents.all()
    bot = commands.Bot(command_prefix=config.get_prefix, intents=intents, help_command=None)


@bot.event
async def on_ready():
    """
        Called when bot start-up has finished
    """
    try:
        # Start-up messages
        print("Music Bot is Ready!")
        print("Read bot settings from Config!")
        for guild in bot.guilds:
            print(f"\t{bot.user.name} has connected to {guild.owner.name}'s server | {guild.name} |")

        for extension in extensions:
            bot.load_extension(extension)

    except nextcord.DiscordException as e:
        print("on_ready event failed.")
        print(e)

if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
