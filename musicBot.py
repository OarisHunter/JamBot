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
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix=config.get_prefix, intents=intents, help_command=None)


@bot.event
async def on_ready():
    """
        Called when bot start-up has finished
    """
    # Start-up messages
    print("-*-*-*-*-*-*-*-* Tempo is Ready! *-*-*-*-*-*-*-*-*-*-")
    server_settings = config.read_config('SERVER_SETTINGS')
    print("\tRead from config!")

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
    print('\t', '---'.join(label[:column_width - 1].rjust(column_width + 2, '-') for label in labels))
    for row in info:
        print('\t', ' | '.join(str(element).rjust(column_width + 2) for element in row))

    if config.read_config('BOT_SETTINGS')['broken']:
        await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="Maintenance"))

    for extension in extensions:
        bot.load_extension(extension)

if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
