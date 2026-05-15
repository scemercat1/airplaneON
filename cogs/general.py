import discord
from discord import app_commands
from discord.ext import commands
import datetime
import uuid
import aiohttp

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.codes_db = self.bot.db["premium_codes"]
        self.guild_db = self.bot.db["guild_data"]

    @app_commands.command(name="help", description="Information about Aircraft Bot and setup guides")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✈️ Aircraft Games - Information Center", 
            description="Aircraft Games is a high-performance bot designed for gaming and server management.",
            color=0x3498db
        )
        embed.add_field(name="🌐 Web Dashboard", value="Manage your server settings, custom messages, and more at our web panel.", inline=False)
        embed.add_field(name="🛠️ Staff Setup", value="To configure your staff roles, use the `/mods` command (Found in Moderation).", inline=False)
        embed.add_field(name="📈 Leveling Setup", value="1. Talk to gain XP.\n2. Use `/levelconfig` to set role rewards.\n3. Use `/rank` to view your stats.", inline=False)
        embed.add_field(name="📝 About", value="Built with discord.py and Motor (MongoDB). Version 1.0.0", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reactionrolemenu", description="Create a customizable reaction role menu")
    @app_commands.describe(text="Message content", role1="First Role", role2="Second Role", role3="Third Role")
    @app_commands.checks.has_permissions(administrator=True)
    async def reactionrolemenu(self, interaction: discord.Interaction, text: str, role1: discord.Role, role2: discord.Role = None, role3: discord.Role = None):
        embed = discord.Embed(title="Select Your Roles", description=text, color=0x00ffaa)
        roles = [r for r in [role1, role2, role3] if r]
        emojis = ["1️⃣", "2️⃣", "3️⃣"]
        role_list_text = ""
        for i, role in enumerate(roles):
            role_list_text += f"{emojis[i]} : {role.mention}\n"
        embed.add_field(name="Available Roles", value=role_list_text, inline=False)
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        for i in range(len(roles)):
            await message.add_reaction(emojis[i])

    @app_commands.command(name="premium", description="Redeem a premium activation code")
    async def premium(self, interaction: discord.Interaction, code: str):
        code_data = await self.codes_db.find_one({"code": code, "used": False})
        if not code_data:
            return await interaction.response.send_message("❌ **Invalid or expired code.**", ephemeral=True)
        days = code_data["duration_days"]
        expiry = datetime.datetime.now() + datetime.timedelta(days=days)
        await self.guild_db.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {"premium": True, "premium_expiry": expiry.isoformat(), "redeemed_by": str(interaction.user.id)}},
            upsert=True
        )
        await self.codes_db.update_one({"code": code}, {"$set": {"used": True, "redeem_date": datetime.datetime.now().isoformat()}})
        await interaction.response.send_message(f"🚀 **Premium Activated!** Expires: **{expiry.strftime('%Y-%m-%d')}**.")

    @commands.command(name="custombio")
    async def custombio(self, ctx, *, bio: str):
        guild_data = await self.guild_db.find_one({"guild_id": str(ctx.guild.id)})
        if not guild_data or not guild_data.get("premium"):
            return await ctx.send("❌ This is a **Premium Only** feature. Upgrade your server to use custom bios!")
        
        expiry_str = guild_data.get("premium_expiry")
        if expiry_str:
            expiry = datetime.datetime.fromisoformat(expiry_str)
            if datetime.datetime.now() > expiry:
                await self.guild_db.update_one({"guild_id": str(ctx.guild.id)}, {"$set": {"premium": False}})
                try:
                    await ctx.guild.me.edit(nick=None)
                except:
                    pass
                return await ctx.send("❌ Premium has expired. Bio/Nickname reset.")

        try:
            await ctx.guild.me.edit(nick=bio[:32])
            await self.guild_db.update_one({"guild_id": str(ctx.guild.id)}, {"$set": {"custom_bio": bio}})
            await ctx.send(f"✅ Bot nickname updated to: **{bio[:32]}**")
        except discord.Forbidden:
            await ctx.send("❌ I don't have 'Change Nickname' permissions to update the bio!")

    @commands.command(name="premiumcoderegen")
    @commands.is_owner()
    async def premiumcoderegen(self, ctx, time: str):
        if time == "1m": days = 30
        elif time == "1y": days = 365
        elif time == "10y": days = 3650
        else: return await ctx.send("❌ Use: `1m`, `1y`, or `10y`.")
        new_code = f"AC-{uuid.uuid4().hex[:8].upper()}"
        await self.codes_db.insert_one({"code": new_code, "duration_days": days, "used": False, "created_at": datetime.datetime.now().isoformat()})
        try:
            await ctx.author.send(f"🎟️ **New Code**: `{new_code}` ({time})")
            await ctx.send("✅ Sent to DMs.")
        except discord.Forbidden:
            await ctx.send(f"✅ Code: `{new_code}`")

    @app_commands.command(name="meme", description="Get a random meme from the web")
    async def meme(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as response:
                if response.status == 200:
                    data = await response.json()
                    embed = discord.Embed(title=data['title'], url=data['postLink'], color=0x3498db)
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}")
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("❌ Failed to fetch meme.", ephemeral=True)

    @commands.command(name="admin-pushupdate")
    @commands.is_owner()
    async def push_update(self, ctx, *, message: str):
        success, failed = 0, 0
        status_msg = await ctx.send(f"⏳ Sending to {len(self.bot.guilds)} owners...")
        for guild in self.bot.guilds:
            if guild.owner:
                try:
                    embed = discord.Embed(title="🚀 Global Update", description=message, color=0xe74c3c)
                    await guild.owner.send(embed=embed)
                    success += 1
                except: failed += 1
        await status_msg.edit(content=f"✅ **Sent: {success}** | Failed: {failed}")

async def setup(bot):
    await bot.add_cog(General(bot))
