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

    @commands.command(name="admin-pushupdate")
    @commands.is_owner()
    async def push_update(self, ctx, *, message: str):
        success = 0
        failed = 0
        
        # Notify the admin that the process has started
        status_msg = await ctx.send(f"⏳ Sending update to {len(self.bot.guilds)} server owners...")

        for guild in self.bot.guilds:
            owner = guild.owner
            if owner:
                try:
                    embed = discord.Embed(
                        title="🚀 Aircraft Games - Global Update",
                        description=message,
                        color=0xe74c3c
                    )
                    embed.set_footer(text=f"Sent to owner of: {guild.name}")
                    await owner.send(embed=embed)
                    success += 1
                except discord.Forbidden:
                    failed += 1
                except Exception:
                    failed += 1
        
        await status_msg.edit(content=f"✅ **Update Push Complete!**\nSent: {success}\nFailed: {failed}")

async def setup(bot):
    await bot.add_cog(General(bot))
