# tasks.py

import nextcord

from nextcord.ext import commands, tasks
from lib.helpers import Utils


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.command_cog = bot.get_cog('Commands')
        self.utilities = Utils.Util

        self.background_update_queue.start()

    @tasks.loop(seconds=60)
    async def background_update_queue(self):
        """
            Multiple process function to update string values in the queue with proper youtube dl songs

        :return:        None
        """
        for guild in self.bot.guilds:
            queue = self.command_cog.queues.get_queue(guild.id)
            # Update queue while playing
            if any(isinstance(song, str) for song in queue):
                print("Strings found!")
                print("starting downloads")

                new_queue = [self.utilities.update_with_yt(queue, start, stop)
                             for start, stop in [(0, len(queue)/2), (len(queue)/2, len(queue))]]
                print('finished downloads')
                print(new_queue)

    @background_update_queue.before_loop
    async def before_start(self):
        await self.bot.wait_until_ready()


def setup(bot):
    # Required Function for Cog loading
    bot.add_cog(Tasks(bot))
