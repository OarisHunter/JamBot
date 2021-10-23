# tasks.py

from nextcord.ext import commands, tasks
from lib.helpers import Utils

class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.utilities = Utils.Util()
        self.commands = bot.get_cog("Commands")

        self.start_tasks()

    @tasks.loop(seconds=20)
    async def update_queues(self):
        """
            Background task to update server queues that have non-YouTube sourced songs

        :return:    None
        """
        for guild in self.bot.guilds:
            server_queue = self.commands.queues.get_queue(guild.id).copy()
            for song in server_queue:
                if len(song) == 2:  # Song is from non-youtube source
                    # Generate new queue with updated song values
                    new_queue = await self.utilities.get_new_queue(server_queue)
                    # TODO: Check that this is still required, fixed an old bug
                    while not len(server_queue) == len(new_queue):
                        new_queue = await self.utilities.get_new_queue(server_queue)

                    # Truncate queue to match current queue
                    old_queue_len = self.commands.queues.get_queue(guild.id)
                    if not len(new_queue) == len(old_queue_len):
                        new_queue = new_queue[len(new_queue) - len(old_queue_len):]

                    self.commands.queues.set_queue(guild.id, new_queue)
                    break

    @update_queues.before_loop
    async def wait_until_login(self):
        """
            Blocks tasks from beginning before bot has finished logging in

        :return:    None
        """
        await self.bot.wait_until_ready()

    def start_tasks(self):
        """
            Task start wrapper

        :return:    None
        """
        self.update_queues.start()

def setup(bot):
    # Required Function for Cog loading
    bot.add_cog(Tasks(bot))
