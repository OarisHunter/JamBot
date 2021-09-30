# events.py

from discord.ext import commands
from subfunctions.helpers import Utils


class Events(commands.Cog):
    """
    Discord Cog for event handling
    """
    def __init__(self, bot):
        self.bot = bot
        self.default_prefix = '~'
        self.embeds = Utils.Embeds(bot)
        self.utilities = Utils.Util()
        self.config = Utils.ConfigUtil()
        self.command_cog = bot.get_cog("Commands")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
            Disconnects bot if it is alone in a voice channel

        :param member:  discord.Member object of member whose voice state changed, automatically passed
        :param before:  discord.VoiceState prior to change, automatically passed
        :param after:   discord.VoiceState after change, automatically passed
        :return:        None
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

        :param guild:   discord.Guild object, automatically passed
        :return:        None
        """
        # Set prefix of new server to default prefix
        self.config.write_config('w', "PREFIXES", str(guild.id), self.default_prefix)

        # Update server queues
        self.command_cog.queues.create_server_queue()

        print(f"{self.bot.user.name} added to {guild.name}!")

        await guild.system_channel.send(embed=self.embeds.generate_new_server_embed(guild))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """
            Removes guild id and stored prefix from config.ini

        :param guild:   discord.Guild object, automatically passed
        :return:        None
        """
        # remove server's prefix from config
        self.config.write_config('d', "PREFIXES", str(guild.id))

        # Update server queues
        self.command_cog.queues.create_server_queue()

        print(f"{self.bot.user.name} removed from {guild.name}")

def setup(bot):
    # Required Function for Cog loading
    bot.add_cog(Events(bot))
