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
        button_list = [nextcord.ui.Button(label=str(i+1), style=nextcord.ButtonStyle.gray, custom_id=str(i))
                       for i in range(self.queue_display_length)]
        for i in button_list:
            self.add_item(i)

    async def interaction_check(self, interaction):
        """
            Gets custom id of clicked button and stops view to allow command to continue

        :param interaction:     Discord Interaction
        :return:                None
        """
        self.value = int(interaction.data['custom_id'])
        self.stop()
