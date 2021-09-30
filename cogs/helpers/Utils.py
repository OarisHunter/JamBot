# Utils.py

import discord
import math

from configparser import ConfigParser

class ConfigUtil:
    """
        Config Utility functions for music bot
    """
    def get_prefix(self, client, message):
        """
            Get prefixes from config.ini
        """
        prefixes = self.read_config('PREFIXES')
        # in DM messages force default prefix
        if not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return prefixes[str(message.guild.id)]

    @staticmethod
    def read_config(field):
        """
            Get server options from config.ini

        :return:        Tuple with config values
        """

        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[field]
        return config_field

    @staticmethod
    def write_config(mode, field, key, value=None):
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete
        :param field:   Config.ini field
        :param key:     Key for value in config
        :param value:   Value for key in config
        :return:        NULL
        """
        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[str(field)]

        if mode == 'w':
            config_field[str(key)] = value
        elif mode == 'd':
            config_field.pop(str(key))
        else:
            print('invalid config write mode')

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)

class Util:
    """
        Utility functions for music bot
    """
    @staticmethod
    def tuple_to_string(tup):
        """
            Converts an indeterminate length tuple to a string

        :return:    string
        """
        temp = ""
        for i in tup:
            temp += i + " "
        return temp.strip()

    @staticmethod
    def song_info_to_tuple(song_info, ctx):
        """
            Extract info from song_info into song tuple
            song = tuple:(string:title,
                              string:url,
                              string:web_page,
                              string:ctx.message.author,
                              int:duration,
                              string:thumbnail)
        """
        title = song_info['title']
        url = song_info["formats"][0]["url"]
        web_page = song_info['webpage_url']
        duration = song_info['duration']
        thumbnail = song_info["thumbnails"][-1]['url']
        return title, url, web_page, ctx.message.author, duration, thumbnail

class Embeds:
    """
        Embed functions for music bot
    """
    def __init__(self, bot):
        self.bot = bot
        self.config = ConfigUtil()
        self.utilities = Util()
        bot_settings = self.config.read_config('BOT_SETTINGS')
        self.invite_link = bot_settings['invite_link']
        self.embed_theme = int(bot_settings['embed_theme'], 0)
        self.queue_display_length = int(bot_settings['queue_display_length'])
        self.default_prefix = bot_settings['default_prefix']

    def generate_np_embed(self, ctx, song: tuple):
        """
            Generates embed for "Now Playing" messages

            song: tuple (song_title, playback_url, webpage_url, author of request)
        """
        embed = discord.Embed(title="Now Playing", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_image(url=song[5])
        embed.add_field(name="Song: ",
                        value=f"[{song[0]}]({song[2]})\n"
                              f"Duration - {math.floor(song[4] / 60)}:{str(math.floor(song[4] % 60)).rjust(2, '0')}",
                        inline=False)
        embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
        return embed

    def generate_added_queue_embed(self, ctx, song):
        """
            Generates embed for "Added to Queue" messages

            song: tuple (song_title, playback_url, webpage_url, author of request)
        """
        embed = discord.Embed(title="Added to Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        if type(song) == tuple:
            embed.add_field(name="Song: ", value=f"[{song[0]}]({song[2]})", inline=False)
            embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
        else:
            overflow = False
            for count, i in enumerate(song):
                # Cap queued song display length
                if count == self.queue_display_length:
                    overflow = True
                    break
                # Embed link if song info is from youtube
                if type(i) == str:
                    embed.add_field(name=f"{count + 1}: ", value=f"{i}", inline=False)
                else:
                    embed.add_field(name=f"{count + 1}: ", value=f"[{i[0]}]({i[2]})", inline=False)
            if overflow:
                embed.set_footer(text=f"+{len(song) - self.queue_display_length} more")
            else:
                embed.set_footer(text=f"Requested by {song[0][3].name}", icon_url=song[0][3].avatar_url)
        return embed

    def generate_display_queue(self, ctx, queue):
        """
            Generates embed for "Queue" messages

            queue: Server song queue
        """
        embed = discord.Embed(title="Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        # Build message to display
        overflow = False
        for count, song in enumerate(queue):
            # Cap queue display length
            if count == self.queue_display_length:
                overflow = True
                break
            # Embed link if song info is from youtube
            if type(song) == str:
                embed.add_field(name=f"{count + 1}: ", value=f"{song}", inline=False)
            else:
                embed.add_field(name=f"{count + 1}: ", value=f"[{song[0]}]({song[2]})", inline=False)
        # Display overflow message
        if overflow:
            embed.set_footer(text=f"+{len(queue) - self.queue_display_length} more")

        # return embed
        return embed

    def generate_invite(self, ctx):
        """
            Generate invite embed
        """
        embed = discord.Embed(title="Invite Link", url=self.invite_link, color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        embed.add_field(name=f"Copyable link:", value=f"{self.invite_link}", inline=False)

        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.avatar_url)

        return embed

    def generate_help(self, ctx):
        """
            Generates help embed
        """
        embed = discord.Embed(title="Help", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        for i in self.bot.commands:
            if not i.name == 'help':
                embed.add_field(name=self.config.get_prefix(ctx, ctx) + i.name, value=i.help, inline=False)

        return embed

    def generate_new_server_embed(self, guild):
        """
            Generate new server embed
        """
        embed = discord.Embed(title="Thanks for adding Tempo!", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        embed.add_field(name="Getting Started!",
                        value="Use '~help' to get started.\n"
                              "You can change the prefix from '~' by using '~prefix <new prefix>",
                        inline=False)

        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬",
                        value='\u200b',
                        inline=False)

        embed.add_field(name="Bot is under constant development, Pardon the dust!",
                        value="Restarts are frequent, songs may cut out during a restart.",
                        inline=False)

        embed.set_image(url=self.bot.user.avatar_url)

        embed.set_footer(text=f"{self.bot.user.name} added to {guild.name}!", icon_url=guild.icon_url)

        return embed
