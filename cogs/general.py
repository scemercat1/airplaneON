import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import uuid
import asyncio

# =========================================================
# INTERACTIVE BUTTON PANELS (MODERN UI)
# =========================================================

class PremiumPanelView(discord.ui.View):
    """Buttons attached to the Premium Observability channel embed"""
    def __init__(self, cog):
        super().__init__(timeout=None)  # Keeps buttons working permanently across bot restarts
        self.cog = cog

    @discord.ui.button(label="💎 Add Premium (Gen Code)", style=discord.Style.green, custom_id="panel_add_premium")
    async def add_premium_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        
        # Generates a quick 30-day code right through the interactive UI
        code = f"AC-{uuid.uuid4().hex[:10].upper()}"
        await self.cog.codes_db.insert_one({"code": code, "days": 30, "used": False})
        await interaction.response.send_message(f"✅ Generated 30-Day Premium Code:\n`{code}`\nUse `/premium` to activate it!", ephemeral=True)

    @discord.ui.button(label="❌ Clear Active Premium Statuses", style=discord.Style.danger, custom_id="panel_remove_premium")
    async def remove_premium_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        await self.cog.guild_db.update_many({"premium": True}, {"$set": {"premium": False}, "$unset": {"expires": ""}})
        await interaction.response.send_message("✅ Wiped all server premium flags from the database.", ephemeral=True)


class CustomInstanceView(discord.ui.View):
    """Buttons attached to the Custom Instances channel embed"""
    def __init__(self, cog):
        super().__init__(timeout=None)  # Keeps buttons working permanently across bot restarts
        self.cog = cog

    @discord.ui.button(label="⚙️ Reset All Nicknames", style=discord.Style.blurple, custom_id="panel_reset_instances")
    async def reset_instances(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.check_is_team(interaction.user.id):
            return await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            
        await self.cog.guild_db.update_many({}, {"$unset": {"custombot_name": ""}})
        await interaction.response.send_message("✅ Cleared custom name profile entries from DB.", ephemeral=True)


# =========================================================
# GENERAL COG
# =========================================================

class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # DATABASES
        self.codes_db = bot.db["premium_codes"]
        self.guild_db = bot.db["guild_data"]
        self.menus_db = bot.db["role_menus"]
        self.config_db = bot.db["system_config"]

        # WATER REMINDERS
        self.water_users = {}

        # COMMAND STATS
        self.command_usage = {}

        self.water_ticker.start()

    # =====================================================
    # COG UNLOAD
    # =====================================================

    def cog_unload(self):
        self.water_ticker.cancel()

    # =====================================================
    # TEAM CHECK
    # =====================================================

    async def check_is_team(self, user_id: int):
        app = await self.bot.application_info()
        if app.team:
            for member in app.team.members:
                if member.id == user_id:
                    return True
        return user_id == app.owner.id

    # =====================================================
    # COMMAND LOGGER
    # =====================================================

    async def register_command_use(self, command_name: str):
        if command_name not in self.command_usage:
            self.command_usage[command_name] = 0
        self.command_usage[command_name] += 1

    # =====================================================
    # OWNER TESTING SERVER SYSTEM
    # =====================================================

    @commands.command(name="owner%testingserver")
    async def owner_testingserver(self, ctx):
        await self.register_command_use("owner%testingserver")

        # SECURITY
        if not await self.check_is_team(ctx.author.id):
            return await ctx.send("❌ Unauthorized.")

        # LIFETIME LIMIT
        usage = await self.config_db.find_one({"type": "testingserver_usage"})
        if not usage:
            await self.config_db.insert_one({"type": "testingserver_usage", "count": 0})
            usage = {"count": 0}

        if usage["count"] >= 3:
            return await ctx.send("❌ Lifetime limit reached.")

        warning = discord.Embed(
            title="⚠️ SERVER TRANSFORMATION",
            description="Deleting all channels and deploying control panels...",
            color=0xe74c3c
        )
        await ctx.send(embed=warning)
        await asyncio.sleep(3)

        guild = ctx.guild

        # DELETE EVERYTHING
        for channel in guild.channels:
            try:
                await channel.delete()
            except:
                pass

        # CREATE CATEGORIES
        testing = await guild.create_category("TESTING")
        hangout = await guild.create_category("HANGOUT")
        observability = await guild.create_category("OBSERVABILITY")

        # TESTING CHANNELS
        await guild.create_text_channel("test-1", category=testing)
        await guild.create_text_channel("test-2", category=testing)
        await guild.create_text_channel("test-3", category=testing)

        # HANGOUT CHANNELS
        await guild.create_text_channel("counting", category=hangout)
        await guild.create_text_channel("games", category=hangout)

        # OBSERVABILITY CHANNELS
        premium_channel = await guild.create_text_channel("premium", category=observability)
        custom_channel = await guild.create_text_channel("custominstances", category=observability)
        info_channel = await guild.create_text_channel("info", category=observability)
        await guild.create_text_channel("lolz", category=observability)
        await guild.create_voice_channel("lolZ2-fr", category=observability)

        # PREMIUM PANEL (WITH INTERACTIVE BUTTON VIEWS ATTACHED)
        premium_embed = discord.Embed(
            title="💎 Premium Observability",
            description="Premium servers & codes database overview.",
            color=0xf1c40f
        )

        premium_servers = []
        async for data in self.guild_db.find({"premium": True}):
            premium_servers.append(f"• {data['guild_id']}")

        premium_codes = []
        async for code in self.codes_db.find():
            premium_codes.append(f"• {code['code']} | Used: {code['used']}")

        premium_embed.add_field(
            name="Servers",
            value="\n".join(premium_servers) if premium_servers else "None",
            inline=False
        )
        premium_embed.add_field(
            name="Codes",
            value="\n".join(premium_codes[:20]) if premium_codes else "None",
            inline=False
        )

        await premium_channel.send(embed=premium_embed, view=PremiumPanelView(self))

        # CUSTOMBOT PANEL (WITH INTERACTIVE BUTTON VIEWS ATTACHED)
        custom_embed = discord.Embed(
            title="🤖 Custom Instances",
            description="Servers utilizing configured instances.",
            color=0x3498db
        )

        custom_servers = []
        async for data in self.guild_db.find({"custombot_name": {"$exists": True}}):
            custom_servers.append(f"• {data['guild_id']} | {data.get('custombot_name')}")

        custom_embed.add_field(
            name="Instances",
            value="\n".join(custom_servers) if custom_servers else "None",
            inline=False
        )

        await custom_channel.send(embed=custom_embed, view=CustomInstanceView(self))

        # INFO PANEL
        total_members = sum(g.member_count for g in self.bot.guilds)
        most_used = "None"
        if self.command_usage:
            most_used = max(self.command_usage, key=self.command_usage.get)

        info_embed = discord.Embed(title="📊 Global Information", color=0x2ecc71)
        info_embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        info_embed.add_field(name="Members", value=str(total_members), inline=True)
        info_embed.add_field(name="Most Used Command", value=most_used, inline=False)

        await info_channel.send(embed=info_embed)

        # UPDATE USAGE
        await self.config_db.update_one({"type": "testingserver_usage"}, {"$inc": {"count": 1}})

    # =====================================================
    # /help COMMAND
    # =====================================================

    @app_commands.command(name="help", description="Aircraft information")
    async def help_command(self, interaction: discord.Interaction):
        await self.register_command_use("/help")

        embed = discord.Embed(title="✈️ Aircraft Bot", description="Premium bot system.", color=0x3498db)
        embed.add_field(name="💎 Premium", value="/premium", inline=False)
        embed.add_field(name="🎭 Roles", value="/rolemenu + /reactionroles", inline=False)
        embed.add_field(name="💧 Water", value="/drinkwater", inline=False)

        await interaction.response.send_message(embed=embed)

    # =====================================================
    # /rolemenu COMMAND
    # =====================================================

    @app_commands.command(name="rolemenu", description="Create a role menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def rolemenu(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        role1: discord.Role,
        emoji1: str,
        role2: discord.Role = None,
        emoji2: str = None,
        role3: discord.Role = None,
        emoji3: str = None
    ):
        await self.register_command_use("/rolemenu")

        data = [{"role_id": role1.id, "emoji": emoji1}]

        if role2 and emoji2:
            data.append({"role_id": role2.id, "emoji": emoji2})
        if role3 and emoji3:
            data.append({"role_id": role3.id, "emoji": emoji3})

        await self.menus_db.update_one(
            {"name": name},
            {"$set": {"description": description, "roles": data}},
            upsert=True
        )

        await interaction.response.send_message(f"✅ Menu `{name}` saved.")

    # =====================================================
    # /reactionroles COMMAND
    # =====================================================

    @app_commands.command(name="reactionroles", description="Deploy reaction roles")
    @app_commands.checks.has_permissions(administrator=True)
    async def reactionroles(self, interaction: discord.Interaction, menu_name: str):
        await self.register_command_use("/reactionroles")

        menu = await self.menus_db.find_one({"name": menu_name})
        if not menu:
            return await interaction.response.send_message("❌ Menu not found.", ephemeral=True)

        embed = discord.Embed(title="🎭 Reaction Roles", description=menu["description"], color=0x9b59b6)
        lines = []

        for role_data in menu["roles"]:
            role = interaction.guild.get_role(role_data["role_id"])
            if role:
                lines.append(f"{role_data['emoji']} — {role.mention}")

        embed.add_field(name="Roles", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"MENU:{menu_name}")

        msg = await interaction.channel.send(embed=embed)

        for role_data in menu["roles"]:
            await msg.add_reaction(role_data["emoji"])

        await interaction.response.send_message("✅ Deployed.", ephemeral=True)

    # =====================================================
    # REACTION LISTENERS (BACKWARDS COMPATIBILITY)
    # =====================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        member = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        if not message.embeds: return
        embed = message.embeds[0]
        if not embed.footer or not embed.footer.text.startswith("MENU:"): return

        menu_name = embed.footer.text.replace("MENU:", "")
        menu = await self.menus_db.find_one({"name": menu_name})
        if not menu: return

        for role_data in menu["roles"]:
            if str(payload.emoji) == role_data["emoji"]:
                role = guild.get_role(role_data["role_id"])
                if role:
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return

        member = guild.get_member(payload.user_id)
        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        if not message.embeds: return
        embed = message.embeds[0]
        if not embed.footer or not embed.footer.text.startswith("MENU:"): return

        menu_name = embed.footer.text.replace("MENU:", "")
        menu = await self.menus_db.find_one({"name": menu_name})
        if not menu: return

        for role_data in menu["roles"]:
            if str(payload.emoji) == role_data["emoji"]:
                role = guild.get_role(role_data["role_id"])
                if role:
                    await member.remove_roles(role)

    # =====================================================
    # /premium COMMAND
    # =====================================================

    @app_commands.command(name="premium", description="Activate premium")
    async def premium(self, interaction: discord.Interaction, code: str):
        await self.register_command_use("/premium")

        db_code = await self.codes_db.find_one({"code": code.upper()})
        if not db_code:
            return await interaction.response.send_message("❌ Invalid code.", ephemeral=True)

        if db_code["used"]:
            return await interaction.response.send_message("❌ Already used.", ephemeral=True)

        expires = datetime.datetime.utcnow() + datetime.timedelta(days=db_code["days"])

        await self.guild_db.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"premium": True, "expires": expires}},
            upsert=True
        )

        await self.codes_db.update_one(
            {"code": code.upper()},
            {"$set": {"used": True}}
        )

        await interaction.response.send_message("✅ Premium activated.")

    # =====================================================
    # !custombot COMMAND
    # =====================================================

    @commands.command(name="custombot")
    async def custombot(self, ctx, *, nickname):
        await self.register_command_use("!custombot")

        data = await self.guild_db.find_one({"guild_id": ctx.guild.id})
        if not data or not data.get("premium"):
            return await ctx.send("❌ Premium required.")

        try:
            await ctx.guild.me.edit(nick=nickname)
            await self.guild_db.update_one(
                {"guild_id": ctx.guild.id},
                {"$set": {"custombot_name": nickname}}
            )
            await ctx.send(f"✅ Changed to `{nickname}`")
        except Exception as e:
            await ctx.send(f"❌ {e}")

    # =====================================================
    # !premiumcoderegen COMMAND
    # =====================================================

    @commands.command(name="premiumcoderegen")
    async def premiumcoderegen(self, ctx, days: int):
        await self.register_command_use("!premiumcoderegen")

        if not await self.check_is_team(ctx.author.id):
            return await ctx.send("❌ Unauthorized.")

        code = f"AC-{uuid.uuid4().hex[:10].upper()}"
        await self.codes_db.insert_one({"code": code, "days": days, "used": False})

        await ctx.send(f"✅ Generated:\n`{code}`")

    # =====================================================
    # /drinkwater COMMAND
    # =====================================================

    @app_commands.command(name="drinkwater", description="Enable hydration reminders")
    async def drinkwater(self, interaction: discord.Interaction):
        await self.register_command_use("/drinkwater")

        self.water_users[interaction.user.id] = {"channel": interaction.channel.id}
        await interaction.response.send_message("💧 Enabled.")

    # =====================================================
    # HYDRATION LOOP
    # =====================================================

    @tasks.loop(minutes=60)
    async def water_ticker(self):
        await self.bot.wait_until_ready()

        for user_id, data in self.water_users.items():
            channel = self.bot.get_channel(data["channel"])
            if not channel: continue
            try:
                user = await self.bot.fetch_user(user_id)
                await channel.send(f"💧 {user.mention} drink water.")
            except:
                pass


# =========================================================
# SETUP FUNCTION
# =========================================================

async def setup(bot):
    await bot.add_cog(General(bot))
