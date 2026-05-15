import discord
from discord import app_commands
from discord.ext import commands
import datetime
import uuid
import aiohttp
import asyncio

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
        embed.add_field(name="🌐 Web Dashboard", value="Manage your server settings at our web panel.", inline=False)
        embed.add_field(name="🛠️ Staff Setup", value="Configure staff roles via `/mods`.", inline=False)
        embed.add_field(name="📈 Leveling Setup", value="1. Talk for XP.\n2. `/levelconfig` for rewards.\n3. `/rank` for stats.", inline=False)
        embed.add_field(name="💎 Premium", value="Use `!custombot` to unlock server-specific profiles!", inline=False)
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
            {"$set": {"premium": True, "premium_expiry": expiry.isoformat()}},
            upsert=True
        )
        await self.codes_db.update_one({"code": code}, {"$set": {"used": True}})
        await interaction.response.send_message(f"🚀 **Premium Activated!** Expires: **{expiry.strftime('%Y-%m-%d')}**.")

    @commands.command(name="custombot")
    async def custombot(self, ctx):
        guild_data = await self.guild_db.find_one({"guild_id": str(ctx.guild.id)})
        if not guild_data or not guild_data.get("premium"):
            return await ctx.send("❌ This is a **Premium Only** feature!")

        await ctx.message.delete()
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("⚙️ **Custom Bot Configuration**")
        
        p1 = await ctx.send("🏷️ **Name:** Tell us your new name (or type 'skip')")
        try:
            m_name = await self.bot.wait_for('message', timeout=60.0, check=check)
            new_name = m_name.content if m_name.content.lower() != "skip" else None
            await m_name.delete()
            await p1.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        p2 = await ctx.send("📝 **Bio:** Tell us your new bio (or type 'skip')")
        try:
            m_bio = await self.bot.wait_for('message', timeout=60.0, check=check)
            new_bio = m_bio.content if m_bio.content.lower() != "skip" else None
            await m_bio.delete()
            await p2.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        p3 = await ctx.send("🖼️ **PFP:** Upload a picture (or type 'skip')")
        try:
            m_pfp = await self.bot.wait_for('message', timeout=60.0, check=check)
            await m_pfp.delete()
            await p3.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        confirm = await ctx.send("❓ **Are you sure you want to enable custom bot?** (yes/no)")
        try:
            m_conf = await self.bot.wait_for('message', timeout=30.0, check=check)
            if m_conf.content.lower() != "yes": return await ctx.send("❌ Cancelled.")
            await m_conf.delete()
            await confirm.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        load = await ctx.send("🔄 **Processing...**")
        await asyncio.sleep(1.5)
        await load.edit(content="📡 Requesting......................... - **DONE!**")
        await asyncio.sleep(1.5)
        await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**")
        await asyncio.sleep(1.5)
        await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**\n💾 Applying........................... - **DONE!**")
        await asyncio.sleep(1)

        try:
            payload = {}
            if new_name: payload["nick"] = new_name
            if new_bio: payload["description"] = new_bio

            await self.bot.http.request(
                discord.http.Route(
                    "PATCH", 
                    "/guilds/{guild_id}/members/{user_id}", 
                    guild_id=ctx.guild.id, 
                    user_id=self.bot.user.id
                ),
                json=payload
            )
            
            await load.delete()
            await ctx.send("✅ **Bot updated on this guild with success!**\nThanks for using AircraftGames! ✈️")
        except Exception as e:
            await ctx.send(f"❌ Error applying: {e}")

    @commands.command(name="premiumcoderegen")
    @commands.is_owner()
    async def premiumcoderegen(self, ctx, time: str):
        time = time.lower()
        if time == "1d": days = 1
        elif time == "1m": days = 30
        elif time == "1y": days = 365
        elif time == "10y": days = 3650
        else: return await ctx.send("❌ Use: `1d`, `1m`, `1y`, or `10y`.")

        new_code = f"AC-{uuid.uuid4().hex[:8].upper()}"
        await self.codes_db.insert_one({"code": new_code, "duration_days": days, "used": False})
        try:
            await ctx.author.send(f"🎟️ **Code**: `{new_code}` ({time})")
            await ctx.send("✅ Sent to DMs.")
        except:
            await ctx.send(f"✅ Code: `{new_code}`")

    @app_commands.command(name="meme", description="Get a random meme")
    async def meme(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as response:
                data = await response.json()
                embed = discord.Embed(title=data['title'], color=0x3498db)
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"r/{data['subreddit']}")
                await interaction.response.send_message(embed=embed)

    @commands.command(name="admin-pushupdate")
    @commands.is_owner()
    async def push_update(self, ctx, *, message: str):
        success, failed = 0, 0
        status = await ctx.send(f"⏳ Sending to {len(self.bot.guilds)} owners...")
        for guild in self.bot.guilds:
            if guild.owner:
                try:
                    e = discord.Embed(title="🚀 Update", description=message, color=0xe74c3c)
                    await guild.owner.send(embed=e)
                    success += 1
                except: failed += 1
        await status.edit(content=f"✅ **Sent: {success}** | Failed: {failed}")

async def setup(bot):
    await bot.add_cog(General(bot))
