import discord
from discord import app_commands
from discord.ext import commands
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Access the database connected in bot.py
        self.db = self.bot.db["levels"]

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        # Find user in DB
        user_data = await self.db.find_one({"user": user_id, "guild": guild_id})
        
        if not user_data:
            # First time talking
            await self.db.insert_one({
                "user": user_id, 
                "guild": guild_id, 
                "xp": 5, 
                "lvl": 1
            })
        else:
            # Add random XP
            xp_to_add = random.randint(5, 15)
            new_xp = user_data["xp"] + xp_to_add
            # Level formula: Every 100 XP is a level (simple version)
            new_lvl = (new_xp // 100) + 1
            
            if new_lvl > user_data["lvl"]:
                await message.channel.send(f"🎊 Congrats {message.author.mention}, you reached **Level {new_lvl}**!")
            
            await self.db.update_one(
                {"_id": user_data["_id"]}, 
                {"$set": {"xp": new_xp, "lvl": new_lvl}}
            )

    @app_commands.command(name="rank", description="Check your current level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        
        user_data = await self.db.find_one({
            "user": str(target.id), 
            "guild": str(interaction.guild.id)
        })
        
        if not user_data:
            await interaction.response.send_message(f"📊 {target.display_name} hasn't earned any XP yet!", ephemeral=True)
            return

        embed = discord.Embed(title=f"📊 Rank: {target.display_name}", color=0x3498db)
        embed.add_field(name="Level", value=user_data["lvl"], inline=True)
        embed.add_field(name="Total XP", value=user_data["xp"], inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
