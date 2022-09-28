# views.py

import nextcord

from typing import List, Any
from nextcord import Interaction, ui
from nextcord.ext.commands import Bot, Context
from lib.helpers.Utils import ConfigUtil
from lib.helpers.Embeds import Embeds


class ConfirmView(nextcord.ui.View):
    """
        View for Confirm/Cancel responses

        Creates confirm and cancel buttons
    """
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.value = None

    @nextcord.ui.button(label='Confirm', style=nextcord.ButtonStyle.green)
    async def confirm_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to Confirm option

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.value = True
        self.stop()

    @nextcord.ui.button(label='Cancel', style=nextcord.ButtonStyle.red)
    async def cancel_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to Cancel option

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.value = False
        self.stop()

    async def on_timeout(self) -> None:
        """
            Deletes message and returns to command call

        :return:    None
        """
        self.stop()
    

class Dropdown(nextcord.ui.Select):
    """
        Base nextcord select based dropdown
    """
    def __init__(self, placeholder):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=[])
        self.selected = None

    async def callback(self, interaction: Interaction):
        """
            updates selected value

        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.selected = self.values[0]

class PurgeView(nextcord.ui.View):
    """
        view for dropdown select menus
    """
    def __init__(self, bot: Bot, ctx: Context, options: List[Any], placeholder: str = "Select an option", timeout: int = 10):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.options = options
        self.message = None

        self.dropdown = Dropdown(placeholder=placeholder)
        self.value = None

    async def create_message(self) -> None:
        """
            Creates a starting message

        :return:    None
        """
        for index, item in enumerate(self.options):
            self.dropdown.add_option(label=item[1], value=str(index))
        self.add_item(self.dropdown)
        self.message = await self.ctx.channel.send(view=self)

    @nextcord.ui.button(label="Select", row=4)
    async def button_(self, button: nextcord.Button, interaction: Interaction):
        """
            Confirm selection button

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.value = int(self.dropdown.selected)
        await self.message.delete()
        self.stop()

    async def on_timeout(self) -> None:
        """
            Deletes message and returns to command call

        :return:    None
        """
        self.value = int(self.dropdown.selected)
        await self.message.delete()
        self.stop()


class PageView(nextcord.ui.View):
    """
        Discord View that supplies page buttons to children classes.
    """
    def __init__(self, bot: Bot, ctx: Context, timeout: int):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Embeds(bot)

    @nextcord.ui.button(label='<<', style=nextcord.ButtonStyle.gray)
    async def first_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to switch to first page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = 0
        await self.update_message()

    @nextcord.ui.button(label='<', style=nextcord.ButtonStyle.gray)
    async def prev_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to switch to previous page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = (self.current_page - 1) % self.num_pages
        await self.update_message()

    @nextcord.ui.button(label='>', style=nextcord.ButtonStyle.gray)
    async def next_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to switch to next page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = (self.current_page + 1) % self.num_pages
        await self.update_message()

    @nextcord.ui.button(label='>>', style=nextcord.ButtonStyle.gray)
    async def last_(self, button: ui.Button, interaction: Interaction) -> None:
        """
            Button to switch to last page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = self.num_pages - 1
        await self.update_message()

    async def create_message(self) -> None:
        """
            Creates a starting message, must be overwritten

        :return:    None
        """
        pass

    async def update_message(self) -> None:
        """
            Updates message with new page, must be overwritten

        :return:    None
        """
        pass

    async def on_timeout(self) -> None:
        """
            Deletes message and returns to command call

        :return:    None
        """
        await self.message.delete()
        self.stop()


class HelpView(PageView):
    """
        Discord View to generate the help command and create a UI, displays commands in a page format.
    """
    def __init__(self, bot, ctx, timeout):
        super().__init__(bot, ctx, timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Embeds(bot)

    async def create_message(self) -> None:
        """
            Creates a starting help message

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_help(self.ctx, self.current_page)
        self.message = await self.ctx.channel.send(embed=embed,
                                                   view=self)

    async def update_message(self) -> None:
        """
            Updates message with new page

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_help(self.ctx, self.current_page)
        await self.message.edit(embed=embed,
                                view=self)


class QueueView(PageView):
    """
        Discord View to generate the queue message and create a UI, displays commands in a page format.
    """
    def __init__(self, bot: Bot, ctx: Context, queue: list, timeout: int):
        super().__init__(bot, ctx, timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Embeds(bot)
        self.queue = queue

    async def create_message(self) -> None:
        """
            Creates a starting queue message

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_display_queue(self.ctx, self.queue, self.current_page)
        self.message = await self.ctx.channel.send(embed=embed,
                                                   view=self)

    async def update_message(self) -> None:
        """
            Updates message with new page

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_display_queue(self.ctx, self.queue, self.current_page)
        await self.message.edit(embed=embed,
                                view=self)


class LyricsView(PageView):
    def __init__(self, bot: Bot, ctx: Context, lyrics: list, title: str, artist: str, timeout: int):
        super().__init__(bot, ctx, timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Embeds(bot)
        self.lyrics = lyrics
        self.title = title
        self.artist = artist

    async def create_message(self) -> None:
        """
            Creates a starting queue message

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_lyrics(self.ctx, self.lyrics, self.title, self.artist, self.current_page)
        self.message = await self.ctx.channel.send(embed=embed,
                                                   view=self)

    async def update_message(self) -> None:
        """
            Updates message with new page

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_lyrics(self.ctx, self.lyrics, self.title, self.artist, self.current_page)
        await self.message.edit(embed=embed,
                                view=self)


class SearchView(nextcord.ui.View):
    """
        View for search command

        Creates buttons based on config defined queue display length
    """

    def __init__(self):
        super().__init__()
        config = ConfigUtil().read_config('BOT_SETTINGS')
        self.queue_display_length = config['queue_display_length']
        self.value = None

        # Create buttons on object creation
        self.add_buttons()

    def add_buttons(self) -> None:
        """
            Dynamically create buttons to choose a song from search command embed

        :return:    None
        """
        button_list = [nextcord.ui.Button(label=str(i + 1), style=nextcord.ButtonStyle.gray, custom_id=str(i))
                       for i in range(self.queue_display_length)]
        for i in button_list:
            self.add_item(i)

    async def interaction_check(self, interaction: Interaction) -> None:
        """
            Overwrites method from super class
            Gets custom id of clicked button and stops view to allow command to continue

        :param interaction:     Discord Interaction: Interaction
        :return:                None
        """
        self.value = int(interaction.data['custom_id'])
        self.stop()
