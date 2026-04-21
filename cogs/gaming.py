import discord
from discord import app_commands
from discord.ext import commands
import random

class Gaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Using a dictionary for counting. Reset on bot restart.
        # In a future update, we can move this to MongoDB.
        self.count_data = {} 

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots and messages that aren't numbers
        if message.author.bot or not message.content.isdigit():
            return
        
        # Only runs in channels with "counting" in the name
        if "counting" in message.channel.name.lower():
            current_count = self.count_data.get(message.channel.id, 0)
            user_number = int(message.content)
            
            if user_number == current_count + 1:
                self.count_data[message.channel.id] = user_number
                await message.add_reaction("✅")
            else:
                # Wrong number! Reset and delete
                self.count_data[message.channel.id] = 0
                await message.delete()
                await message.channel.send(
                    f"❌ {message.author.mention} ruined it at **{current_count}**! Start back at **1**.", 
                    delete_after=5
                )

    @app_commands.command(name="mysteriousball", description="Ask the ball a question")
    @app_commands.describe(question="What do you want to ask the ball?")
    async def mysteriousball(self, interaction: discord.Interaction, question: str):
        responses = [
            "Yes", "No", "Whatever", "Go touch grass", 
            "Hahaha", "Maybe...", "Ask again never", 
            "The stars say yes", "Most definitely not"
        ]
        response = random.choice(responses)
        
        embed = discord.Embed(title="🔮 The Mysterious Ball", color=0x9b59b6)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{response}**", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Gaming(bot))
