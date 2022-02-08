import asyncio
from importlib import reload
import logging
from types import NoneType
import discord 
import config
import youtube_dl
from video import Video
import math
from discord.ext import commands

# TODO: abstract FFMPEG options into their own file?
FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
"""
Command line options to pass to `ffmpeg` before the `-i`.

See https://stackoverflow.com/questions/43218292/youtubedl-read-error-with-discord-py/44490434#44490434 for more information.
Also, https://ffmpeg.org/ffmpeg-protocols.html for command line option reference.
"""

async def audio_playing(ctx):
    """Checks that audio is currently playing before continuing."""
    client = ctx.guild.voice_client
    if client and client.channel and client.source:
        return True
    else:
        await ctx.send(f"How am I supposed to show you that if I'm not currently playing audio??\nMake me play an audio first, then try again fuckwad")
        raise commands.CommandError("Not currently playing any audio.")


async def in_voice_channel(ctx):
    """Checks that the command sender is in the same voice channel as the bot."""
    voice = ctx.author.voice
    bot_voice = ctx.guild.voice_client
    if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
        return True
    else:
        await ctx.send(f"How are you going to hear me if i'm not in your voice chat?\nMove me first or make me play an audio first, then try again fuckwad")
        raise commands.CommandError(
            "You need to be in the channel to do that.")


async def is_audio_requester(ctx):
    """Checks that the command sender is the song requester."""
    music = ctx.bot.get_cog("Music")
    state = music.get_state(ctx.guild)
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator or state.is_requester(ctx.author):
        return True
    else:
        raise commands.CommandError(
            "You need to be the song requester to do that.")


class Music(commands.Cog):
    """Bot commands to help play music."""

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config[__name__.split(".")[-1]]  # retrieve module name, find config entry
        self.states = {}
        self.bot.add_listener(self.on_reaction_add, "on_reaction_add")

    def get_state(self, guild):
        """Gets the state for `guild`, creating it if it does not exist."""
        if guild.id in self.states:
            return self.states[guild.id]
        else:
            self.states[guild.id] = GuildState()
            return self.states[guild.id]

    @commands.command(aliases=["stop"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        """Leaves the voice channel, if currently in one."""
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild)
        if client and client.channel:
            await client.disconnect()
            state.playlist = []
            state.now_playing = None
        else:
            raise commands.CommandError("Not in a voice channel.")

    @commands.command(aliases=["resume", "p"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    @commands.check(is_audio_requester)
    async def pause(self, ctx):
        """Pauses any currently playing audio."""
        client = ctx.guild.voice_client
        self._pause_audio(client)

    def _pause_audio(self, client):
        if client.is_paused():
            client.resume()
        else:
            client.pause()

    @commands.command(aliases=["vol", "v"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    @commands.check(is_audio_requester)
    async def volume(self, ctx, volume: int):
        """Change the volume of currently playing audio (values 0-250 by default)."""
        reload(config)
        cfg = config.load_config()
        self.config = cfg[__name__.split(".")[-1]]

        async with ctx.typing():
            state = self.get_state(ctx.guild)

            # make sure volume is nonnegative
            if volume < 0:
                await ctx.send(f"You think i'm fucking stupid?\n{volume} is a negative volume\nHow would that work?\nWould I suck the sound out of your head??\nFucking dip-ass\nI'm setting it to 0 instead")
                volume = 0
        
            max_vol = self.config["max_volume"]
            if max_vol > -1:  # check if max volume is set
                # clamp volume to [0, max_vol]
                if volume > max_vol:
                    await ctx.send(f"Unfortunately there is a max volume set right now and {volume} is too high\nI'm setting it to {max_vol}, which is the highest setting right now, instead")
                    volume = max_vol

            client = ctx.guild.voice_client
            await ctx.send(f"Volume is now: {volume}")
            changeconfig("config.toml", 5, f'"last_volume"={volume} # Last set volume')

            if not isinstance(client, NoneType):
                state.volume = float(volume) / 100.0
                client.source.volume = state.volume  # update the AudioSource's volume to match

    @commands.command(aliases=["volmax", "vmax"])
    @commands.check(is_audio_requester)
    async def max_volume(self, ctx, volume: int):
        """Changes max volume setting"""
        reload(config)
        cfg = config.load_config()
        self.config = cfg[__name__.split(".")[-1]]
        async with ctx.typing():
            state = self.get_state(ctx.guild)
            client = ctx.guild.voice_client

            #checks if new value is unlimited volume
            if volume == -1:
                # sets max volume to -1
                changeconfig("config.toml", 4, '"max_volume"=-1 # Max audio volume. Set to -1 for unlimited.[tips]')
                await ctx.send(f"Setting max-volunme to unlimited\nBe careful\nDon't want to rupture anyone's eardrums")
                return

            # make sure volume is nonnegative
            elif volume < 0 & volume != -1:
                changeconfig("config.toml", 4, '"max_volume"=0 # Max audio volume. Set to -1 for unlimited.[tips]')
                await ctx.send(f"You've understood something wrong or you're stupid\nI can't have a negative volume in general\nHow could my max-volume be negative?")
                if not isinstance(client, NoneType):
                    await ctx.send(f"I'm setting to 0 instead")
                    volume = 0
                    state.volume = float(volume) / 100.0
                    client.source.volume = state.volume  # update the AudioSource's volume to match
                    await ctx.send(f"Max volume is now: {volume}")
                    await ctx.send(f"Volume is now: {volume}")
                    changeconfig("config.toml", 5, f'"last_volume"={volume} # Last set volume')
                    return
 
            #sets current volume to max volume if current volume is greater than new max
            elif self.config["last_volume"] > volume & volume != -1:
                if not isinstance(client, NoneType):
                    await ctx.send(f"This max volume is greater than the current volume\nDon't worry i'll lower current volume to be the new max")
                    await self.volume(ctx, volume)
            
            changeconfig("config.toml", 4, f'"max_volume"={volume} # Max audio volume. Set to -1 for unlimited.[tips]')
            await ctx.send(f"Max volume is now: {volume}")

    @commands.command(aliases=["showvol", "sv"])
    @commands.check(audio_playing)
    async def show_volume(self, ctx):
        """Changes max volume setting"""
        reload(config)
        cfg = config.load_config()
        self.config = cfg[__name__.split(".")[-1]]
        async with ctx.typing():
            maxvol = self.config["max_volume"]
            vol = self.config["last_volume"]
            await ctx.send(f"Max volume: {maxvol}")
            await ctx.send(f"Current Volume: {vol}")
 
    @commands.command()
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    async def skip(self, ctx):
        """Skips the currently playing song, or votes to skip it."""
        async with ctx.typing():
            state = self.get_state(ctx.guild)
            client = ctx.guild.voice_client
            if ctx.channel.permissions_for(
                    ctx.author).administrator or state.is_requester(ctx.author):
                # immediately skip if requester or admin
                client.stop()
            elif self.config["vote_skip"]:
                # vote to skip song
                channel = client.channel
                self._vote_skip(channel, ctx.author)
                # announce vote
                users_in_channel = len([
                    member for member in channel.members if not member.bot
                ])  # don't count bots
                required_votes = math.ceil(
                    self.config["vote_skip_ratio"] * users_in_channel)
                await ctx.send(
                    f"{ctx.author.mention} doesn't want to hear this shit anymore ({len(state.skip_votes)}/{required_votes} votes)"
                )
            else:
                raise commands.CommandError("Sorry, vote skipping is disabled.")

    def _vote_skip(self, channel, member):
        """Register a vote for `member` to skip the song playing."""
        logging.info(f"{member.name} votes to skip")
        state = self.get_state(channel.guild)
        state.skip_votes.add(member)
        users_in_channel = len([
            member for member in channel.members if not member.bot
        ])  # don't count bots
        if (float(len(state.skip_votes)) /
                users_in_channel) >= self.config["vote_skip_ratio"]:
            # enough members have voted to skip, so skip the song
            logging.info(f"Enough votes, skipping...")
            channel.guild.voice_client.stop()

    def _play_song(self, client, state, song):
        state.now_playing = song
        state.skip_votes = set()  # clear skip votes
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song.stream_url, before_options=FFMPEG_BEFORE_OPTS), volume=state.volume)

        def after_playing(err):
            if len(state.playlist) > 0:
                next_song = state.playlist.pop(0)
                self._play_song(client, state, next_song)
            else:
                asyncio.run_coroutine_threadsafe(client.disconnect(),
                                                 self.bot.loop)

        client.play(source, after=after_playing)

    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def nowplaying(self, ctx):
        """Displays information about the current song."""
        async with ctx.typing():
            state = self.get_state(ctx.guild)
            message = await ctx.send("", embed=state.now_playing.get_embed())
            await self._add_reaction_controls(message)

    @commands.command(aliases=["q", "playlist"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def queue(self, ctx):
        """Display the current play queue."""
        async with ctx.typing():
            state = self.get_state(ctx.guild)
            await ctx.send(self._queue_text(state.playlist))

    def _queue_text(self, queue):
        """Returns a block of text describing a given song queue."""
        if len(queue) > 0:
            message = [f"{len(queue)} songs in queue:"]
            message += [
                f"  {index+1}. **{song.title}** (requested by **{song.requested_by.name}**)"
                for (index, song) in enumerate(queue)
            ]  # add individual songs
            return "\n".join(message)
        else:
            return "The play queue is empty."

    @commands.command(aliases=["cq"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.has_permissions(administrator=True)
    async def clearqueue(self, ctx):
        """Clears the play queue without leaving the channel."""
        async with ctx.typing():
            state = self.get_state(ctx.guild)
            state.playlist = []

    @commands.command(aliases=["jq"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.has_permissions(administrator=True)
    async def jumpqueue(self, ctx, song: int, new_index: int):
        """Moves song at an index to `new_index` in queue."""
        async with ctx.typing():
            state = self.get_state(ctx.guild)  # get state for this guild
            if 1 <= song <= len(state.playlist) and 1 <= new_index:
                song = state.playlist.pop(song - 1)  # take song at index...
                state.playlist.insert(new_index - 1, song)  # and insert it.

                await ctx.send(self._queue_text(state.playlist))
            else:
                raise commands.CommandError("You must use a valid index.")

    @commands.command(brief="Plays audio from <url>.")
    @commands.guild_only()
    async def play(self, ctx, *, url):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""
        async with ctx.typing():
            client = ctx.guild.voice_client
            state = self.get_state(ctx.guild)  # get the guild's state

            if client and client.channel:
                try:
                    video = Video(url, ctx.author)
                except youtube_dl.DownloadError as e:
                    logging.warn(f"Error downloading video: {e}")
                    await ctx.send(
                        "There was an error downloading your video, sorry.")
                    return
                state.playlist.append(video)
                message = await ctx.send(
                    "Added to queue.", embed=video.get_embed())
                await self._add_reaction_controls(message)
            else:
                if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                    channel = ctx.author.voice.channel
                    try:
                        video = Video(url, ctx.author)
                    except youtube_dl.DownloadError as e:
                        await ctx.send(
                            "There was an error downloading your video, sorry.")
                        return
                    client = await channel.connect()
                    self._play_song(client, state, video)
                    message = await ctx.send("", embed=video.get_embed())
                    await self._add_reaction_controls(message)
                    logging.info(f"Now playing '{video.title}'")
                else:
                    raise commands.CommandError(
                        "You need to be in a voice channel to do that.")

    async def on_reaction_add(self, reaction, user):
        """Respods to reactions added to the bot's messages, allowing reactions to control playback."""
        message = reaction.message
        if user != self.bot.user and message.author == self.bot.user:
            await message.remove_reaction(reaction, user)
            if message.guild and message.guild.voice_client:
                user_in_channel = user.voice and user.voice.channel and user.voice.channel == message.guild.voice_client.channel
                permissions = message.channel.permissions_for(user)
                guild = message.guild
                state = self.get_state(guild)
                if permissions.administrator or (
                        user_in_channel and state.is_requester(user)):
                    client = message.guild.voice_client
                    if reaction.emoji == "⏯":
                        # pause audio
                        self._pause_audio(client)
                    elif reaction.emoji == "⏭":
                        # skip audio
                        client.stop()
                    elif reaction.emoji == "⏮":
                        state.playlist.insert(
                            0, state.now_playing
                        )  # insert current song at beginning of playlist
                        client.stop()  # skip ahead
                elif reaction.emoji == "⏭" and self.config["vote_skip"] and user_in_channel and message.guild.voice_client and message.guild.voice_client.channel:
                    # ensure that skip was pressed, that vote skipping is
                    # enabled, the user is in the channel, and that the bot is
                    # in a voice channel
                    voice_channel = message.guild.voice_client.channel
                    self._vote_skip(voice_channel, user)
                    # announce vote
                    channel = message.channel
                    users_in_channel = len([
                        member for member in voice_channel.members
                        if not member.bot
                    ])  # don't count bots
                    required_votes = math.ceil(
                        self.config["vote_skip_ratio"] * users_in_channel)
                    await channel.send(
                        f"{user.mention} voted to skip ({len(state.skip_votes)}/{required_votes} votes)"
                    )

    async def _add_reaction_controls(self, message):
        """Adds a 'control-panel' of reactions to a message that can be used to control the bot."""
        CONTROLS = ["⏮", "⏯", "⏭"]
        for control in CONTROLS:
            await message.add_reaction(control)


class GuildState:
    """Helper class managing per-guild state."""

    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None

    def is_requester(self, user):
        return self.now_playing.requested_by == user

def changeconfig(path, line, replace):
    cfg_file = open(path, "r")
    cfg_lines = cfg_file.readlines()
    cfg_lines[line] = replace + "\n"
    cfg_file = open(path, "w")
    cfg_file.writelines(cfg_lines)
    cfg_file.close()
