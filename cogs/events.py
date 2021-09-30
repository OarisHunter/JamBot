"""

    Discord event handler

"""

from discord.ext import commands
from .helpers import utils


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_prefix = '~'
        self.embeds = utils.Embeds(bot)
        self.utilities = utils.Util()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
            Disconnects bot if it is alone in a voice channel
        """
        try:
            # Check if bot is alone in channel, disconnect it if so
            bot_channel = member.guild.voice_client.channel
            if bot_channel is not None:
                members = bot_channel.members
                if self.bot.user in members and len(members) == 1:
                    # Disconnect bot
                    await member.guild.voice_client.disconnect()

        except AttributeError:
            pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
            Removes guild id and stored prefix from config.ini
        """

        # Set prefix of new server to default prefix
        utils.ConfigUtil().write_config('w', 'PREFIXES', str(guild.id), self.default_prefix)

        # Update server queues
        self.queues.create_server_queue()

        print(f"{self.bot.user.name} added to {guild.name}!")

        await guild.system_channel.send(embed=self.embeds.generate_new_server_embed(guild))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """
            Removes guild id and stored prefix from config.ini
        """
        # remove server's prefix from config
        utils.ConfigUtil().write_config('d', 'PREFIXES', str(guild.id))

        # Update server queues
        self.queues.create_server_queue()

        print(f"{self.bot.user.name} removed from {guild.name}")

def setup(bot):
    bot.add_cog(Events(bot))
