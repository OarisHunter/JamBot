# Utils.py
import sys

import nextcord
import math
import ast
import youtube_dl

from configparser import ConfigParser


class ConfigUtil:
    """
        Config Utility functions for music bot
    """
    def get_prefix(self, client, message):
        """
            Get prefixes from config.ini

        :param client:      nextcord.Client object, automatically passed
        :param message:     nextcord.Message object
        :return:            guild prefix str from config
        """
        server_config = self.read_config('SERVER_SETTINGS')
        # in DM messages force default prefix
        if not message.guild:
            return self.read_config('BOT_SETTINGS')['default_prefix']
        return server_config[str(message.guild.id)]['prefix']

    @staticmethod
    def read_config(field):
        """
            Get server options from config.ini

            Convert to proper types here (default is str)

        :param field:   config.ini field to read and return values from
        :return:        Tuple with config values
        """
        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[field]

        config_dict = {}
        if field == 'BOT_SETTINGS':
            config_dict["invite_link"] = config_field['invite_link']
            config_dict["test_song"] = config_field['test_song']
            config_dict['ydl_opts'] = ast.literal_eval(config_field['ydl_opts'])
            config_dict['ffmpeg_opts'] = ast.literal_eval(config_field['ffmpeg_opts'])
            config_dict['embed_theme'] = int(config_field['embed_theme'], 0)
            config_dict['queue_display_length'] = int(config_field['queue_display_length'])
            config_dict['default_prefix'] = config_field['default_prefix']
            config_dict['view_timeout'] = int(config_field['view_timeout'])
        elif field == 'SERVER_SETTINGS':
            for i in config_field.keys():
                temp = ast.literal_eval(config_field[i])
                config_dict[i] = {'prefix': temp['prefix'], 'loop': bool(temp['loop'])}
        else:
            print("Bad field passed to read_config")
        return config_dict

    @staticmethod
    def write_config(mode, field, key, value=None):
        """
            Writes/Deletes key-value pair to config.ini

        :param mode:    'w' = write | 'd' = delete
        :param field:   Config.ini field
        :param key:     Key for value in config
        :param value:   Value for key in config
        :return:        None
        """
        config_object = ConfigParser()
        config_object.read("config.ini")
        config_field = config_object[str(field)]

        if mode == 'w':
            config_field[str(key)] = str(value)
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
    def __init__(self):
        config_obj = ConfigUtil()
        config = config_obj.read_config('BOT_SETTINGS')
        self.test_song = config['test_song']
        self.ydl_opts = config['ydl_opts']

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

        :param song_info:   dict from youtube_dl download
        :param ctx:         Command Context
        :return:            tuple:(string:title,
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

    def download_from_yt(self, link):
        """
            Extracts info from yt link, adds song to server queue, plays song from queue.

        :param link:    link str
        :return:        song info dict
                        list of song info dicts if link is a playlist
        """
        # Call Youtube_DL to fetch song info
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            # DEBUG COMMAND, pass test song from config in place of link
            if link == "DEBUG":
                song_info = ydl.extract_info(self.test_song, download=False)
            else:
                song_info = ydl.extract_info(link, download=False)
        # print(song_info)  # Debug call to see youtube_dl output

        # Detect if link is a playlist
        try:
            if song_info['_type'] == 'playlist':
                # If link is a playlist set song_info to a list of songs
                song_info = song_info['entries']
        except KeyError:
            pass

        return song_info

    def update_with_yt(self, ctx, queue, start, stop, count, return_dict):
        result = []
        for i in queue[start:stop]:
            if type(i) == str:
                song_info = self.download_from_yt(i)
                song = self.song_info_to_tuple(song_info, ctx)
                result.append(song)
        return_dict[count] = result

class Embeds:
    """
        Embed functions for music bot
    """
    def __init__(self, bot):
        self.bot = bot
        self.config = ConfigUtil()
        self.utilities = Util()

        # Get config values
        bot_settings = self.config.read_config('BOT_SETTINGS')
        self.invite_link = bot_settings['invite_link']
        self.embed_theme = bot_settings['embed_theme']
        self.queue_display_length = bot_settings['queue_display_length']
        self.default_prefix = bot_settings['default_prefix']

    def generate_np_embed(self, ctx, song: tuple):
        """
            Generates embed for "Now Playing" messages

        :param ctx:     Command Context
        :param song:    tuple:(song_title, playback_url, webpage_url, author of request, duration, thumbnail)
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Now Playing", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_image(url=song[5])
        embed.add_field(name="Song: ",
                        value=f"[{song[0]}]({song[2]})\n"
                              f"Duration - {math.floor(song[4] / 60)}:{str(math.floor(song[4] % 60)).rjust(2, '0')}",
                        inline=False)
        embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].display_avatar)
        return embed

    def generate_added_queue_embed(self, ctx, song):
        """
            Generates embed for "Added to Queue" messages

        :param ctx:     Command Context
        :param song:    tuple:(song_title, playback_url, webpage_url, author of request, duration, thumbnail)
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Added to Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        if type(song) == tuple:
            embed.add_field(name="Song: ", value=f"[{song[0]}]({song[2]})", inline=False)
            embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].display_avatar)
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
                embed.set_footer(text=f"Requested by {song[0][3].name}", icon_url=song[0][3].display_avatar)
        return embed

    def generate_display_queue(self, ctx, queue, page):
        """
            Generates embed for "Queue" messages

        :param ctx:     Command Context
        :param queue:   Server queue list
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        # Break queue into pages of length `queue_display_length`
        queue_pages = [queue[i:i + self.queue_display_length]
                       for i in range(0, len(queue), self.queue_display_length)]

        # Build message to display
        for count, song in enumerate(queue_pages[page]):
            # Embed link if song info is from youtube
            song_num = count + 1 + (1 * (page * self.queue_display_length))
            if type(song) == str:
                embed.add_field(name=f"{song_num}: ",
                                value=f"{song}",
                                inline=False)
            else:
                embed.add_field(name=f"{song_num}: ",
                                value=f"[{song[0]}]({song[2]})",
                                inline=False)

        embed.set_footer(text=f'Page {page+1}/{len(queue_pages)} --- {len(queue)} songs')

        return embed, len(queue_pages)

    def generate_invite(self, ctx):
        """
            Generate invite embed

        :param ctx:     Command Context
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Invite Link", url=self.invite_link, color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)

        embed.add_field(name=f"Copyable link:", value=f"{self.invite_link}", inline=False)

        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.display_avatar)

        return embed

    def generate_help(self, ctx, page):
        """
            Generate help embed

        :param ctx:     Command Context
        :param page:    Page to display
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Help",
                               description="<> - indicates a required argument\n"
                                           "[] - indicates an optional argument",
                               color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)

        # Generate list of command pages to be displayed excluding help, sort by name
        command_list = [i for i in list(self.bot.commands) if not i.name == 'help']
        command_list = sorted(command_list, key=lambda x: x.name)
        # Break command list into pages of length `queue_display_length`
        command_pages = [command_list[i:i+self.queue_display_length]
                         for i in range(0, len(command_list), self.queue_display_length)]

        # Display commands in embed
        for i in command_pages[page]:
            embed.add_field(name=f"{self.config.get_prefix(ctx, ctx)}{i.name} {i.usage}",
                            value=i.help,
                            inline=False)

        embed.set_footer(text=f'Page {page+1}/{len(command_pages)}')

        return embed, len(command_pages)

    def generate_new_server_embed(self, guild):
        """
            Generate new server embed

        :param guild:   nextcord Guild object
        :return:        nextcord Embed
        """
        embed = nextcord.Embed(title="Thanks for adding Tempo!", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)

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

        embed.set_image(url=self.bot.user.display_avatar)

        guild_icon = guild.icon
        if guild_icon:
            embed.set_footer(text=f"{self.bot.user.name} added to {guild.name}!", icon_url=guild_icon.url)
        else:
            embed.set_footer(text=f"{self.bot.user.name} added to {guild.name}!")

        return embed

    def generate_search_embed(self, ctx, results):
        """
            Generates search results embed

        :param ctx:         Discord Message Context
        :param results:     Search results from SongSearch:
                                results = list( tuple( title, url, duration, ui ), ... )
        :return:            Discord Embed
        """
        embed = nextcord.Embed(title="Select a Song to Play!", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        for count, result in enumerate(results):
            embed.add_field(name=f'Result {count + 1}',
                            value=f"[{result[0]}]({result[1]})\n"
                                  f"Duration: {result[2]}, Views: {result[3]}",
                            inline=False)

        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.display_avatar)

        return embed

    def generate_remove_embed(self, ctx, song):
        """
            Generates the embed to display a removed song from the queue

        :param ctx:     Discord Message Context
        :param song:    tuple:(song_title, playback_url, webpage_url, author of request, duration, thumbnail)
                        string of song title
        :return:        Discord Embed
        """
        embed = nextcord.Embed(title="Remove Song", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        if type(song) == str:
            embed.add_field(name=f"Remove from Queue?: ",
                            value=f"{song}",
                            inline=False)
        else:
            embed.add_field(name=f"Remove from Queue?: ",
                            value=f"[{song[0]}]({song[2]})",
                            inline=False)
            embed.set_image(url=song[5])
        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.display_avatar)
        return embed

    def generate_loop_embed(self, ctx, loop):
        """
            Generates response to loop command message
                Displays status of the loop setting

        :param ctx:     Discord Message Context
        :param loop:    Boolean
        :return:        Discord Embed
        """
        embed = nextcord.Embed(title='Loop', color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        message = 'Loop Enabled' if loop else 'Loop Disabled'
        embed.add_field(name='▬▬▬▬▬▬▬▬▬▬▬',
                        value=message,
                        inline=False)
        embed.set_footer(text=f'Generated by {ctx.message.author.name}', icon_url=ctx.message.author.display_avatar)
        return embed


if __name__ == "__main__":
    config_test = ConfigUtil()

    bot_settings = config_test.read_config("BOT_SETTINGS")
    server_settings = config_test.read_config("SERVER_SETTINGS")

    print(bot_settings, '\n')
    print("server: ", server_settings['138622532248010752'])
    print("prefix: ", server_settings['138622532248010752']['prefix'])
    print("loop: ", server_settings['138622532248010752']['loop'])
