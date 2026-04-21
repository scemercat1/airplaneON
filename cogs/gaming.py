import discord
from discord.ext import commands
import random

class Gaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.count_data = {} # In prod, move this to MongoDB

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.content.isdigit(): return
        
        # Example: only works in a channel named 'counting'
        if "counting" in message.channel.name.lower():
            current = self.count_data.get(message.channel.id, 0)
            val = int(message.content)
            
            if val == current + 1:
                self.count_data[message.channel.id] = val
                await message.add_reaction("✅")
            else:
                self.count_data[message.channel.id] = 0
                await message.delete()
                await message.channel.send(f"❌ {message.author.mention} ruined it! Start back at 1.", delete_after=5)

    @app_commands.command(name="mysteriousball")
    async def mball(self, itx, question: str):
        responses = ["Yes", "No", "Whatever", "Go touch grass", "Hahaha", "Maybe...", "Ask again never"]
        await itx.response.send_message(f"🔮 **Question:** {question}\n✨ **Answer:** {random.choice(responses)}")

async def setup(bot): await bot.add_cog(Gaming(bot))
