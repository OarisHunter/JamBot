# LyricsParser.py
import os

import lyricsgenius

from dotenv import load_dotenv
from typing import List


class LyricsParser:
    def __init__(self):
        load_dotenv()
        self.genius = lyricsgenius.Genius(os.getenv('LYRICS_GENIUS_TOKEN'))

    def __find_lyrics(self, title: str, artist: str) -> List[str]:
        """
            Private function to get a list of lines in the track

        :param title:   Track title : str
        :param artist:  Track artist : str
        :return:        Lyric lines : List[str]
        """
        # search for song
        song = self.genius.search_song(title, artist)
        # Break song into lines
        line_list = [line for line in song.lyrics.split('\n') if line]

        # Clean up first and last line
        line_list[0] = '[Intro]' if '[Intro]' in line_list[0] else None
        line_list[-1] = line_list[-1].split('Embed')[0]

        return line_list

    def get_lyrics(self, title: str, artist: str) -> str:
        """
            Get lyrics in a formatted list style

        :param title:   Track title : str
        :param artist:  Track artist : str
        :return:        lyrics : str
        """
        line_list = self.__find_lyrics(title, artist)

        # Format result string
        result = ''.join(f'\t{line}\n'
                         if '[' not in line
                         else f'\n{line}\n'
                         for line in line_list)
        return result

    def get_lyrics_list(self, title: str, artist: str) -> List[str]:
        """
            Get a list containing each line in the lyrics (headers included)

        :param title:   Track title : str
        :param artist:  Track artist : str
        :return:        Lyric lines : List[str]
        """
        return self.__find_lyrics(title, artist)


if __name__ == '__main__':
    parser = LyricsParser()
    lyrics = parser.get_lyrics('godspeed', 'wage war')
    print(lyrics)
    lyrics_lines = parser.get_lyrics_list('godspeed', 'wage war')
    print(lyrics_lines)
