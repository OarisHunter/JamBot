# SongSearch.py

import nextcord
import asyncio

from lib.helpers.Utils import Util, Embeds, ConfigUtil
from youtube_search import YoutubeSearch


class SongSearch:
    def __init__(self):
        config = ConfigUtil().read_config('BOT_SETTINGS')
        self.queue_display_length = config['queue_display_length']

    def search_yt(self, keywords: str):
        results = YoutubeSearch(keywords, max_results=self.queue_display_length).to_dict()
        return self.convert_results(results)

    def convert_results(self, results):
        return [self.result_to_tuple(i) for i in results]

    @staticmethod
    def result_to_tuple(result):
        return (result['title'],
               "https://youtube.com" + result['url_suffix'],
                result['duration'],
                result['views'])