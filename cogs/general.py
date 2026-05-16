import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import uuid
import aiohttp
import asyncio

# ==================== VIEW INTERFACES FOR OBSERVABILITY SYSTEM ====================

class PremiumManageView(discord.ui.View):
    """Handles the active button controls inside the #premium observability channel"""
    def __init__(self, cog):
        super().__init__(timeout=None) # Persistent view
        self.cog = cog

    @discord.ui.button(label="Cancel Server Premium", style=discord.ButtonStyle.danger, custom_id="obs_cancel_premium")
    async def cancel_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        modal = GuildIDInputModal(self.cog, action="cancel_premium")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Modify/Create Code", style=discord.ButtonStyle.success, custom_id="obs_modify_code")
    async def modify_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        modal = CodeInputModal(self.cog)
        await interaction.response.send_modal(modal)


class CustomInstanceView(discord.ui.View):
    """Handles moderation overrides inside the #custominstances observability channel"""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Override Bot Info (ToS enforcement)", style=discord.ButtonStyle.primary, custom_id="obs_override_bot")
    async def override_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        modal = GuildIDInputModal(self.cog, action="override_profile")
        await interaction.response.send_modal(modal)


# ==================== INTERACTIVE DATA ENTRY MODALS ====================

class GuildIDInputModal(discord.ui.Modal, title="Target Guild Identification"):
    guild_id = discord.ui.TextInput(label="Enter Guild ID", placeholder="123456789012345678")
    
    def __init__(self, cog, action):
        super().__init__()
        self.cog = cog
        self.action = action

    async def on_submit(self, interaction: discord.Interaction):
        g_id = self.guild_id.value.strip()
        
        if self.action == "cancel_premium":
            await self.cog.guild_db.update_one({"guild_id": g_id}, {"$set": {"premium": False}})
            await interaction.response.send_message(f"✅ Premium stripped from guild: `{g_id}`.", ephemeral=True)
            await self.cog.update_observability_channels()
            
        elif self.action == "override_profile":
            modal = ProfileOverrideModal(self.cog, g_id)
            await interaction.response.send_modal(modal)


class ProfileOverrideModal(discord.ui.Modal, title="Emergency Profile Override"):
    new_name = discord.ui.TextInput(label="Reset Name (Type 'skip' to keep)", default="Reset Bot Name")
    new_bio = discord.ui.TextInput(label="Reset Bio (Type 'skip' to keep)", default="Reset Bot Bio", style=discord.TextStyle.paragraph)

    def __init__(self, cog, target_guild_id):
        super().__init__()
        self.cog = cog
        self.target_guild_id = target_guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        url = f"https://discord.com/api/v10/guilds/{self.target_guild_id}/members/@me"
        headers = {"Authorization": f"Bot {self.cog.bot.http.token}", "Content-Type": "application/json"}
        
        payload = {}
        if self.new_name.value.lower() != "skip": payload["nick"] = self.new_name.value
        if self.new_bio.value.lower() != "skip": payload["bio"] = self.new_bio.value

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers) as resp:
                if resp.status in [200, 204]:
                    await interaction.followup.send(f"✅ Executed override on guild `{self.target_guild_id}`.", ephemeral=True)
                else:
                    err = await resp.text()
                    await interaction.followup.send(f"❌ API Failure ({resp.status}): `{err}`", ephemeral=True)
        await self.cog.update_observability_channels()


class CodeInputModal(discord.ui.Modal, title="Code Generation Matrix"):
    code = discord.ui.TextInput(label="Code (Leave blank for random generation)", required=False, placeholder="AC-PREMIUMV2")
    days = discord.ui.TextInput(label="Duration (in days)", default="30")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        final_code = self.code.value.strip().upper() if self.code.value else f"AC-{uuid.uuid4().hex[:8].upper()}"
        try:
            day_count = int(self.days.value)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid day value format.", ephemeral=True)

        await self.cog.codes_db.update_one(
            {"code": final_code},
            {"$set": {"duration_days": day_count, "used": False}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Generated Code: `{final_code}` for `{day_count}` days.", ephemeral=True)
        await self.cog.update_observability_channels()


# ==================== MAIN GENERAL COG SYSTEM ====================

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.codes_db = self.bot.db["premium_codes"]
        self.guild_db = self.bot.db["guild_data"]
        self.menus_db = self.bot.db["role_menus"] 
        self.reminders = {}
        self.water_ticker.start()
        self.obs_channels = {} 

    def cog_unload(self):
        self.water_ticker.cancel()

    async def check_is_team(self, ctx_or_interaction):
        author = ctx_or_interaction.author if hasattr(ctx_or_interaction, 'author') else ctx_or_interaction.user
        app_info = await self.bot.application_info()
        if app_info.team:
            return any(m.id == author.id for m in app_info.team.members)
        return author.id == app_info.owner.id

    @app_commands.command(name="help", description="Information about Aircraft Bot")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✈️ Aircraft Games - Info", 
            description="Aircraft Games is a high-performance premium bot.",
            color=0x3498db
        )
        embed.add_field(name="🌐 Dashboard", value="Manage everything online.", inline=False)
        embed.add_field(name="💎 Premium", value="Use `!custombot` to customize your bot!", inline=False)
        embed.add_field(name="🎭 Reaction Roles", value="Use `/rolemenu` to save configuration, then deploy using `/reactionroles`.", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rolemenu", description="Create and save a reusable server role menu template")
    @app_commands.describe(
        name="Unique identifier name for this template",
        description="The description displayed above choices",
        role1="First Role", emoji1="Emoji for first role",
        role2="Second Role", emoji2="Emoji for second role",
        role3="Third Role", emoji3="Emoji for third role",
        role4="Fourth Role", emoji4="Emoji for fourth role"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def rolemenu_create(
        self, interaction: discord.Interaction, 
        name: str, description: str, 
        role1: discord.Role, emoji1: str,
        role2: discord.Role = None, emoji2: str = None,
        role3: discord.Role = None, emoji3: str = None,
        role4: discord.Role = None, emoji4: str = None
    ):
        raw_pairs = [(role1, emoji1), (role2, emoji2), (role3, emoji3), (role4, emoji4)]
        roles_data = []

        for role, emoji in raw_pairs:
            if role and emoji:
                roles_data.append({
                    "role_id": role.id,
                    "emoji": emoji.strip()
                })

        menu_name_clean = name.lower().strip()
        await self.menus_db.update_one(
            {"guild_id": str(interaction.guild_id), "menu_name": menu_name_clean},
            {"$set": {
                "description": description,
                "roles": roles_data
            }},
            upsert=True
        )
        await interaction.response.send_message(f"💾 **Template saved to database!** Use `/reactionroles template_name: {menu_name_clean}` to print it out.", ephemeral=True)

    @app_commands.command(name="reactionroles", description="Deploy a saved configuration template to this channel")
    @app_commands.describe(template_name="The configuration name you saved using /rolemenu")
    @app_commands.checks.has_permissions(administrator=True)
    async def reactionroles_deploy(self, interaction: discord.Interaction, template_name: str):
        menu_name_clean = template_name.lower().strip()
        
        menu_data = await self.menus_db.find_one({
            "guild_id": str(interaction.guild_id), 
            "menu_name": menu_name_clean
        })

        if not menu_data:
            return await interaction.response.send_message(f"❌ Could not find a template layout named `{template_name}` on this server.", ephemeral=True)

        embed = discord.Embed(
            title=f"🎭 {template_name.title()} Roles", 
            description=menu_data["description"], 
            color=0x2ecc71
        )
        
        value_text = ""
        for item in menu_data["roles"]:
            value_text += f"{item['emoji']} - <@&{item['role_id']}>\n"
        
        embed.add_field(name="Select your options below:", value=value_text, inline=False)
        embed.set_footer(text=f"Aircraft Games System | ID: {menu_name_clean}")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for item in menu_data["roles"]:
            try:
                await msg.add_reaction(item["emoji"])
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        channel = guild.get_channel(payload.channel_id)
        if not channel: return

        try:
            msg = await channel.fetch_message(payload.message_id)
        except Exception: return

        if not msg.embeds or not msg.footer.text or "Aircraft Games System | ID:" not in msg.footer.text:
            return

        template_name = msg.footer.text.split("ID: ")[1].strip()

        menu_data = await self.menus_db.find_one({
            "guild_id": str(payload.guild_id), 
            "menu_name": template_name
        })
        if not menu_data: return

        member = guild.get_member(payload.user_id)
        if not member:
            try: member = await guild.fetch_member(payload.user_id)
            except Exception: return

        emoji_str = str(payload.emoji)
        
        for item in menu_data["roles"]:
            if item["emoji"] == emoji_str:
                role = guild.get_role(item["role_id"])
                if role:
                    try:
                        if role in member.roles:
                            await member.remove_roles(role)
                        else:
                            await member.add_roles(role)
                    except Exception:
                        pass
                    
                    try:
                        await msg.remove_reaction(payload.emoji, member)
                    except Exception:
                        pass
                break

    # ==================== CRITICAL SYSTEM AUTO-BUILD COMMAND CENTER ====================
    @commands.command(name="owner-testingserver")
    async def owner_testingserver(self, ctx):
        if not await self.check_is_team(ctx):
            return await ctx.send("❌ Access Denied: Core Developers and Admins only.")

        tracker = await self.guild_db.find_one({"_id": "global_debug_tracker"})
        use_count = tracker.get("count", 0) if tracker else 0

        if use_count >= 3:
            return await ctx.send("❌ **CRITICAL LIMIT REACHED:** This initialization block has already been executed 3 times globally across its operational lifetime.")

        await ctx.send("⚠️ **CRITICAL WARNING:** Running this command will **PERMANENTLY NUKE** every channel and category inside this server to format it into an active observability hub.\nType `CONFIRM_NUKE` within 15 seconds to proceed.")
        
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM_NUKE"
        try:
            await self.bot.wait_for('message', timeout=15.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("❌ Execution aborted. Confirmation timeout.")

        await self.guild_db.update_one(
            {"_id": "global_debug_tracker"},
            {"$inc": {"count": 1}},
            upsert=True
        )

        await ctx.send("⚡ *Formatting data tracks... Wiping server matrix...*")

        for channel in ctx.guild.channels:
            try: await channel.delete()
            except Exception: pass

        cat_testing = await ctx.guild.create_category("Testing")
        cat_hangout = await ctx.guild.create_category("Hangout")
        cat_obs = await ctx.guild.create_category("Observability")

        await ctx.guild.create_text_channel("test-1", category=cat_testing)
        await ctx.guild.create_text_channel("test-2", category=cat_testing)
        await ctx.guild.create_text_channel("test-3", category=cat_testing)

        await ctx.guild.create_text_channel("counting", category=cat_hangout)
        await ctx.guild.create_text_channel("games", category=cat_hangout)

        ch_premium = await ctx.guild.create_text_channel("premium", category=cat_obs)
        ch_instances = await ctx.guild.create_text_channel("custominstances", category=cat_obs)
        ch_info = await ctx.guild.create_text_channel("info", category=cat_obs)
        
        await ctx.guild.create_text_channel("lolz", category=cat_obs)
        await ctx.guild.create_voice_channel("lolZ2-fr", category=cat_obs)

        self.obs_channels = {
            "premium": ch_premium.id,
            "instances": ch_instances.id,
            "info": ch_info.id
        }

        await self.update_observability_channels()

    async def update_observability_channels(self):
        if not self.obs_channels:
            return

        # PANEL 1: #PREMIUM
        ch_premium = self.bot.get_channel(self.obs_channels.get("premium"))
        if ch_premium:
            await ch_premium.purge(limit=10)
            embed = discord.Embed(title="🌐 Core Data Observability: Premium Clusters", color=0x9b59b6, timestamp=datetime.datetime.now())
            
            premium_guilds = []
            async for doc in self.guild_db.find({"premium": True}):
                premium_guilds.append(f"• **Guild ID:** `{doc['guild_id']}` (Expires: {doc.get('premium_expiry', 'Never')})")
            
            available_codes = []
            async for doc in self.codes_db.find({"used": False}):
                available_codes.append(f"• `{doc['code']}` ({doc['duration_days']} Days)")

            embed.add_field(name="💎 Premium Active Guilds", value="\n".join(premium_guilds) if premium_guilds else "No Active Premium Instances.", inline=False)
            embed.add_field(name="🎟️ Unused Database Codes", value="\n".join(available_codes) if available_codes else "No Available Codes.", inline=False)
            await ch_premium.send(embed=embed, view=PremiumManageView(self))

        # PANEL 2: #CUSTOMINSTANCES
        ch_instances = self.bot.get_channel(self.obs_channels.get("instances"))
        if ch_instances:
            await ch_instances.purge(limit=10)
            embed = discord.Embed(title="🛡️ ToS Monitoring Module: Active Profiles", color=0xe67e22)
            
            active_profiles = []
            async for doc in self.guild_db.find({"premium": True}):
                g_id = doc.get("guild_id")
                guild_obj = self.bot.get_guild(int(g_id)) if g_id else None
                if guild_obj and guild_obj.me.nick:
                    active_profiles.append(f"• **Guild:** {guild_obj.name} (`{g_id}`)\n  ↳ **Current Nick:** `{guild_obj.me.nick}`")

            embed.description = "\n\n".join(active_profiles) if active_profiles else "No active custom profile instances online."
            await ch_instances.send(embed=embed, view=CustomInstanceView(self))

        # PANEL 3: #INFO
        ch_info = self.bot.get_channel(self.obs_channels.get("info"))
        if ch_info:
            await ch_info.purge(limit=10)
            embed = discord.Embed(title="📊 Cluster Runtime Diagnostics", color=0x34495e)
            embed.add_field(name="📡 Server Connection Footprint", value=f"`{len(self.bot.guilds)} servers`")
            embed.add_field(name="👥 Total Reach Metrics", value=f"`{sum(g.member_count for g in self.bot.guilds if g.member_count)} members`")
            await ch_info.send(embed=embed)

    # ==================== PREMIUM HANDLING CORE ====================
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

        p2 = await ctx.send("📝 **Bio:** Tell us your new bio - Max 190 chars (or type 'skip')")
        try:
            m_bio = await self.bot.wait_for('message', timeout=60.0, check=check)
            new_bio = m_bio.content if m_bio.content.lower() != "skip" else None
            if new_bio and len(new_bio) > 190:
                return await ctx.send("❌ Bio is too long! Discord caps per-guild bios at 190 characters.")
            await m_bio.delete(); await p2.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        confirm = await ctx.send("❓ **Are you sure you want to apply these custom profile changes?** (yes/no)")
        try:
            m_conf = await self.bot.wait_for('message', timeout=30.0, check=check)
            if m_conf.content.lower() != "yes": return await ctx.send("❌ Cancelled.")
            await m_conf.delete(); await confirm.delete()
        except asyncio.TimeoutError: return await ctx.send("❌ Timed out.")

        load = await ctx.send("🔄 **Processing...**")
        await asyncio.sleep(0.5); await load.edit(content="📡 Requesting......................... - **DONE!**")
        await asyncio.sleep(0.5); await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**")
        await asyncio.sleep(0.5); await load.edit(content="📡 Requesting......................... - **DONE!**\n🔍 Analyzing........................... - **DONE!**\n💾 Applying........................... - **DONE!**")

        try:
            url = f"https://discord.com/api/v10/guilds/{ctx.guild.id}/members/@me"
            headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
            
            payload = {}
            if new_name: payload["nick"] = new_name
            if new_bio: payload["bio"] = new_bio

            if not payload:
                await load.delete()
                return await ctx.send("ℹ️ No updates were provided. Profile left unchanged.")

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
            await ctx.send("✅ **Bot profile updated on this guild with success!**\nThanks for using AircraftGames! ✈️")
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

    # ==================== AUTOMATED TICKERS & UTILITIES ====================
    @app_commands.command(name="drinkwater", description="Setup hydration alerts")
    @app_commands.describe(channel="Channel to post reminders", fromwheninwhen="Interval in minutes (e.g. 60)", pingeveryone="Ping @everyone (on/off)", pingrole="Specific role to ping")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def drinkwater(self, interaction: discord.Interaction, channel: discord.TextChannel, fromwheninwhen: int, pingeveryone: str = "off", pingrole: discord.Role = None):
        ping_ev = pingeveryone.lower() == "on"
        self.reminders[interaction.guild_id] = {
            "channel_id": channel.id, "interval": fromwheninwhen, "ping_everyone": ping_ev,
            "ping_role_id": pingrole.id if pingrole else None, "last_sent": datetime.datetime.now()
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
                    if config["ping_everyone"]: content = f"@everyone {content}"
                    elif config["ping_role_id"]: content = f"<@&{config['ping_role_id']}> {content}"
                    try:
                        await channel.send(content)
                        config["last_sent"] = now
                    except: pass

    @water_ticker.before_loop
    async def before_water_ticker(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(General(bot))
