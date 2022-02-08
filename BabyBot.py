import discord 
import config
from discord.ext import commands, tasks
from itertools import cycle
import music 
import redditscraper

cfg = config.load_config()

status = cycle(("with your heart", "with the idea of hang gliding", "with fire", "the world's smallest violin",
                "with a rubik's cube", "with knives"))

file = open("cmd_pre.txt", "r")
pre = str(file.read().strip("\n"))
print("Bot command prefix is:", pre)


intents = discord.Intents.all()
client = commands.Bot(command_prefix=(pre, ">"),
                      description='Relatively simple music bot example',
                      intents=intents)



@client.event
async def on_ready():
    change_status.start()
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(activity=discord.Game("with a rubik's cube"))
    print("Baby bot is ready.")


@client.event
async def on_message(message):
    if str(message.author) != "Schimimblinii#8781":
        if "hey little buddy" in message.content:
            await message.channel.send("Hey, whats up")
        for word in message.content.split(" "):
            word_lower = word.lower()
            if word_lower == "proud" or word_lower == "pride":
                if str(message.author) == "Schmimbles#7465":
                    await message.channel.send("Thank you, my father\nYour pride strengthens my resolve")
    await client.process_commands(message)


@client.event
async def on_member_join(member):
    print(f'{member} has joined the server.')


@client.event
async def on_member_remove(member):
    print(f'{member} has left the server')


@tasks.loop(seconds=30)
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))


@client.command()
async def ping(ctx):
    latency = (client.latency * 1000).__format__(".2f")
    await ctx.send(f"Pong!\nLatency:{latency}ms")


@client.command()
async def change(ctx, *, changed):
    client.command_prefix = changed
    cmd_pre_file = open("cmd_pre.txt", "w")
    cmd_pre_file.write(changed)
    await ctx.send(f"Changed Command Prefix to {changed}")


@client.command()
async def Hell_Yeah_it_Worked(ctx):
    await ctx.send("Fuck yeah it did!")


client.add_cog(music.Music(client, cfg))
client.add_cog(redditscraper.DealAlert(client))
client.run('Nzg0ODIxMTE0ODc4NTU4MjY4.X8u3nw.nfNgt4LtFPckzMs4623NMeohx6w')
