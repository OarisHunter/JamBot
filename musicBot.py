# musicBot.py

"""
Music Bot
    Plays YouTube linked videos in discord voice channel

    @author: Pierce Thompson
"""

import os
import nextcord

from traceback import format_exc
from nextcord.ext import commands
from dotenv import load_dotenv
from lib.helpers.Utils import ConfigUtil, Util
from lib.helpers.Roles import RoleHandler

# Create member vars
config = ConfigUtil()
extensions = [
    'lib.cogs.commands',
    'lib.cogs.util_commands',
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
    # Check config validity
    if not config.validate_config():
        return
    server_settings = config.read_config('SERVER_SETTINGS')

    # Display table of connected guild information
    labels = ['Guild ID', 'Guild Name', 'Guild Owner', 'Prefix', 'Loop']
    try:
        info = [(guild.id,
                 guild.name,
                 guild.owner.name,
                 server_settings.get(str(guild.id))['prefix'],
                 server_settings.get(str(guild.id))['loop'])
                for guild in bot.guilds]
        print(f"\tConnected to {len(bot.guilds)} servers.")
        Util.display_table(info, labels)
    except BaseException as e:
        if config.read_config('BOT_SETTINGS')['debug_mode']:
            print('musicBot.on_ready | {}'.format(format_exc()))
        print('Failed to display server table')

    # Check if bot is broken
    if config.read_config('BOT_SETTINGS')['broken']:
        await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name="Maintenance"))

    for extension in extensions:
        bot.load_extension(extension)

    roleHandler = RoleHandler()
    await roleHandler.createDJRoleForServers(bot)


if __name__ == "__main__":
    # Run bot
    bot.run(TOKEN, reconnect=True)
