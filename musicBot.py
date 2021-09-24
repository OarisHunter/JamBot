# musicBot.py

"""
Music Bot

    Plays YouTube linked videos in discord voice channel

@author: Pierce Thompson
"""

import ast
import os
import discord
import asyncio
import youtube_dl
import spotipy

from discord.ext import commands
from spotipy import SpotifyClientCredentials
from sclib import SoundcloudAPI, Track, Playlist
from botEmbeds import *
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


"""
    Get prefixes from config.ini
"""
def get_prefix(client, message):
    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_prefixes = config_object["PREFIXES"]
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
# Spotify API
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_CID'),
                                                                              client_secret=os.getenv('SPOTIFY_SECRET')
                                                                              ))
# SoundCloud API
soundcloud = SoundcloudAPI()


"""
    Called when bot start-up has finished
"""
@bot.event
async def on_ready():
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
"""
    Command to connect to voice
        plays song 
            from yt link
            from yt search
            from yt playlist link
"""
@bot.command(name= 'play', help= 'Connects Bot to Voice')
async def play_(ctx, *link):
    await ctx.message.delete(delay=5)

    # Check that author is in a voice channel
    if ctx.author.voice is None:
        return await ctx.channel.send("Not in a Voice Channel", delete_after=10)

    # Convert command args to string
    # allows for multi word song searches
    link = tuple_to_string(link)

    # Pass link to parser to determine origin
    song_info = await extract_song_info(ctx, link)

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
        await add_song_to_queue(ctx, song_info)

        # Play song if not playing a song
        if not vc.is_playing():
            await play_music_(ctx)


"""
    Command to skip currently playing song
"""
@bot.command(name= 'skip', help= 'Skips to next Song in Queue')
async def skip_(ctx):
    try:
        await ctx.message.delete(delay=5)

        vc = ctx.guild.voice_client # Get current voice client

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


"""
    Command to clear server's Queue
"""
@bot.command(name= 'clear', help= 'Clears the Song Queue')
async def clear_(ctx):
    try:
        await ctx.message.delete(delay=5)

        # Empty the queue
        get_queue(ctx.guild.id).clear()

        # Send response
        await ctx.channel.send("**Cleared the Queue!**", delete_after=20)

    except discord.DiscordException:
        pass


"""
    Command to display songs in server's Queue
"""
@bot.command(name= 'queue', help= 'Displays the Queue')
async def queue_(ctx):
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


"""
    Command to display "Now Playing" message
"""
@bot.command(name= 'np', help= 'Displays the currently playing song')
async def nowPlaying_(ctx):
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




"""
    Pauses music to be resumed later
"""
@bot.command(name= 'pause', help= 'Pauses currently playing song')
async def pause_(ctx):
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


"""
    Resumes paused music
"""
@bot.command(name = 'resume', help= 'Resumes currently playing song')
async def resume_(ctx):
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

"""
    Command to disconnect bot from voice
"""
@bot.command(name= 'disconnect', help= 'Disconnects from Voice')
async def disconnect_(ctx):
    try:
        vc = ctx.guild.voice_client

        # Check that the bot is connected to voice
        if vc and vc.is_connected():
            await vc.disconnect()

        await ctx.message.delete()

    except discord.DiscordException:
        pass

"""
    Command to change/display server defined prefix
"""
@bot.command(name= 'prefix', help= 'Changes prefix for this server')
@commands.has_permissions(administrator=True)
async def prefix_(ctx, *prefix):
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


"""
    Sends an embed with invite links to add bot to other servers.    
"""
@bot.command(name = 'invite', help= 'Shows invite link to add bot to your server')
async def invite_(ctx):
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    await ctx.channel.send(embed=generate_invite(ctx, bot, embed_theme, invite_link))


"""
    Custom help command
"""
@bot.command(name= 'help')
async def help_(ctx):
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    await ctx.channel.send(embed=generate_help(ctx, bot, embed_theme, get_prefix))


# --------------- Events -------------- #
"""
    Disconnects bot if it is alone in a voice channel
"""
@bot.event
async def on_voice_state_update(member, before, after):
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


"""
    Removes guild id and stored prefix from config.ini
"""
@bot.event
async def on_guild_join(guild):
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


"""
    Removes guild id and stored prefix from config.ini
"""
@bot.event
async def on_guild_remove(guild):
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
"""
    Directs link to proper parse method
    
    Support for Apple, SoundCloud, Spotify, and YT
"""
async def extract_song_info(ctx, link):
    song_info = None
    if "https://music.apple.com" in link:
        await ctx.channel.send("**Apple Music support coming soon!**", delete_after=20)
    elif "https://open.spotify.com" in link:
        await ctx.channel.send("**Spotify Link!** This may take a moment...", delete_after=20)
        song_info = await spotify_to_yt_dl(ctx, link)
    elif "https://soundcloud.com" in link:
        await ctx.channel.send("**SoundCloud Link!** This may take a moment...", delete_after=20)
        song_info = await soundcloud_to_yt_dl(ctx, link)
    else:
        song_info = await download_from_yt(ctx, link)
    return song_info


"""
    Converts an indeterminate length tuple to a string
"""
def tuple_to_string(tup):
    temp = ""
    for i in tup:
        temp += i + " "
    return temp.strip()


"""
    Generate song queues for all servers
        Non-Queue destructive
"""
def create_server_queue():
    # Loop through guilds bot is in
    for guild in bot.guilds:
        # Get guild id
        g_id = str(guild.id)
        # Add guild id to queue dict
        if g_id not in server_queues:
            server_queues[g_id] = []


"""
    Get Server Queue from Queue Dict
"""
def get_queue(guild_id):
    return server_queues[str(guild_id)]


"""
    Add song to Server Queue in Queue Dict
"""
def add_queue(guild_id, song_tuple):
    server_queues[str(guild_id)].append(song_tuple)


"""
    Add song(s) to queue
"""
async def add_song_to_queue(ctx, song_info):
    # If link was a playlist, loop through list of songs and add them to the queue
    if type(song_info) == list:
        song_list = []
        for i in song_info:
            # Generate song tuple
            title = i['title']
            url = i["formats"][0]["url"]
            web_page = i['webpage_url']
            duration = i['duration']
            thumbnail = i["thumbnails"][-1]['url']
            song = (title, url, web_page, ctx.message.author, duration, thumbnail)

            # Add song to queue, and song list for playback and message display
            add_queue(ctx.guild.id, song)
            song_list.append(song)
        if (len(song_info)) > 1 or ctx.guild.voice_client.is_playing():
            await ctx.channel.send(embed=generate_added_queue_embed(ctx, song_list, bot, embed_theme, queue_display_length), delete_after=40)
    # Otherwise add the single song to the queue, display message if song was added to the queue
    else:
        # Generate song tuple
        title = song_info['title']
        url = song_info["formats"][0]["url"]
        web_page = song_info['webpage_url']
        duration = song_info['duration']
        thumbnail = song_info["thumbnails"][-1]['url']
        song = (title, url, web_page, ctx.message.author, duration, thumbnail)

        # Display added to queue if queue is not empty
        if len(get_queue(ctx.guild.id)) >= 1:
            await ctx.channel.send(embed=generate_added_queue_embed(ctx, song, bot, embed_theme, queue_display_length), delete_after=40)

        # add song to queue for playback
        add_queue(ctx.guild.id, song)


"""
    Get server options from config.ini
"""
def read_config():
    global test_song, ydl_opts, ffmpeg_opts, invite_link

    config_object = ConfigParser()
    config_object.read("config.ini")
    bot_settings = config_object["BOT_SETTINGS"]
    test_song = bot_settings["test_song"]
    ydl_opts = ast.literal_eval(bot_settings["ydl_opts"])
    ffmpeg_opts = ast.literal_eval(bot_settings["ffmpeg_opts"])
    invite_link = bot_settings["invite_link"]


"""
    Extract songs and artists from spotify playlist, convert to song list, get song info from youtube
"""
async def spotify_to_yt_dl(ctx, link):
    song_info = None
    # Check for track or playlist link
    if 'playlist' in link:
        # Get playlist from playlist id
        playlist = spotify.playlist_items(link[link.find("playlist/") + 9:])
        # convert playlist tracks to list of youtube searchable strings
        song_info = []
        for i in playlist['tracks']['items']:
            search = f"{i['track']['name']} {i['track']['album']['artists'][0]['name']}"

            # Download song info from yt and add to song info list
            yt_dl = await download_from_yt(ctx, search)
            song_info.append(yt_dl[0])

    elif 'track' in link:
        # Get track from track id
        track = spotify.track(link[link.find("track/") + 6:])
        # Convert into youtube searchable string
        search = f"{track['name']} {track['album']['artists'][0]['name']}"

        # Download song info from yt and add to song info
        song_info = await download_from_yt(ctx, search)

    else:
        pass
    return song_info


async def soundcloud_to_yt_dl(ctx, link):
    song_info = None
    sc_result = soundcloud.resolve(link)
    if type(sc_result) == Playlist:
        # Get playlist info from SoundCloud
        song_info = []
        for track in sc_result:
            # Convert track details into searchable youtube string
            search = f'{track.title} {track.artist}'
            # Get song info from youtube and add to song info list
            yt_dl = await download_from_yt(ctx, search)
            song_info.append(yt_dl[0])
    elif type(sc_result) == Track:
        search = f'{sc_result.title} {sc_result.artist}'
        song_info = await download_from_yt(ctx, search)
    else:
        pass
    return song_info


"""
    Extracts info from yt link, adds song to server queue, plays song from queue.
"""
async def download_from_yt(ctx, link):
    # Call Youtube_DL to fetch song info
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # DEBUG COMMAND
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


"""
    Play songs in server's queue
"""
async def play_music_(ctx):
    try:
        # Get voice client
        vc = ctx.guild.voice_client
        # Get server song queue
        song_queue = get_queue(ctx.guild.id)

        while song_queue:
            try:
                if vc.is_connected() and not vc.is_playing():
                    # Create FFmpeg audio stream, attach to voice client
                    vc.play(discord.FFmpegPCMAudio(song_queue[0][1], **ffmpeg_opts))
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
bot.run(TOKEN)
