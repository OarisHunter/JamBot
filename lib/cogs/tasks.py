# tasks.py

import nextcord

from nextcord.ext import commands, tasks
from nextcord.ext.commands import Bot
from lib.helpers.Utils import Util
from lib.helpers.Utils import ConfigUtil
from traceback import format_exc


class Tasks(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.utilities = Util()
        self.commands = bot.get_cog("Commands")
        self.config_obj = ConfigUtil()
        self.config = self.config_obj.read_config('BOT_SETTINGS')

        self.start_tasks()

    @tasks.loop(seconds=20)
    async def update_queues(self) -> None:
        """
            Background task to update server queues that have non-YouTube sourced songs

        :return:    None
        """
        try:
            for guild in self.bot.guilds:
                server_queue = self.commands.queues.get_queue(guild.id)
                for song in server_queue:
                    if len(song) == 2:  # Song is from non-youtube source
                        await self.utilities.repopulate_queue(server_queue)
                        break
        except IndexError or ValueError:
            if self.config['debug_mode']:
                print('Util.repopulate_queue | {}'.format(format_exc()))

    @update_queues.before_loop
    async def wait_until_login(self) -> None:
        """
            Blocks tasks from beginning before bot has finished logging in

        :return:    None
        """
        await self.bot.wait_until_ready()

    def start_tasks(self) -> None:
        """
            Task start wrapper

        :return:    None
        """
        self.update_queues.start()


def setup(bot: Bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(Tasks(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")
