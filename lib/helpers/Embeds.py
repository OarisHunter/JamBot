# Embeds.py

import math

from nextcord import Embed
from lib.helpers.Utils import ConfigUtil
from lib.helpers.Utils import Util


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
        embed = Embed(title="Now Playing", color=self.embed_theme)
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
        embed = Embed(title="Added to Queue", color=self.embed_theme)
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
                if len(i) == 2:
                    embed.add_field(name=f"{count + 1}: ", value=f"{i[0]}", inline=False)
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
        :param page:    page of queue to display
        :return:        nextcord Embed
        """
        embed = Embed(title="Queue", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        # Break queue into pages of length `queue_display_length`
        queue_pages = [queue[i:i + self.queue_display_length]
                       for i in range(0, len(queue), self.queue_display_length)]

        # Build message to display
        for count, song in enumerate(queue_pages[page]):
            # Embed link if song info is from youtube
            song_num = count + 1 + (1 * (page * self.queue_display_length))
            if len(song) == 2:
                embed.add_field(name=f"{song_num}: ",
                                value=f"{song[0]}",
                                inline=False)
            else:
                embed.add_field(name=f"{song_num}: ",
                                value=f"[{song[0]}]({song[2]})",
                                inline=False)

        embed.set_footer(text=f'Page {page + 1}/{len(queue_pages)} '
                              f'--- '
                              f'{len(queue)} songs '
                              f'--- '
                              f'Total Duration: {self.utilities.calculate_duration(queue)}')

        return embed, len(queue_pages)

    def generate_invite(self, ctx):
        """
            Generate invite embed

        :param ctx:     Command Context
        :return:        nextcord Embed
        """
        embed = Embed(title="Invite Link", url=self.invite_link, color=self.embed_theme)
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
        embed = Embed(title="Help",
                      description="<> - indicates a required argument\n"
                                  "[] - indicates an optional argument",
                      color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)

        # Generate list of command pages to be displayed excluding help, sort by name
        command_list = [i for i in list(self.bot.commands) if not i.name == 'help']
        command_list = sorted(command_list, key=lambda x: x.name)
        # Break command list into pages of length `queue_display_length`
        command_pages = [command_list[i:i + self.queue_display_length]
                         for i in range(0, len(command_list), self.queue_display_length)]

        # Display commands in embed
        for i in command_pages[page]:
            embed.add_field(name=f"{self.config.get_prefix(ctx, ctx)}{i.name} {i.usage}",
                            value=i.help,
                            inline=False)

        embed.set_footer(text=f'Page {page + 1}/{len(command_pages)}')

        return embed, len(command_pages)

    def generate_new_server_embed(self, guild):
        """
            Generate new server embed

        :param guild:   nextcord Guild object
        :return:        nextcord Embed
        """
        embed = Embed(title="Thanks for adding Tempo!", color=self.embed_theme)
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
        embed = Embed(title="Select a Song to Play!", color=self.embed_theme)
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
        embed = Embed(title="Remove Song", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        if len(song) == 2:
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
        embed = Embed(title='Loop', color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        message = 'Loop Enabled' if loop else 'Loop Disabled'
        embed.add_field(name='▬▬▬▬▬▬▬▬▬▬▬',
                        value=message,
                        inline=False)
        embed.set_footer(text=f'Generated by {ctx.message.author.name}', icon_url=ctx.message.author.display_avatar)
        return embed

    def generate_mix_embed(self, ctx, results):
        """
            Generates response to mix command message

        :param ctx:         Discord message context
        :param results:     List of artists for the user to choose from
        :return:            Discord Embed
        """
        embed = Embed(title='Loop', color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        for count, result in enumerate(results):
            embed.add_field(name=f'Artist {count + 1}',
                            value=f"{result[0]}",
                            inline=False)

        embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.display_avatar)

        return embed

    def generate_lyrics(self, ctx, lyrics, title, artist, page):
        """
            Generates embed for "Queue" messages

        :param ctx:     Command Context: Context
        :param lyrics:  Lyrics lines list: List[str]
        :param title:   track title: str
        :param artist:  track artist: str
        :param page:    page of queue to display: int
        :return:        nextcord Embed: Embed
        """
        embed = Embed(title="Lyrics", color=self.embed_theme)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        # Break lyrics into pages
        lyrics.append('[end]')
        lyrics_pages = []
        lyrics_page = []
        for line in range(len(lyrics)):
            if '[end]' == lyrics[line + 1]:
                break
            elif '[' and ']' in lyrics[line + 1]:
                lyrics_page.append(lyrics[line])
                lyrics_pages.append(lyrics_page)
                lyrics_page = []
            else:
                lyrics_page.append(lyrics[line])

        # Build message to display
        embed.add_field(name=''.join(word.capitalize() for word in title),
                        value=''.join(word.capitalize() for word in artist),
                        inline=False)

        embed.add_field(name=f"{lyrics_pages[page][0]}",
                        value=''.join(f'{line}\n' for line in lyrics_pages[page][1:]),
                        inline=False)

        embed.set_footer(text=f'Page {page + 1}/{len(lyrics_pages)}')

        return embed, len(lyrics_pages)

    def doom_embed(self, ctx):
        """
            Generates response to DOOM command

        :param ctx:     Discord message context
        :return:        Discord Embed
        """
        embed = Embed(title='DOOM', color=self.embed_theme)
        embed.set_thumbnail(url="https://i1.sndcdn.com/avatars-7EKbPp1OVrlDMLIc-ou0k0g-t240x240.jpg")

        embed.add_field(name="Rip & Tear",
                        value="Until it is done.",
                        inline=False)
        embed.set_footer(text=f'{ctx.message.author.name} is loading their shotgun...',
                         icon_url=ctx.message.author.display_avatar)
        return embed

    def broken_embed(self):
        """
            Generates a message to notify user that bot is down

        :return:    Discord Embed
        """
        embed = Embed(title='We\'re Sorry...', color=self.embed_theme)
        embed.add_field(name="Tempo is down",
                        value="Something is broken...\n"
                              "We're working on fixing it, stay tuned!",
                        inline=False)
        embed.set_footer(text=f"{self.bot.user.name} is under maintenance", icon_url=self.bot.user.display_avatar)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        return embed
