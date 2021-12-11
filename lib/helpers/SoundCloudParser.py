class SoundcloudParser:
    """
        Soundcloud request parsing wrapper
    """

    def __init__(self, author):
        self.author = author
        self.utilities = Util()
        self.api = SoundcloudAPI()  # never pass a Soundcloud client ID that did not come from this library

    def parse_link(self, link):
        """
            Parses soundcloud link

        :param link:    Soundcloud link
        :return:        song info tuple
                            list[tuple("title artist", message author),...] if link was a playlist
                            downloaded song info from youtube if link was a track
        """
        response = self.api.resolve(link)

        song_info = None
        track_flag = False
        if type(response) == Playlist:
            song_info = [(f'{self.utilities.scrub_song_title(track.title)} {track.artist}', self.author)
                         for track in response]

        elif type(response) == Track:
            track = f'{self.utilities.scrub_song_title(response.title)} {response.artist}'
            song_info = Util().download_from_yt(track)
            song_info = song_info[0] if type(song_info) == list else song_info
            track_flag = True
        return song_info, track_flag
