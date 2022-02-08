from discord.ext import commands
import asyncpraw
import pickle

user_agent = "Discount Checker 1.0 by /u/meguypersondude"
reddit = asyncpraw.Reddit(
    client_id ="h9zx5dCDnOHhh8pMUmmdjg",
    client_secret ="IfwefkKsDoSfxEz4BkN982ihNOy5rA",
    user_agent = user_agent
)

class WatchedGame():
    """Data class for watched game object"""
    def __init__(self):
        self.watchers = []
        self.gamename = ""
        
    
    def add_watcher(self, watcher):
        self.watchers.append(watcher)
        return
        
    def get_watchers(self):
        return self.watchers
    
    def set_name(self, name):
        self.gamename = name
        return

    def get_name(self):
        return self.gamename


class DealAlert(commands.Cog):
    """Bot commands to send alerts on game deal posts"""

    def __init__(self, bot):
        self.bot = bot
        self.watchedgamelist = []
        try:
            self.watchedgamelist = pickle.load(open("watchlist.p", "rb"))
        except(FileNotFoundError):
            pass


    @commands.command(aliases=["gda"])
    async def game_deal_alert(self, ctx):
        """Command to start alert stream"""

        subreddit = await reddit.subreddit("ButtonPets")
        
        async for submission in subreddit.stream.submissions(): # pulls from subreddit on submission 
            with open('watchlist.pkl', 'rb') as f:
                self.watchedgamelist = pickle.load(f)

            for game in self.watchedgamelist:
                game_title = str(game.get_name()).lower()
                sub_titile = str(submission.title).lower()

                if game_title in sub_titile: # if the game's name is in the submission, let watchers know
                    print("found it!")

                    for user in game.get_watchers():
                        await ctx.send(f"{user}")

                    await ctx.send(f"There is a sale on a game you were watching:\n{submission.title}\nhttps://www.reddit.com{submission.permalink}\n")




    @commands.command(aliases=["ag"])
    async def addgame(self, game):
        new_game = WatchedGame()
        new_game.set_name(str(game))
        self.watchedgamelist.append(new_game)
        pickle.dump(self.watchedgamelist, open("watchlist.p", "wb"))


    @commands.command(aliases=["aw"])
    async def addwatcher(self, ctx, game_watched, watcher):

        game_watched = str(game_watched)

        for game_ob in self.watchedgamelist:
            
            if game_ob.get_name() == game_watched:
                game_ob.add_watcher(watcher)
                with open('watchlist.pkl', 'wb') as f:
                    pickle.dump(self.watchedgamelist, f)
                await ctx.send(f"Got it\n adding {watcher} to {game_watched} watch list\n")
                return
        
        await self.addgame(game_watched)
        await ctx.send(f"Oh whoops, {game_watched} doesn't seem to be watched already\nCreating a watch for it and adding {watcher} to it\n")
        self.watchedgamelist[-1].add_watcher(watcher)
        pickle.dump(self.watchedgamelist, open("watchlist.p", "wb"))
