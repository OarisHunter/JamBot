# SongSearch.py

from lib.helpers.Utils import ConfigUtil
from youtube_search import YoutubeSearch


class SongSearch:
    def __init__(self):
        config = ConfigUtil().read_config('BOT_SETTINGS')
        self.queue_display_length = config['queue_display_length']

    def search_yt(self, keywords: str):
        """
            Searches youtube for top videos from listed keywords

        :param keywords:    User defined string of keywords to search for
        :return:            list(tuple(title, url, duration, views))
        """
        results = YoutubeSearch(keywords, max_results=self.queue_display_length).to_dict()
        return self.convert_results(results)

    def convert_results(self, results):
        """
            Converts YoutubeSearch output to readable format

        :param results:     YoutubeSearch dictionary
        :return:            list(tuple(title, url, duration, views))
        """
        return [self.result_to_tuple(i) for i in results]

    @staticmethod
    def result_to_tuple(result):
        """
            Converts dictionary entry from YoutubeSearch to a tuple

        :param result:  YoutubeSearch dict entry
        :return:        tuple(title, url, duration, views)
        """
        return (result['title'],
                "https://youtube.com" + result['url_suffix'],
                result['duration'],
                result['views'])
