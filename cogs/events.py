"""

    Discord event handler

"""

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_prefix = '~'

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
        # Parse Config, get server prefixes
        config_object = ConfigParser()
        config_object.read("config.ini")
        bot_prefixes = config_object["PREFIXES"]

        # Set prefix of new server to default prefix
        bot_prefixes[str(guild.id)] = self.default_prefix

        # Update server queues
        create_server_queue()

        print(f"{self.bot.user.name} added to {guild.name}!")
        # try:
        await guild.system_channel.send(embed=generate_new_server_embed(guild, self.bot, embed_theme))
        # except discord.DiscordException:
        #     print(f"Couldn't send new server message in {guild.name}")

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """
            Removes guild id and stored prefix from config.ini
        """
        # Parse Config, get server prefixes
        config_object = ConfigParser()
        config_object.read("config.ini")
        bot_prefixes = config_object["PREFIXES"]

        # remove server's prefix from config
        bot_prefixes.pop(str(guild.id))

        # Update server queues
        create_server_queue()

        print(f"{self.bot.user.name} removed from {guild.name}")

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)