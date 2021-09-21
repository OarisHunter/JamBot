# musicBot.py

"""
Music Bot

    Plays YouTube linked videos in discord voice channel

@author: Pierce Thompson
"""

import ast
import math
import os
import discord
import asyncio
import youtube_dl

from discord.ext import commands
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
            from link
            from search
            from playlist link
"""
@bot.command(name= 'play', help= 'Connects Bot to Voice')
async def play_(ctx, *link):
    await ctx.message.delete(delay=5)

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

    # Convert command args to string
    # allows for multi word song searches
    link = tuple_to_string(link)

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

    # Add song(s) to queue from song info
    await add_song_to_queue(ctx, song_info)

    # Play song if not playing a song
    if not vc.is_playing():
        await play_music_(ctx, vc)


"""
    Command to skip currently playing song
"""
@bot.command(name= 'skip', help= 'Skips to next Song in Queue')
async def skip_(ctx):
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


"""
    Command to clear server's Queue
"""
@bot.command(name= 'clear', help= 'Clears the Song Queue')
async def clear_(ctx):
    await ctx.message.delete(delay=5)

    # Empty the queue
    get_queue(ctx.guild.id).clear()

    # Send response
    await ctx.channel.send("**Cleared the Queue!**", delete_after=20)


"""
    Command to display songs in server's Queue
"""
@bot.command(name= 'queue', help= 'Displays the Queue')
async def queue_(ctx):
    await ctx.message.delete(delay=5)

    song_queue = get_queue(ctx.guild.id)
    if song_queue:
        embed = generate_display_queue(ctx, song_queue)

        await ctx.channel.send(embed=embed, delete_after=60)
    else:
        await ctx.channel.send("**Queue is empty!**", delete_after=10)

"""
    Command to display "Now Playing" message
"""
@bot.command(name= 'np', help= 'Displays the currently playing song')
async def nowPlaying_(ctx):
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    vc = ctx.message.guild.voice_client
    song_queue = get_queue(ctx.guild.id)
    if vc and vc.is_playing():
        print(f"Now Playing {song_queue[0][0]} in {ctx.author.voice.channel.name} of {ctx.guild.name}")
        # await ctx.channel.send(f'**Now Playing**\n\n{song_queue[0][0]}', delete_after=10)
        await ctx.channel.send(embed=generate_np_embed(ctx, song_queue[0]))
    else:
        print(f'NowPlaying: Not in a Voice Channel in {ctx.guild.name}')
        await ctx.channel.send(f'Not in a Voice Channel', delete_after=10)


"""
    Pauses music to be resumed later
"""
@bot.command(name= 'pause', help= 'Pauses currently playing song')
async def pause_(ctx):
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

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
        if vc.is_connected():
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

        await ctx.channel.send(f'Prefix for {ctx.guild.name} has been changed to: {bot_prefixes[str(ctx.guild.id)]}', delete_after=10)
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

    await ctx.channel.send(embed=generate_invite(ctx))


"""
    Custom help command
"""
@bot.command(name= 'help')
async def help_(ctx):
    try:
        await ctx.message.delete(delay=5)
    except discord.DiscordException:
        pass

    await ctx.channel.send(embed=generate_help(ctx))


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
    Generates embed for "Now Playing" messages
    
    song: tuple (song_title, playback_url, webpage_url, author of request)
"""
def generate_np_embed(ctx, song: tuple):
    embed = discord.Embed(title="Now Playing", color=embed_theme)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_image(url=song[5])
    embed.add_field(name="Song: ",
                    value=f"[{song[0]}]({song[2]})\n"
                          f"Duration - {math.floor(song[4]/60)}:{song[4]%60}",
                    inline=False)
    embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
    return embed


"""
    Generates embed for "Added to Queue" messages

    song: tuple (song_title, playback_url, webpage_url, author of request)
"""
def generate_added_queue_embed(ctx, song, flag):
    embed = discord.Embed(title="Added to Queue", color=embed_theme)
    embed.set_thumbnail(url=bot.user.avatar_url)
    if flag == 0:
        embed.add_field(name="Song: ", value=f"[{song[0]}]({song[2]})", inline=False)
        embed.set_footer(text=f"Requested by {song[3].name}", icon_url=song[3].avatar_url)
    else:
        for i in song:
            embed.add_field(name="Song: ", value=f"[{i[0]}]({i[2]})", inline=False)
        embed.set_footer(text=f"Requested by {song[0][3].name}", icon_url=song[0][3].avatar_url)
    return embed


"""
    Generates embed for "Queue" messages

    queue: Server song queue
"""
def generate_display_queue(ctx, queue):
    embed = discord.Embed(title="Queue", color=embed_theme)
    embed.set_thumbnail(url=bot.user.avatar_url)
    # Build message to display
    overflow = False
    for count, song in enumerate(queue):
        # Cap queue display length
        if count == queue_display_length:
            overflow = True
            break
        embed.add_field(name=f"{count + 1}: ", value=f"[{song[0]}]({song[2]})", inline=False)
    # Display overflow message
    if overflow:
        embed.set_footer(text=f"+{len(queue) - queue_display_length} more")

    # return embed
    return embed


"""
    Generate invite embed
"""
def generate_invite(ctx):
    embed = discord.Embed(title="Invite Link", url=invite_link,  color=embed_theme)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar_url)

    embed.add_field(name=f"Copyable link:", value=f"{invite_link}", inline=False)

    embed.set_footer(text=f"Generated by {ctx.message.author.name}", icon_url=ctx.message.author.avatar_url)

    return embed


"""
    Generates help embed
"""
def generate_help(ctx):
    embed = discord.Embed(title="Help", color=embed_theme)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar_url)

    for i in bot.commands:
        if not i.name == 'help':
            embed.add_field(name=get_prefix(ctx, ctx) + i.name, value=i.help, inline=False)

    return embed


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
            await ctx.channel.send(embed=generate_added_queue_embed(ctx, song_list, 1), delete_after=20)
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
            await ctx.channel.send(embed=generate_added_queue_embed(ctx, song, 0), delete_after=20)

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
    Play songs in server's queue
"""
async def play_music_(ctx, vc):
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
        try:
            await ctx.invoke(bot.get_command('disconnect'))
        except discord.DiscordException:
            pass

# Run bot
bot.run(TOKEN)
