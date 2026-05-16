import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import uuid
import aiohttp
import asyncio

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.codes_db = self.bot.db["premium_codes"]
        self.guild_db = self.bot.db["guild_data"]
        self.reminders = {}
        self.water_ticker.start()

    def cog_unload(self):
        self.water_ticker.cancel()

    async def check_is_team(self, ctx):
        app_info = await self.bot.application_info()
        if app_info.team:
            return any(m.id == ctx.author.id for m in app_info.team.members)
        return ctx.author.id == app_info.owner.id

    @app_commands.command(name="help", description="Information about Aircraft Bot")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✈️ Aircraft Games - Info", 
            description="Aircraft Games is a high-performance premium bot.",
            color=0x3498db
        )
        embed.add_field(name="🌐 Dashboard", value="Manage everything online.", inline=False)
        embed.add_field(name="💎 Premium", value="Use `!custombot` to customize your bot!", inline=False)
        embed.add_field(name="🎭 Reaction Roles", value="Use `/reactionroles create` to setup menus.", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reactionroles", description="Create a reaction roles menu")
    @app_commands.describe(
        name="Panel title",
        panel_description="Description above roles",
        role1="First Role", role2="Second Role", role3="Third Role",
        role4="Fourth Role", role5="Fifth Role"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reactionroles_create(
        self, interaction: discord.Interaction, 
        name: str, panel_description: str, 
        role1: discord.Role, role2: discord.Role = None, 
        role3: discord.Role = None, role4: discord.Role = None, 
        role5: discord.Role = None
    ):
        embed = discord.Embed(title=name, description=panel_description, color=0x2ecc71)
        roles = [r for r in [role1, role2, role3, role4, role5] if r]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        value_text = ""
        for i, role in enumerate(roles):
            value_text += f"{emojis[i]} - {role.mention}\n"
        
        embed.add_field(name="Select a role below:", value=value_text, inline=False)
        embed.set_footer(text="Aircraft Games - Role System")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for i in range(len(roles)):
            await msg.add_reaction(emojis[i])

    @app_commands.command(name="premium", description="Activate a premium code")
    async def premium(self, interaction: discord.Interaction, code: str):
        code_data = await self.codes_db.find_one({"code": code, "used": False})
        if not code_data:
            return await interaction.response.send_message("❌ Invalid or expired code.", ephemeral=True)
        
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
        if not await self.check_is_team(ctx):
            return await ctx.send("❌ Only Bot Team owners, devs, and admins can use this command!")

        guild_data = await self.guild_db.find_one({"guild_id": str(ctx.guild.id)})
        if not guild_data or not guild_data.get("premium"):
            return await ctx.send("❌ This guild does not have **Premium**!")

        await ctx.message.delete()
        def check(m): return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("⚙️ **Custom Bot Configuration**")
        
        p1 = await ctx.send("🏷️ **Name:** Tell us your new name (or type 'skip')")
        try:
            m_name = await self.bot.wait_for('message', timeout=60.0, check=check)
            new_name = m_name.content if m_name.content.lower() != "skip" else None
            await m_name.delete(); await p1.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        p2 = await ctx.send("📝 **Bio:** Tell us your new bio (or type 'skip')")
        try:
            m_bio = await self.bot.wait_for('message', timeout=60.0, check=check)
            new_bio = m_bio.content if m_bio.content.lower() != "skip" else None
            await m_bio.delete(); await p2.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        confirm = await ctx.send("❓ **Are you sure you want to enable custom bot?** (yes/no)")
        try:
            m_conf = await self.bot.wait_for('message', timeout=30.0, check=check)
            if m_conf.content.lower() != "yes": return await ctx.send("❌ Cancelled.")
            await m_conf.delete(); await confirm.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        load = await ctx.send("🔄 **Processing...**")
        await asyncio.sleep(1); await load.edit(content="📡 Requesting......................... - **DONE!**")
        await asyncio.sleep(1); await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**")
        await asyncio.sleep(1); await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**\n💾 Applying........................... - **DONE!**")

        try:
            # We target the specific current bot user context path on the guild endpoint
            url = f"https://discord.com/api/v10/guilds/{ctx.guild.id}/members/@me"
            
            headers = {
                "Authorization": f"Bot {self.bot.http.token}",
                "Content-Type": "application/json"
            }
            
            payload = {}
            if new_name: payload["nick"] = new_name
            if new_bio: payload["description"] = new_bio

            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=payload, headers=headers) as resp:
                    if resp.status == 403:
                        await load.delete()
                        error_details = await resp.text()
                        return await ctx.send(f"❌ **API Rejection (403):** Discord blocked this edit. Details: `{error_details}`")
                    elif resp.status not in [200, 204]:
                        await load.delete()
                        error_details = await resp.text()
                        return await ctx.send(f"❌ **API Error ({resp.status}):** `{error_details}`")
            
            await load.delete()
            await ctx.send("✅ **Bot updated on this guild with success!**\nThanks for using AircraftGames! ✈️")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="premiumcoderegen")
    async def premiumcoderegen(self, ctx, time: str):
        if not await self.check_is_team(ctx):
            return await ctx.send("❌ Only Bot Team members can use this!")

        time = time.lower()
        days = {"1d": 1, "1m": 30, "1y": 365, "10y": 3650}.get(time, 30)
        
        new_code = f"AC-{uuid.uuid4().hex[:8].upper()}"
        await self.codes_db.insert_one({"code": new_code, "duration_days": days, "used": False})
        
        try:
            await ctx.author.send(f"🎟️ **Code**: `{new_code}` ({time})")
            await ctx.send("✅ Sent to DMs.")
        except:
            await ctx.send(f"✅ Code: `{new_code}`")

    @app_commands.command(name="drinkwater", description="Setup hydrations alerts")
    @app_commands.describe(
        channel="Channel to post reminders", 
        fromwheninwhen="Interval in minutes (e.g. 60)", 
        pingeveryone="Ping @everyone (on/off)", 
        pingrole="Specific role to ping"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def drinkwater(
        self, interaction: discord.Interaction, 
        channel: discord.TextChannel, 
        fromwheninwhen: int, 
        pingeveryone: str = "off", 
        pingrole: discord.Role = None
    ):
        ping_ev = pingeveryone.lower() == "on"
        guild_id = interaction.guild_id
        
        self.reminders[guild_id] = {
            "channel_id": channel.id,
            "interval": fromwheninwhen,
            "ping_everyone": ping_ev,
            "ping_role_id": pingrole.id if pingrole else None,
            "last_sent": datetime.datetime.now()
        }
        
        await interaction.response.send_message(f"💧 **Water reminders configured!** Every {fromwheninwhen} minutes in {channel.mention}.")

    @tasks.loop(minutes=1.0)
    async def water_ticker(self):
        now = datetime.datetime.now()
        for guild_id, config in list(self.reminders.items()):
            time_passed = (now - config["last_sent"]).total_seconds() / 60.0
            if time_passed >= config["interval"]:
                channel = self.bot.get_channel(config["channel_id"])
                if channel:
                    content = "💧 **Time to stay hydrated! Drink some water!**"
                    if config["ping_everyone"]:
                        content = f"@everyone {content}"
                    elif config["ping_role_id"]:
                        content = f"<@&{config['ping_role_id']}> {content}"
                    
                    try:
                        await channel.send(content)
                        config["last_sent"] = now
                    except:
                        pass

    @water_ticker.before_loop
    async def before_water_ticker(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(General(bot))
