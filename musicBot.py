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
config = ConfigUtil()
extensions = [
    'lib.cogs.commands',
    'lib.cogs.events'
]

# Create Bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
# TOKEN = os.getenv('TEST_TOKEN')
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix=config.get_prefix, intents=intents, help_command=None)
# bot = commands.Bot(command_prefix='`', intents=intents, help_command=None)


@bot.event
async def on_ready():
    """
        Called when bot start-up has finished
    """
    # Start-up messages
    print("-*-*-*-*-*-*-*-* Tempo is Ready! *-*-*-*-*-*-*-*-*-*-")
    print("Read bot settings from Config!")
    print(f"\tConnected to {len(bot.guilds)} servers.")
    print(f"\t{'-'*8}Guild ID{'-'*(18+3)}Guild Name{'-'*25}Guild Owner{'-'*13}")
    for guild in bot.guilds:
        print(f'\t| {guild.id} | {guild.name:>34} | {guild.owner.name:>34} |')

    for extension in extensions:
        bot.load_extension(extension)

if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
