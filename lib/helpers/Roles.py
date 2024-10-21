# Roles.py

from nextcord import Colour
from nextcord.ext.commands import Bot
from lib.helpers.Utils import ConfigUtil

class RoleHandler:
    """
    Class to handle actions related to roles
    """
    async def createDJRoleForServers(self, bot: Bot):
        """
            Generates DJ role for servers that do not have it

        :param bot:     bot client: Bot
        :return:        None
        """
        config = ConfigUtil().read_config('BOT_SETTINGS')
        roleName = config['dj_role_name']
        for guild in bot.guilds:
            # Skip guilds that have the role
            if roleName in (role.name for role in guild.roles):
                continue

            print(f'Creating role for guild {guild.name}')
            new_role = await guild.create_role(
                name=roleName,
                colour=Colour.orange(),
                hoist=True,
                reason='DJ role created for use of Tempo'
            )
