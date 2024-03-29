------------------------------------------------------------------------------------------------------------------------
Music Bot

    Plays YouTube linked videos in discord voice channel

    Rewritten with Cogs!

------------------------------------------------------------------------------------------------------------------------

REQUIREMENTS

    - FFMpeg
    - cookies.txt with YouTube.com cookies in Netscape HTTP format

------------------------------------------------------------------------------------------------------------------------

FEATURES

    - Stream YouTube videos from a given link.
    - Display title of video with "Now Playing".
    - Queue songs in order they are posted.
    - Skip songs in queue.
    - Display Queue.
    - Clear Queue.
    - Search YouTube for a song.
    - Play YouTube Playlists.
    - Server independent, changeable prefixes.
    - Server independent song queues.
    - Embed messages for "Now Playing", "Added to Queue", and displaying the Queue.
    - Pause/Resume.
    - Invite command.
    - Custom help command.
    - Auto disconnect/Disconnect time-out.
    - Spotify, Soundcloud support
        NOTE: Songs added from an external playlist do not have links until background queue update runs.
    - Search for top 5 results on YT.
    - Shuffle queue.
    - Multi-skip.
    - Remove specific song in queue.
    - Loop.
    - Lyrics finder
    - Message purge
    - Easter egg

------------------------------------------------------------------------------------------------------------------------

KNOWN ISSUES

    - Connection loss attempts to restart extensions that are already loaded (console clutter, no effect on functionality)

------------------------------------------------------------------------------------------------------------------------

TO-DO LIST
    (Not ordered by priority)

    - Refactor bot for readability and efficiency.
    - Add support for slash commands.
    - Apple Music support. (web scraper? may not be possible without api access)

------------------------------------------------------------------------------------------------------------------------

FRAMEWORKS/LIBRARIES

    - nextcord
    - yt-dlp (formerly youtube_dl)
    - spotipy
    - soundcloud-lib
    - youtube-search-python
    - lyricsgenius
