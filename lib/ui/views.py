# views.py

import nextcord

from lib.helpers import Utils


class SearchView(nextcord.ui.View):
    """
        View for search command

        Creates buttons based on config defined queue display length
    """

    def __init__(self):
        super().__init__()
        config = Utils.ConfigUtil().read_config('BOT_SETTINGS')
        self.queue_display_length = config['queue_display_length']
        self.value = None

        # Create buttons on object creation
        self.add_buttons()

    def add_buttons(self):
        """
            Dynamically create buttons to choose a song from search command embed

        :return:    None
        """
        button_list = [nextcord.ui.Button(label=str(i + 1), style=nextcord.ButtonStyle.gray, custom_id=str(i))
                       for i in range(self.queue_display_length)]
        for i in button_list:
            self.add_item(i)

    async def interaction_check(self, interaction):
        """
            Overwrites method from super class
            Gets custom id of clicked button and stops view to allow command to continue

        :param interaction:     Discord Interaction
        :return:                None
        """
        self.value = int(interaction.data['custom_id'])
        self.stop()

class PageView(nextcord.ui.View):
    """
        Discord View that supplies page buttons to children classes.
    """
    def __init__(self, bot, ctx, timeout):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Utils.Embeds(bot)

    @nextcord.ui.button(label='<<', style=nextcord.ButtonStyle.gray)
    async def first_(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """
            Button to switch to first page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = 0
        await self.update_message()

    @nextcord.ui.button(label='<', style=nextcord.ButtonStyle.gray)
    async def prev_(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """
            Button to switch to previous page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = (self.current_page - 1) % self.num_pages
        await self.update_message()

    @nextcord.ui.button(label='>', style=nextcord.ButtonStyle.gray)
    async def next_(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """
            Button to switch to next page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = (self.current_page + 1) % self.num_pages
        await self.update_message()

    @nextcord.ui.button(label='>>', style=nextcord.ButtonStyle.gray)
    async def last_(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """
            Button to switch to last page

        :param button:      nextcord.ui.Button object
        :param interaction: nextcord.Interaction object
        :return:            None
        """
        self.current_page = self.num_pages - 1
        await self.update_message()

    async def create_message(self):
        """
            Creates a starting message, must be overwritten

        :return:    None
        """
        pass

    async def update_message(self):
        """
            Updates message with new page, must be overwritten

        :return:    None
        """
        pass

    async def on_timeout(self):
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
        self.embeds = Utils.Embeds(bot)

    async def create_message(self):
        """
            Creates a starting help message

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_help(self.ctx, self.current_page)
        self.message = await self.ctx.channel.send(embed=embed,
                                                   view=self)

    async def update_message(self):
        """
            Updates message with new page

        :return:    None
        """
        embed, _ = self.embeds.generate_help(self.ctx, self.current_page)
        await self.message.edit(embed=embed,
                                view=self)

class QueueView(PageView):
    """
        Discord View to generate the queue message and create a UI, displays commands in a page format.
    """
    def __init__(self, bot, ctx, queue, timeout):
        super().__init__(bot, ctx, timeout=timeout)
        self.ctx = ctx
        self.num_pages = 0
        self.current_page = 0
        self.message = None
        self.embeds = Utils.Embeds(bot)
        self.queue = queue

    async def create_message(self):
        """
            Creates a starting queue message

        :return:    None
        """
        embed, self.num_pages = self.embeds.generate_display_queue(self.ctx, self.queue, self.current_page)
        self.message = await self.ctx.channel.send(embed=embed,
                                                   view=self)

    async def update_message(self):
        """
            Updates message with new page

        :return:    None
        """
        embed, _ = self.embeds.generate_display_queue(self.ctx, self.queue, self.current_page)
        await self.message.edit(embed=embed,
                                view=self)
