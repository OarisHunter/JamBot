import nextcord

from nextcord import Message
from nextcord.ext import commands
from nextcord.ext.commands import Context, Bot
from lib.helpers.Utils import ConfigUtil
from lib.ui import views
from lib.helpers.Embeds import Embeds

class UtilCommands(commands.Cog):
    """
        nextcord Cog for utility based command handling
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.embeds = Embeds(bot)

        self.config_obj = ConfigUtil()
        config = self.config_obj.read_config('BOT_SETTINGS')
        self.view_timeout = config['view_timeout']

    @commands.command(name='purge',
                      help='Cleans messages from specified user in current channel',
                      usage="[number of messages to delete] {user}")
    async def msg_purge_(self, ctx: Context, num: int, *, user: str = ""):
        """
            Purges messages from specified user in current channel

        :param ctx:             Discord message context: Context
        :param num:             Number of messages to purge: int
        :param user:            User to purge messages of: str
        :return:                None
        """
        def check_author(msg: Message):
            return msg.author.id == matched_users[0]

        try:
            await ctx.message.delete(delay=1)
        except nextcord.DiscordException:
            pass

        if user != "":
            members = [(
                user.id,
                f"{user.nick}#{user.discriminator}" if user.nick is not None else f"{user.name}#{user.discriminator}")
                for user in ctx.guild.members]
            matched_users = [member for member in members if user.upper() in member[1].upper()]
        else:
            matched_users = [(self.bot.user.id, f"{self.bot.user.name}")]

        # Display option for several matched users
        if len(matched_users) > 1:
            view = views.PurgeView(self.bot, ctx, matched_users, "Select user", self.view_timeout)
            await view.create_message()
            await view.wait()
            matched_users = matched_users[view.value]
        else:
            matched_users = matched_users[0]

        # Confirm action
        view = views.ConfirmView(self.view_timeout)
        confirm_msg = await ctx.channel.send(f"Purge {num} of {matched_users[1]}'s messages?", view=view)
        await view.wait()
        await confirm_msg.delete()
        if view.value:
            deleted = await ctx.channel.purge(limit=num+1, check=check_author)
            await ctx.channel.send(embed=self.embeds.generate_purge_embed(ctx, matched_users[1], deleted), delete_after=10)
        else:
            await ctx.channel.send("**Canceled Message Purge**", delete_after=5)


def setup(bot: Bot):
    # Required Function for Cog loading
    try:
        bot.add_cog(UtilCommands(bot))
    except nextcord.ext.commands.errors.ExtensionAlreadyLoaded:
        print("Extension already loaded.")