import discord
from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Information about Aircraft Bot and setup guides")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✈️ Aircraft Games - Information Center", 
            description="Aircraft Games is a high-performance bot designed for gaming and server management.",
            color=0x3498db
        )
        
        embed.add_field(
            name="🌐 Web Dashboard", 
            value="Manage your server settings, custom messages, and more at our web panel.", 
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Staff Setup", 
            value="To configure your staff roles, use the `/mods` command (Found in Moderation).", 
            inline=False
        )
        
        embed.add_field(
            name="📈 Leveling Setup", 
            value="1. Talk to gain XP.\n2. Use `/levelconfig` to set role rewards.\n3. Use `/rank` to view your stats.", 
            inline=False
        )
        
        embed.add_field(
            name="📝 About", 
            value="Built with discord.py and Motor (MongoDB). Version 1.0.0", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))
