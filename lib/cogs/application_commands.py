import nextcord

from nextcord import Interaction
from nextcord.ext import commands

TEST_GUILDS = [138622532248010752]


class ApplicationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name='test',
                            description='first slash command',
                            guild_ids=TEST_GUILDS)
    async def slash_test(self, interaction: Interaction):
        await interaction.response.send_message("Slash command!")


def setup(bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(ApplicationCommands(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")
