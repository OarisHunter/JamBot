# musicBot.py

"""
Music Bot

    Plays YouTube linked videos in discord voice channel

@author: Pierce Thompson
"""

import ast
import os
import asyncio
import youtube_dl
import spotipy

from discord.ext import commands
from spotipy import SpotifyClientCredentials
from sclib import SoundcloudAPI, Track, Playlist
from helpers.BotEmbeds import *
from dotenv import load_dotenv
from configparser import ConfigParser

# Create member vars
TEST_MODE = False
default_prefix = "~"
server_queues = {}
test_song = ""
ydl_opts = {}
ffmpeg_opts = {}
queue_display_length = 5
embed_theme = discord.Color.dark_gold()
invite_link = ""


def get_prefix(client, message):
    """
        Get prefixes from config.ini
    """
    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_prefixes = config_object["PREFIXES"]
    # in DM messages force default prefix
    if not message.guild:
        return default_prefix
    return bot_prefixes[str(message.guild.id)]


# Create Bot
load_dotenv()
if TEST_MODE:
    TOKEN = os.getenv('TEST_TOKEN')
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="`", intents=intents, help_command=None)
else:
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
# SoundCloud API
soundcloud = SoundcloudAPI()
# Spotify API
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_CID'),
                                                                              client_secret=os.getenv('SPOTIFY_SECRET')
                                                                              ))
# Bot command / control extentsions
extensions = [
    'cogs.commands',
    'cogs.events'
]

if __name__ == '__main__':
    for extension in extensions:
        bot.load_extension(extension)


@bot.event
async def on_ready():
    """
        Called when bot start-up has finished
    """
    try:
        # Start-up messages
        print("Music Bot is Ready!")
        read_config()
        print("Read bot settings from Config!")
        for guild in bot.guilds:
            print(f"\t{bot.user.name} has connected to {guild.owner.name}'s server | {guild.name} |")

        # Generate song queues
        create_server_queue()

    except discord.DiscordException:
        print("on_ready event failed.")


# -------------- Commands ------------- #
@bot.command(name='play', help='Connects Bot to Voice')
async def play_(ctx, *link):
    """
        Command to connect to voice
            plays song
                from yt link
                from yt search
                from yt playlist link
    """
    await ctx.message.delete(delay=5)

    # Check that author is in a voice channel
    if ctx.author.voice is None:
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    # Convert command args to string
    # allows for multi word song searches
    link = tuple_to_string(link)

    # Pass link to parser to determine origin
    song_info, from_youtube = await extract_song_info(ctx, link)

    # Check that author is in a voice channel
    if ctx.author.voice is not None:
        try:
            # Connect to channel of author
            vc = await ctx.author.voice.channel.connect()
        except discord.DiscordException:
            # Catch error if already connected
            vc = ctx.guild.voice_client
    else:
        print(f"Play: Bot not connected to {ctx.guild.name}")
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    if song_info:
        # Add song(s) to queue from song info
        await add_song_to_queue(ctx, song_info, from_youtube=from_youtube)

        # Play song if not playing a song
        if not vc.is_playing():
            await play_music_(ctx)


@bot.command(name='skip', help='Skips to next Song in Queue')
async def skip_(ctx):
    """
        Command to skip currently playing song
    """
    try:
        await ctx.message.delete(delay=5)

        vc = ctx.guild.voice_client  # Get current voice client

        if vc is None:
            print(f"Skip: Bot not connected to {ctx.guild.name}")
            return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

        # Check that there is another song in the queue and the bot is currently playing
        song_queue = get_queue(ctx.guild.id)
        if len(song_queue) > 1 and vc.is_playing():
            # Pop currently playing off queue
            song_queue.pop(0)

            # Update Voice Client source
            try:
                vc.source = discord.FFmpegPCMAudio(song_queue[0][1], **ffmpeg_opts)
                vc.source = discord.PCMVolumeTransformer(vc.source)
                vc.volume = 1
            except discord.errors.ClientException:
                print(f"ClientException: Failed to Play Song in {ctx.guild.name}")

            # Display now playing message
            await ctx.channel.send("**Skipped a Song!**", delete_after=10)
            await ctx.invoke(bot.get_command('np'))
        else:
            vc.stop()
            await ctx.channel.send("**Skipped a Song!**", delete_after=10)

    except discord.DiscordException:
        pass


@bot.command(name='clear', help='Clears the Song Queue')
async def clear_(ctx):
    """
        Command to clear server's Queue
    """
    try:
        await ctx.message.delete(delay=5)

        # Empty the queue
        get_queue(ctx.guild.id).clear()

        # Send response
        await ctx.channel.send("**Cleared the Queue!**", delete_after=20)

    except discord.DiscordException:
        pass


@bot.command(name='queue', help='Displays the Queue')
async def queue_(ctx):
    """
        Command to display songs in server's Queue
    """
    try:
        await ctx.message.delete(delay=5)

        song_queue = get_queue(ctx.guild.id)
        if song_queue:
            embed = generate_display_queue(ctx, song_queue, bot, embed_theme, queue_display_length)

            await ctx.channel.send(embed=embed, delete_after=60)
        else:
            await ctx.channel.send("**Queue is empty!**", delete_after=10)

    except discord.DiscordException:
        pass


@bot.command(name='np', help='Displays the currently playing song')
async def nowPlaying_(ctx):
    """
        Command to display "Now Playing" message
    """
    try:
        await ctx.message.delete(delay=5)

        vc = ctx.message.guild.voice_client
        song_queue = get_queue(ctx.guild.id)
        if vc and vc.is_playing():
            print(f"Now Playing {song_queue[0][0]} in {ctx.author.voice.channel.name} of {ctx.guild.name}")
            # await ctx.channel.send(f'**Now Playing**\n\n{song_queue[0][0]}', delete_after=10)
            await ctx.channel.send(embed=generate_np_embed(ctx, song_queue[0], bot, embed_theme))
        else:
            print(f'NowPlaying: Not in a Voice Channel in {ctx.guild.name}')
            await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    except discord.DiscordException:
        pass


@bot.command(name='pause', help='Pauses currently playing song')
async def pause_(ctx):
    """
        Pauses music to be resumed later
    """
    try:
        await ctx.message.delete(delay=5)

        vc = ctx.guild.voice_client

        if vc.is_connected() and vc.is_playing():
            vc.pause()
            await ctx.channel.send(f'**Music Paused!**', delete_after=10)
        elif vc.is_connected() and vc.is_paused():
            await ctx.channel.send(f'Already Paused', delete_after=10)
        elif vc.is_connected() and not vc.is_playing():
            await ctx.channel.send(f'Not Playing Anything', delete_after=10)
        else:
            await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)

    except discord.DiscordException:
        pass


@bot.command(name='resume', help='Resumes currently playing song')
async def resume_(ctx):
    """
        Resumes paused music
    """
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    vc = ctx.guild.voice_client

    if vc.is_connected() and vc.is_paused():
        vc.resume()
        await ctx.channel.send(f'**Music Resumed!**', delete_after=10)
    elif vc.is_connected() and vc.is_playing():
        await ctx.channel.send(f'Already Playing', delete_after=10)
    elif vc.is_connected() and not vc.is_paused():
        await ctx.channel.send(f'Not Playing Anything', delete_after=10)
    else:
        await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)


@bot.command(name='disconnect', help='Disconnects from Voice')
async def disconnect_(ctx):
    """
        Command to disconnect bot from voice
    """
    try:
        vc = ctx.guild.voice_client

        # Check that the bot is connected to voice
        if vc and vc.is_connected():
            await vc.disconnect()

        await ctx.message.delete()

    except discord.DiscordException:
        pass


@bot.command(name='prefix', help='Changes prefix for this server')
@commands.has_permissions(administrator=True)
async def prefix_(ctx, *prefix):
    """
        Command to change/display server defined prefix
    """
    # Parse Config, get server prefixes
    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_prefixes = config_object["PREFIXES"]

    # If a prefix was given, change the prefix, otherwise display the current prefix
    if prefix and len(prefix) < 2:
        bot_prefixes[str(ctx.guild.id)] = str(''.join(prefix))

        # Update config file
        with open('config.ini', 'w') as conf:
            config_object.write(conf)

        await ctx.channel.send(f'Prefix for {ctx.guild.name} has been changed to: {bot_prefixes[str(ctx.guild.id)]}',
                               delete_after=10)
    else:
        await ctx.channel.send(f'Prefix for {ctx.guild.name} is: {bot_prefixes[str(ctx.guild.id)]}', delete_after=10)


@bot.command(name='invite', help='Shows invite link to add bot to your server')
async def invite_(ctx):
    """
        Sends an embed with invite links to add bot to other servers.
    """
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    await ctx.channel.send(embed=generate_invite(ctx, bot, embed_theme, invite_link))


@bot.command(name='help')
async def help_(ctx):
    """
        Custom help command
    """
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    await ctx.channel.send(embed=generate_help(ctx, bot, embed_theme, get_prefix))


# --------------- Events -------------- #
@bot.event
async def on_voice_state_update(member, before, after):
    """
        Disconnects bot if it is alone in a voice channel
    """
    try:
        # Check if bot is alone in channel, disconnect it if so
        bot_channel = member.guild.voice_client.channel
        if bot_channel is not None:
            members = bot_channel.members
            if bot.user in members and len(members) == 1:
                # Disconnect bot
                await member.guild.voice_client.disconnect()

    except AttributeError:
        pass


@bot.event
async def on_guild_join(guild):
    """
        Removes guild id and stored prefix from config.ini
    """
    # Parse Config, get server prefixes
    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_prefixes = config_object["PREFIXES"]

    # Set prefix of new server to default prefix
    bot_prefixes[str(guild.id)] = default_prefix

    # Update server queues
    create_server_queue()

    print(f"{bot.user.name} added to {guild.name}!")
    # try:
    await guild.system_channel.send(embed=generate_new_server_embed(guild, bot, embed_theme))
    # except discord.DiscordException:
    #     print(f"Couldn't send new server message in {guild.name}")

    # Update config file
    with open('config.ini', 'w') as conf:
        config_object.write(conf)


@bot.event
async def on_guild_remove(guild):
    """
        Removes guild id and stored prefix from config.ini
    """
    # Parse Config, get server prefixes
    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_prefixes = config_object["PREFIXES"]

    # remove server's prefix from config
    bot_prefixes.pop(str(guild.id))

    # Update server queues
    create_server_queue()

    print(f"{bot.user.name} removed from {guild.name}")

    # Update config file
    with open('config.ini', 'w') as conf:
        config_object.write(conf)


# -------------- Functions ------------- #
async def extract_song_info(ctx, link):
    """
        Directs link to proper parse method

        Support for Apple, SoundCloud, Spotify, and YT

        returns song_info : Tuple, List, flag for if info is from youtube
    """
    song_info = None
    from_youtube = True
    if "https://music.apple.com" in link:
        await ctx.channel.send("**Apple Music support coming soon!**", delete_after=20)
    elif "https://open.spotify.com" in link:
        await ctx.channel.send("**Spotify Link!** This may take a moment...", delete_after=20)
        song_info, from_youtube = await spotify_to_yt_dl(ctx, link)
    elif "https://soundcloud.com" in link:
        await ctx.channel.send("**SoundCloud Link!** This may take a moment...", delete_after=20)
        song_info, from_youtube = await soundcloud_to_yt_dl(ctx, link)
    else:
        song_info = await download_from_yt(ctx, link)
    return song_info, from_youtube


def tuple_to_string(tup):
    """
        Converts an indeterminate length tuple to a string
    """
    temp = ""
    for i in tup:
        temp += i + " "
    return temp.strip()


def create_server_queue():
    """
        Generate song queues for all servers
            Non-Queue destructive
    """
    # Loop through guilds bot is in
    for guild in bot.guilds:
        # Get guild id
        g_id = str(guild.id)
        # Add guild id to queue dict
        if g_id not in server_queues:
            server_queues[g_id] = []


def get_queue(guild_id):
    """
        Get Server Queue from Queue Dict
    """
    return server_queues[str(guild_id)]


def add_queue(guild_id, song_set):
    """
        Add song to Server Queue in Queue Dict
    """
    if type(song_set) == list:
        [server_queues[str(guild_id)].append(i) for i in song_set]
    else:
        server_queues[str(guild_id)].append(song_set)


def song_info_to_tuple(song_info, ctx):
    """
        Extract info from song_info into song tuple
        song = tuple:(string:title,
                          string:url,
                          string:web_page,
                          string:ctx.message.author,
                          int:duration,
                          string:thumbnail)
    """
    title = song_info['title']
    url = song_info["formats"][0]["url"]
    web_page = song_info['webpage_url']
    duration = song_info['duration']
    thumbnail = song_info["thumbnails"][-1]['url']
    return title, url, web_page, ctx.message.author, duration, thumbnail


async def add_song_to_queue(ctx, song_info, from_youtube=True):
    """
        Add song(s) to queue

        If a song is from youtube, its song info should added to the queue from youtube in the following format
            song = tuple:(string:title,
                          string:url,
                          string:web_page,
                          string:ctx.message.author,
                          int:duration,
                          string:thumbnail)
        If a song is from another source (Spotify, Soundcloud, etc.), the its song info should added to the queue from
        youtube in the following format
            song = "{song title} {artist}"

            The song will then be downloaded from youtube when it is played.
            NOTE: this means the song webpage/thumbnail url will not be available until then
    """
    if from_youtube:
        # If link was a playlist, loop through list of songs and add them to the queue
        if type(song_info) == list:
            song_list = [song_info_to_tuple(i, ctx) for i in song_info]
            add_queue(ctx.guild.id, song_list)
            if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
                await ctx.channel.send(
                    embed=generate_added_queue_embed(ctx, song_list, bot, embed_theme, queue_display_length),
                    delete_after=40)
        # Otherwise add the single song to the queue, display message if song was added to the queue
        else:
            # Generate song tuple
            song = song_info_to_tuple(song_info, ctx)

            # Display added to queue if queue is not empty
            if len(get_queue(ctx.guild.id)) >= 1:
                await ctx.channel.send(
                    embed=generate_added_queue_embed(ctx, song, bot, embed_theme, queue_display_length),
                    delete_after=40)

            # add song to queue for playback
            add_queue(ctx.guild.id, song)
    else:
        # Create song list, add songs to server queue, display message
        song_list = [i for i in song_info]
        add_queue(ctx.guild.id, song_list)
        if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
            await ctx.channel.send(
                embed=generate_added_queue_embed(ctx, song_list, bot, embed_theme, queue_display_length),
                delete_after=40)


def read_config():
    """
        Get server options from config.ini
    """
    global test_song, ydl_opts, ffmpeg_opts, invite_link

    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_settings = config_object["BOT_SETTINGS"]
    test_song = bot_settings["test_song"]
    ydl_opts = ast.literal_eval(bot_settings["ydl_opts"])
    ffmpeg_opts = ast.literal_eval(bot_settings["ffmpeg_opts"])
    invite_link = bot_settings["invite_link"]


def write_config(mode, field, key, value=None):
    """
    Writes/Deletes key-value pair to config.ini

    :param mode:    'w' = write | 'd' = delete
    :param field:   Config.ini field
    :param key:     Key for value in config
    :param value:   Value for key in config
    :return:
    """
    config_object = ConfigParser()
    config_object.read("config.ini")
    config_field = config_object[field]

    if mode == 'w':
        config_field[str(key)] = value
    elif mode == 'd':
        config_field.pop(str(key))
    else:
        print('invalid config write mode')


async def spotify_to_yt_dl(ctx, link):
    """
        Extract songs and artists from spotify playlist
        convert to song list

        returns song info from youtube if its a track
                list of strings if its a playlist:
                        "{song title} {song artist}"
    """
    song_info = None
    track_flag = True
    # Check for track or playlist link
    if 'playlist' in link:
        # Get playlist from playlist id
        playlist = spotify.playlist_items(link[link.find("playlist/") + 9:])
        # convert playlist tracks to list of youtube searchable strings
        song_info = [f"{i['track']['name']} {i['track']['album']['artists'][0]['name']}"
                     for i in playlist['tracks']['items']]
        track_flag = False

    elif 'track' in link:
        # Get track from track id
        track = spotify.track(link[link.find("track/") + 6:])
        # Download song info from yt and add to song info
        yt_dl = await download_from_yt(ctx, f"{track['name']} {track['album']['artists'][0]['name']}")
        song_info = yt_dl[0]

    else:
        pass
    return song_info, track_flag


async def soundcloud_to_yt_dl(ctx, link):
    """
        Extract songs and artists from soundcloud playlist
        convert to song list

        returns song info from youtube if its a track
                list of strings if its a playlist:
                        "{song title} {song artist}"
    """
    song_info = None
    track_flag = True
    sc_result = soundcloud.resolve(link)

    if type(sc_result) == Playlist:
        # Convert track details into searchable youtube string
        song_info = [f'{track.title} {track.artist}'
                     for track in sc_result]
        track_flag = False

    elif type(sc_result) == Track:
        # Get song info from youtube and add to song info list
        yt_dl = await download_from_yt(ctx, f'{sc_result.title} {sc_result.artist}')
        song_info = yt_dl[0]

    else:
        pass
    return song_info, track_flag


async def download_from_yt(ctx, link):
    """
        Extracts info from yt link, adds song to server queue, plays song from queue.
    """
    # Call Youtube_DL to fetch song info
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # DEBUG COMMAND, pass test song from config in place of link
        if link == "DEBUG":
            song_info = ydl.extract_info(test_song, download=False)
        else:
            song_info = ydl.extract_info(link, download=False)
    # print(song_info)  # Debug call to see youtube_dl output

    # Detect if link is a playlist
    try:
        if song_info['_type'] == 'playlist':
            # If link is a playlist set song_info to a list of songs
            song_info = song_info['entries']
        else:
            print(f"Link from {ctx.guild.name} is unsupported")
    except KeyError:
        pass

    return song_info


async def play_music_(ctx):
    """
        Play songs in server's queue
    """
    try:
        # Get voice client
        vc = ctx.guild.voice_client
        # Get server song queue
        song_queue = get_queue(ctx.guild.id)

        while song_queue:
            try:
                if vc.is_connected() and not vc.is_playing():
                    # Replace yt searchable string in queue with yt_dl song info
                    if type(song_queue[0]) == str:
                        yt_dl = await download_from_yt(ctx, song_queue[0])
                        song_queue[0] = song_info_to_tuple(yt_dl[0], ctx)
                    song_url = song_queue[0][1]
                    # Create FFmpeg audio stream, attach to voice client
                    vc.play(discord.FFmpegPCMAudio(song_url, **ffmpeg_opts))
                    vc.source = discord.PCMVolumeTransformer(vc.source)
                    vc.volume = 1

                    # Display now playing message
                    await ctx.invoke(bot.get_command('np'))

            except discord.errors.ClientException:
                print(f"ClientException: Failed to Play Song in {ctx.guild.name}")
                break

            # Pause function while playing song, prevents rapid song switching
            while vc.is_playing():
                await asyncio.sleep(1)

            # Move to next song in queue once song is finished
            if song_queue:
                song_queue.pop(0)

        # Disconnect if queue is empty and bot is not playing
        await asyncio.sleep(180)
        if not song_queue and not vc.is_playing():
            await ctx.invoke(bot.get_command('disconnect'))

    except discord.DiscordException:
        pass


# Run bot
bot.run(TOKEN, bot=True, reconnect=True)
