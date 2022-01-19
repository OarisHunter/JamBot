import nextcord

from nextcord.ext import commands


class ApplicationCommands(commands.Cog):
    @nextcord.slash_command()
    async def slash_test(self, ctx):
        await ctx.channel.send("Slash command!")


def setup(bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(ApplicationCommands(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")
