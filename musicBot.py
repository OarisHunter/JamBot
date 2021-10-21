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
    'lib.cogs.events',
    'lib.cogs.tasks'
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
    print("Read from config!")
    server_settings = config.read_config('SERVER_SETTINGS')
    print(f"\tConnected to {len(bot.guilds)} servers.")
    print(f"\t{'-'*8}Guild ID{'-'*(18+3)}Guild Name{'-'*25}Guild Owner{'-'*14}Prefix{'-'*6}Loop{'-'*3}")
    for guild in bot.guilds:
        print(f"\t"
              f"| {guild.id} "
              f"| {guild.name:>34} "
              f"| {guild.owner.name:>34} "
              f"| {server_settings[str(guild.id)]['prefix']:>7} "
              f"| {server_settings[str(guild.id)]['loop']:>7} |")

    for extension in extensions:
        bot.load_extension(extension)

if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
