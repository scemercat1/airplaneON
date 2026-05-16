# cogs/general.py

import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import uuid
import asyncio

# =========================================================
# MAIN COG
# =========================================================

class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # DATABASE COLLECTIONS
        self.codes_db = bot.db["premium_codes"]
        self.guild_db = bot.db["guild_data"]
        self.menus_db = bot.db["role_menus"]

        # WATER REMINDER STORAGE
        self.water_users = {}

        self.water_ticker.start()

    # =========================================================
    # COG UNLOAD
    # =========================================================

    def cog_unload(self):
        self.water_ticker.cancel()

    # =========================================================
    # TEAM CHECK
    # =========================================================

    async def check_is_team(self, user_id: int):

        app = await self.bot.application_info()

        if app.team:
            return any(member.id == user_id for member in app.team.members)

        return user_id == app.owner.id

    # =========================================================
    # !owner-testingserver
    # =========================================================

    @commands.command(name="owner-testingserver")
    async def owner_testingserver(self, ctx):

        if not await self.check_is_team(ctx.author.id):
            return await ctx.send("❌ Unauthorized.")

        guild = ctx.guild

        category = await guild.create_category("AIRCRAFT OBSERVABILITY")

        premium_channel = await guild.create_text_channel(
            "premium",
            category=category
        )

        instances_channel = await guild.create_text_channel(
            "custominstances",
            category=category
        )

        logs_channel = await guild.create_text_channel(
            "logs",
            category=category
        )

        embed = discord.Embed(
            title="✅ Observability Ready",
            description="Aircraft observability system deployed.",
            color=0x2ecc71
        )

        await premium_channel.send(embed=embed)
        await instances_channel.send(embed=embed)
        await logs_channel.send(embed=embed)

        await ctx.send("✅ Testing server initialized.")

    # =========================================================
    # /help
    # =========================================================

    @app_commands.command(
        name="help",
        description="Aircraft bot information"
    )
    async def help_command(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="✈️ Aircraft Bot",
            description="Premium automation and moderation system.",
            color=0x3498db
        )

        embed.add_field(
            name="💎 Premium",
            value="Use `/premium` to activate.",
            inline=False
        )

        embed.add_field(
            name="🎭 Reaction Roles",
            value="Use `/rolemenu` then `/reactionroles`.",
            inline=False
        )

        embed.add_field(
            name="💧 Water Reminder",
            value="Use `/drinkwater`.",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # =========================================================
    # /rolemenu
    # =========================================================

    @app_commands.command(
        name="rolemenu",
        description="Create a role menu"
    )
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

        data = []

        data.append({
            "role_id": role1.id,
            "emoji": emoji1
        })

        if role2 and emoji2:
            data.append({
                "role_id": role2.id,
                "emoji": emoji2
            })

        if role3 and emoji3:
            data.append({
                "role_id": role3.id,
                "emoji": emoji3
            })

        await self.menus_db.update_one(
            {"name": name},
            {
                "$set": {
                    "description": description,
                    "roles": data
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Saved role menu `{name}`."
        )

    # =========================================================
    # /reactionroles
    # =========================================================

    @app_commands.command(
        name="reactionroles",
        description="Deploy a saved role menu"
    )
    async def reactionroles(
        self,
        interaction: discord.Interaction,
        menu_name: str
    ):

        menu = await self.menus_db.find_one({
            "name": menu_name
        })

        if not menu:
            return await interaction.response.send_message(
                "❌ Menu not found.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🎭 Reaction Roles",
            description=menu["description"],
            color=0x9b59b6
        )

        lines = []

        for role_data in menu["roles"]:

            role = interaction.guild.get_role(
                role_data["role_id"]
            )

            if role:
                lines.append(
                    f"{role_data['emoji']} — {role.mention}"
                )

        embed.add_field(
            name="Roles",
            value="\n".join(lines),
            inline=False
        )

        embed.set_footer(text=f"MENU:{menu_name}")

        msg = await interaction.channel.send(embed=embed)

        for role_data in menu["roles"]:
            await msg.add_reaction(role_data["emoji"])

        await interaction.response.send_message(
            "✅ Reaction role panel deployed.",
            ephemeral=True
        )

    # =========================================================
    # REACTION ROLE HANDLER
    # =========================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):

        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        channel = guild.get_channel(payload.channel_id)

        message = await channel.fetch_message(payload.message_id)

        if not message.embeds:
            return

        embed = message.embeds[0]

        if not embed.footer.text.startswith("MENU:"):
            return

        menu_name = embed.footer.text.replace("MENU:", "")

        menu = await self.menus_db.find_one({
            "name": menu_name
        })

        if not menu:
            return

        for role_data in menu["roles"]:

            if str(payload.emoji) == role_data["emoji"]:

                role = guild.get_role(
                    role_data["role_id"]
                )

                if role:
                    await member.add_roles(role)

    # =========================================================
    # /premium
    # =========================================================

    @app_commands.command(
        name="premium",
        description="Activate premium"
    )
    async def premium(
        self,
        interaction: discord.Interaction,
        code: str
    ):

        db_code = await self.codes_db.find_one({
            "code": code.upper()
        })

        if not db_code:
            return await interaction.response.send_message(
                "❌ Invalid code.",
                ephemeral=True
            )

        if db_code["used"]:
            return await interaction.response.send_message(
                "❌ Code already used.",
                ephemeral=True
            )

        expires = datetime.datetime.utcnow() + datetime.timedelta(
            days=db_code["days"]
        )

        await self.guild_db.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "premium": True,
                    "expires": expires
                }
            },
            upsert=True
        )

        await self.codes_db.update_one(
            {"code": code.upper()},
            {
                "$set": {
                    "used": True
                }
            }
        )

        await interaction.response.send_message(
            "✅ Premium activated."
        )

    # =========================================================
    # !custombot
    # =========================================================

    @commands.command(name="custombot")
    async def custombot(
        self,
        ctx,
        *,
        nickname
    ):

        data = await self.guild_db.find_one({
            "guild_id": ctx.guild.id
        })

        if not data or not data.get("premium"):
            return await ctx.send(
                "❌ Premium required."
            )

        try:
            await ctx.guild.me.edit(
                nick=nickname
            )

            await ctx.send(
                f"✅ Bot nickname updated to `{nickname}`."
            )

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # =========================================================
    # !premiumcoderegen
    # =========================================================

    @commands.command(name="premiumcoderegen")
    async def premiumcoderegen(
        self,
        ctx,
        days: int
    ):

        if not await self.check_is_team(ctx.author.id):
            return await ctx.send("❌ Unauthorized.")

        code = f"AC-{uuid.uuid4().hex[:10].upper()}"

        await self.codes_db.insert_one({
            "code": code,
            "days": days,
            "used": False
        })

        await ctx.send(
            f"✅ Generated code:\n`{code}`\nDays: `{days}`"
        )

    # =========================================================
    # /drinkwater
    # =========================================================

    @app_commands.command(
        name="drinkwater",
        description="Enable hydration reminders"
    )
    async def drinkwater(
        self,
        interaction: discord.Interaction
    ):

        self.water_users[interaction.user.id] = {
            "channel": interaction.channel.id
        }

        await interaction.response.send_message(
            "💧 Hydration reminders enabled."
        )

    # =========================================================
    # WATER LOOP
    # =========================================================

    @tasks.loop(minutes=60)
    async def water_ticker(self):

        await self.bot.wait_until_ready()

        for user_id, data in self.water_users.items():

            channel = self.bot.get_channel(
                data["channel"]
            )

            if not channel:
                continue

            try:
                user = await self.bot.fetch_user(user_id)

                await channel.send(
                    f"💧 {user.mention} drink water."
                )

            except:
                pass

# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(General(bot))
