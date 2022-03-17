# SongSearch.py

from typing import Tuple, List
from lib.helpers.Utils import ConfigUtil
from youtube_search import YoutubeSearch


class SongSearch:
    def __init__(self):
        config = ConfigUtil().read_config('BOT_SETTINGS')
        self.queue_display_length = config['queue_display_length']

    def search_yt(self, keywords: str) -> List[Tuple[str, str, str, str]]:
        """
            Searches youtube for top videos from listed keywords

        :param keywords:    User defined string of keywords to search for: str
        :return:            list(tuple(title, url, duration, views)): List[Tuple[str, str, str, str]]
        """
        results = YoutubeSearch(keywords, max_results=self.queue_display_length).to_dict()
        return self.convert_results(results)

    def convert_results(self, results: dict) -> List[Tuple[str, str, str, str]]:
        """
            Converts YoutubeSearch output to readable format

        :param results:     YoutubeSearch dictionary: dict
        :return:            list(tuple(title, url, duration, views)): List[Tuple[str, str, str, str]]
        """
        return [self.result_to_tuple(i) for i in results]

    @staticmethod
    def result_to_tuple(result: dict) -> Tuple[str, str, str, str]:
        """
            Converts dictionary entry from YoutubeSearch to a tuple

        :param result:  YoutubeSearch dict entry: dict
        :return:        tuple(title, url, duration, views): Tuple[str, str, str, str]
        """
        return (result['title'],
                "https://youtube.com" + result['url_suffix'],
                result['duration'],
                result['views'])
