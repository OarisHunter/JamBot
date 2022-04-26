# events.py

import nextcord

from nextcord import Member, Guild, VoiceState
from nextcord.ext import commands
from nextcord.ext.commands import Bot
from lib.helpers.Utils import Util, ConfigUtil
from lib.helpers.Embeds import Embeds


class Events(commands.Cog):
    """
    nextcord Cog for event handling
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.default_prefix = "~"
        self.embeds = Embeds(bot)
        self.utilities = Util()
        self.config_obj = ConfigUtil()
        self.command_cog = bot.get_cog("Commands")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """
            Disconnects bot if it is alone in a voice channel

            Checks if bot is alone each time the voice state of a member in a guild the bot is a part of changes
                TODO: filter out VoiceState changes earlier to reduce computational load

        :param member:  object of member whose voice state changed, automatically passed: Member
        :param before:  nextcord VoiceState prior to change, automatically passed: VoiceState
        :param after:   nextcord VoiceState after change, automatically passed: VoiceState
        :return:        None
        """
        try:
            # Check if bot is alone in channel, disconnect it if so
            bot_channel = member.guild.voice_client.channel
            if bot_channel is not None:
                members = bot_channel.members
                if self.bot.user in members and len(members) == 1:
                    # Disconnect bot
                    await member.guild.voice_client.disconnect(force=False)

                    # Clear server song queue
                    self.command_cog.queues.clear_queue(member.guild.id)

                    # Turn off song loop in guild
                    server_settings = self.config_obj.read_config("SERVER_SETTINGS")
                    server = server_settings[str(member.guild.id)]
                    server['loop'] = False
                    self.config_obj.write_config('w', 'SERVER_SETTINGS', str(member.guild.id), server)

        except AttributeError:
            pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        """
            Removes guild id and stored prefix from config.ini

        :param guild:   guild the server joined, automatically passed: Guild
        :return:        None
        """
        # Set prefix of new server to default prefix and loop toggle
        default = {"prefix": self.default_prefix, "loop": False}
        self.config_obj.write_config('w', "SERVER_SETTINGS", str(guild.id), default)

        # Update server queues
        self.command_cog.queues.create_server_queue()

        print(f"{self.bot.user.name} added to {guild.owner.name}'s guild {guild.name}")

        # send the welcome message to the new guild
        await guild.system_channel.send(embed=self.embeds.generate_new_server_embed(guild))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        """
            Removes guild id and stored prefix from config.ini

        :param guild:   guild the server left, automatically passed: Guild
        :return:        None
        """
        # remove server's prefix from config
        self.config_obj.write_config('d', "SERVER_SETTINGS", str(guild.id))

        # Update server queues
        self.command_cog.queues.create_server_queue()

        print(f"{self.bot.user.name} removed from {guild.name}")


def setup(bot: Bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(Events(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")
