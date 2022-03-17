# SpotifyParser.py

import spotipy
import os

from nextcord import Member
from typing import Union, List, Tuple
from lib.helpers.Utils import Util
from spotipy import SpotifyClientCredentials

class SpotifyParser:
    """
        Spotify request parsing wrapper
    """

    def __init__(self, author: Member):
        self.author = author
        self.utilities = Util()
        self.sp = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_CID'),
                                                                client_secret=os.getenv('SPOTIFY_SECRET')))

    def parse_link(self, link: str):
        """
            Wrapper to pass link to correct parsing type

        :param link:    spotify link string
        :return:        song info tuple and boolean for if link was a track
        """
        song_info = None
        is_track = False
        # Check for track or playlist link
        if 'playlist' in link:
            song_info = self.parse_playlist(link)

        elif 'album' in link:
            # Get album from album id
            song_info = self.parse_album(link)

        elif 'track' in link:
            song_info = self.parse_track(link)
            is_track = True
        return song_info, is_track

    def parse_playlist(self, link: str) -> List[Tuple[str, Member]]:
        """
            Parses spotify playlist

        :param link:    Spotify link
        :return:        list[tuple(title, message author),...]
        """
        offset = 0
        result = []
        while offset < self.sp.playlist_items(link, fields='total')['total']:
            response = self.sp.playlist_items(link,
                                              offset=str(offset),
                                              fields='items.track.name, items.track.album.artists',
                                              additional_types=['track'])
            for x in response['items']:
                if x['track']['name']:
                    title = self.utilities.scrub_song_title(x['track']['name'])
                    if x['track']['album']['artists']:
                        artist = x['track']['album']['artists'][0]['name']
                    else:
                        artist = 'song'
                    result.append((f'{title} {artist}', self.author))
            offset = offset + len(response['items'])
        return result

    def parse_album(self, link: str) -> List[Tuple[str, Member]]:
        """
            Parses spotify album

        :param link:    Spotify link
        :return:        list[tuple(title, message author),...]
        """
        response = self.sp.album(link)
        result = []
        for x in response['tracks']['items']:
            if x['name']:
                title = self.utilities.scrub_song_title(x['name'])
                if x['artists']:
                    artist = x['artists'][0]['name']
                else:
                    artist = 'song'
                result.append((f'{title} {artist}', self.author))
        return result

    def parse_track(self, link: str) -> dict:
        """
            Parses spotify track

        :param link:    Spotify link
        :return:        downloaded song info from youtube dl
        """
        response = self.sp.track(link)
        if response['name']:
            title = self.utilities.scrub_song_title(response['name'])
            if response['album']['artists']:
                artist = response['album']['artists'][0]['name']
            else:
                artist = 'song'
            song_info = Util().download_from_yt(f'{title} {artist}')
            return song_info[0] if type(song_info) == list else song_info

    def artist_search(self, query: str) -> List[Tuple[str, str]]:
        response = self.sp.search(q=query, type='artist', limit=5)
        results = [(artist['name'], artist['uri'].split(':')[2]) for artist in response['artists']['items']]
        return results

    def get_artist_top_tracks(self, artist_uri: str) -> List[Tuple[str, Member]]:
        response = self.sp.artist_top_tracks(artist_uri, country='US')
        return [(f"{self.utilities.scrub_song_title(track['name'])} {track['artists'][0]['name']}",
                 self.author)
                for track in response['tracks']]

    def get_artist_all_tracks(self, artist_uri: str) -> List[Tuple[str, Member]]:
        response = self.sp.artist_albums(artist_uri, album_type='album,single', limit=50, country='US')
        return [(f"{self.utilities.scrub_song_title(album_track['name'])} {album_track['artists'][0]['name']}",
                 self.author)
                for album in response['items']
                for album_track in self.sp.album_tracks(album['uri'].split(':')[2], limit=50)['items']]
