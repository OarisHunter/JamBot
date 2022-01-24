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
    'lib.cogs.tasks',
    'lib.cogs.application_commands'
]

# Create Bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix=config.get_prefix, intents=intents, help_command=None)


@bot.event
async def on_ready():
    """
        Called when bot start-up has finished
    """
    # Check config validity
    if not config.validate_config():
        return
    server_settings = config.read_config('SERVER_SETTINGS')

    # Display table of connected guild information
    labels = ['Guild ID', 'Guild Name', 'Guild Owner', 'Prefix', 'Loop']
    info = [(guild.id,
             guild.name,
             guild.owner.name,
             server_settings[str(guild.id)]['prefix'],
             server_settings[str(guild.id)]['loop'])
            for guild in bot.guilds]
    length_list = [len(str(element)) for row in info for element in row]
    column_width = max(length_list)
    print(f"\tConnected to {len(bot.guilds)} servers.")
    print(' ', '---'.join(label[:column_width - 1].rjust(column_width + 2, '-') for label in labels))
    for row in info:
        print(' ', ' | '.join(str(element).rjust(column_width + 2) for element in row))

    # Check if bot is broken
    if config.read_config('BOT_SETTINGS')['broken']:
        await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="Maintenance"))

    for extension in extensions:
        bot.load_extension(extension)

if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
