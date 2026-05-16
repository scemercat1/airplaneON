# cogs/moderation.py

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio

class Moderation(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.db = bot.db

    # =====================================================
    # HELPER
    # =====================================================

    async def get_msg(self, guild_id, type):

        data = await self.db["settings"].find_one({
            "guild_id": str(guild_id)
        })

        return data.get(type) if data else None

    # =====================================================
    # BLACKLIST LISTENER
    # =====================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        if not message.guild:
            return

        data = await self.db["settings"].find_one({
            "guild_id": str(message.guild.id)
        })

        blacklist = (
            data.get("blacklisted_words", [])
            if data else []
        )

        if any(
            word.lower() in message.content.lower()
            for word in blacklist
        ):

            try:

                await message.delete()

                await message.channel.send(
                    (
                        f"{message.author.mention}, "
                        "You said a blacklisted word."
                    ),
                    delete_after=5
                )

            except discord.Forbidden:

                pass

    # =====================================================
    # /blacklistword
    # =====================================================

    @app_commands.command(
        name="blacklistword",
        description="Blacklist a word"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def blacklistword(
        self,
        itx: discord.Interaction,
        word: str
    ):

        word = word.lower()

        await self.db["settings"].update_one(
            {
                "guild_id": str(itx.guild_id)
            },
            {
                "$addToSet": {
                    "blacklisted_words": word
                }
            },
            upsert=True
        )

        await itx.response.send_message(
            f"✅ `{word}` blacklisted.",
            ephemeral=True
        )

    # =====================================================
    # /warn
    # =====================================================

    @app_commands.command(name="warn")
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def warn(
        self,
        itx,
        member: discord.Member,
        reason: str
    ):

        custom = await self.get_msg(
            itx.guild_id,
            "warn"
        )

        msg = (
            custom.replace("{reason}", reason)
            if custom
            else f"Warned for {reason}"
        )

        try:

            await member.send(
                f"⚠️ {msg}"
            )

        except:

            pass

        await itx.response.send_message(
            f"⚠️ Warned {member.mention}"
        )

    # =====================================================
    # /kick
    # =====================================================

    @app_commands.command(name="kick")
    @app_commands.checks.has_permissions(
        kick_members=True
    )
    async def kick(
        self,
        itx,
        member: discord.Member,
        reason: str = "No reason"
    ):

        custom = await self.get_msg(
            itx.guild_id,
            "kick"
        )

        msg = (
            custom.replace("{reason}", reason)
            if custom
            else f"Kicked for {reason}"
        )

        try:

            await member.send(
                f"👞 {msg}"
            )

        except:

            pass

        await member.kick(
            reason=reason
        )

        await itx.response.send_message(
            f"👞 Kicked {member.name}"
        )

    # =====================================================
    # /ban
    # =====================================================

    @app_commands.command(name="ban")
    @app_commands.checks.has_permissions(
        ban_members=True
    )
    async def ban(
        self,
        itx,
        member: discord.Member,
        reason: str = "No reason"
    ):

        await member.ban(
            reason=reason
        )

        await itx.response.send_message(
            f"🔨 Banned {member.name}"
        )

    # =====================================================
    # /timeout
    # =====================================================

    @app_commands.command(name="timeout")
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def timeout(
        self,
        itx,
        member: discord.Member,
        minutes: int,
        reason: str = "No reason"
    ):

        duration = datetime.timedelta(
            minutes=minutes
        )

        await member.timeout(
            duration,
            reason=reason
        )

        await itx.response.send_message(
            f"⏳ Timed out {member.name} for {minutes}m"
        )

    # =====================================================
    # /clear
    # =====================================================

    @app_commands.command(name="clear")
    @app_commands.checks.has_permissions(
        manage_messages=True
    )
    async def clear(
        self,
        itx,
        amount: int
    ):

        await itx.response.defer(
            ephemeral=True
        )

        deleted = await itx.channel.purge(
            limit=amount
        )

        await itx.followup.send(
            f"🧹 Deleted {len(deleted)} messages."
        )

    # =====================================================
    # /slowmode
    # =====================================================

    @app_commands.command(name="slowmode")
    @app_commands.checks.has_permissions(
        manage_channels=True
    )
    async def slowmode(
        self,
        itx,
        seconds: int
    ):

        await itx.channel.edit(
            slowmode_delay=seconds
        )

        await itx.response.send_message(
            f"🐌 Slowmode: {seconds}s"
        )

    # =====================================================
    # /lock
    # =====================================================

    @app_commands.command(name="lock")
    @app_commands.checks.has_permissions(
        manage_channels=True
    )
    async def lock(self, itx):

        await itx.channel.set_permissions(
            itx.guild.default_role,
            send_messages=False
        )

        await itx.response.send_message(
            "🔒 Channel locked."
        )

    # =====================================================
    # /unlock
    # =====================================================

    @app_commands.command(name="unlock")
    @app_commands.checks.has_permissions(
        manage_channels=True
    )
    async def unlock(self, itx):

        await itx.channel.set_permissions(
            itx.guild.default_role,
            send_messages=True
        )

        await itx.response.send_message(
            "🔓 Channel unlocked."
        )

    # =====================================================
    # !owner-2-live-event
    # =====================================================

    @commands.command(name="owner-2-live-event")
    async def owner_2_live_event(self, ctx):

        app = await self.bot.application_info()

        authorized = False

        # OWNER
        if ctx.author.id == app.owner.id:
            authorized = True

        # TEAM MEMBERS
        if app.team:

            for member in app.team.members:

                if member.id == ctx.author.id:
                    authorized = True

        # ADMINS
        if ctx.author.guild_permissions.administrator:
            authorized = True

        if not authorized:

            return await ctx.send(
                "❌ Unauthorized."
            )

        # =================================================
        # STARTUP
        # =================================================

        loading = await ctx.send(
            "```yaml\n"
            "-----------------------\n"
            "--- 📂 Loading Updates ---\n"
            "✅ Loaded: reactroles\n"
            "✅ Loaded: update2.0\n"
            "✅ Loaded: moderation\n"
            "✅ Loaded: premiumcore\n"
            "-----------------------\n"
            "```"
        )

        await asyncio.sleep(4)

        # =================================================
        # BOOT
        # =================================================

        await loading.edit(
            content=
            "```bash\n"
            "Starting Container...\n"
            "Successfully synced all commands.\n"
            "🚀 AircraftGames#1515 is online\n"
            "Connected to MongoDB\n"
            "Status: L£is3n1ng to /corru3pted\n"
            "```"
        )

        await asyncio.sleep(5)

        # =================================================
        # WARNINGS
        # =================================================

        warnings = [

            "```diff\n- websocket instability detected\n```",

            "```ini\n[AircraftCore]\nlatency=893ms\n```",

            "```yaml\nmemory_fragmentation: true\n```",

            "```fix\n[WARN] unknown payload detected\n```"
        ]

        for warn in warnings:

            await ctx.send(warn)

            await asyncio.sleep(2)

        # =================================================
        # WAIT
        # =================================================

        wait_msg = await ctx.send(
            "```Connecting to AircraftNode...```"
        )

        for i in range(60, 0, -10):

            await asyncio.sleep(10)

            try:

                await wait_msg.edit(
                    content=
                    f"```Connecting to AircraftNode... {i}s```"
                )

            except:

                pass

        # =================================================
        # CRASH
        # =================================================

        crash_lines = [

            "Interrupted operation as its client disconnected",

            "Connection ended - MongoDB",

            "Connection ended - AircraftDB",

            "Connection ended",

            "Connection ended - Server",

            "Connection ended - Client",

            "Stopping Container...",

            "Docker Stopped."
        ]

        for line in crash_lines:

            await ctx.send(
                f"```ansi\n{line}\n```"
            )

            await asyncio.sleep(1.5)

        # =================================================
        # HACKER EVENT
        # =================================================

        await asyncio.sleep(3)

        hacker_lines = [

            "01010100 01001000 01000101 01011001",

            "injecting unknown payload...",

            "access granted",

            "bypass successful",

            "AircraftCore breached",

            "who are you?",

            "you were not supposed to see this",

            "restoring hidden archive",

            "memory corruption detected",

            "ERROR ERROR ERROR"
        ]

        for line in hacker_lines:

            await ctx.send(
                f"```{line}```"
            )

            await asyncio.sleep(2)

        # =================================================
        # FINAL EMBED
        # =================================================

        embed = discord.Embed(
            title="█▓▒░ SYSTEM BREACH DETECTED ░▒▓█",
            description=(
                "`origin unknown`\n"
                "`connection unstable`\n"
                "`memory restored`\n\n"
                "An external client "
                "has accessed Aircraft Core."
            ),
            color=0xff0000
        )

        embed.set_footer(
            text="trace failed"
        )

        await ctx.send(embed=embed)

        # =================================================
        # STATIC
        # =================================================

        static = [

            "█ █ █ █ █ █",

            "unknown_client.exe",

            "#$@!$#!@#!@",

            "TRACE FAILED",

            "reconnect? reconnect?",

            "0110010101010101",

            "/// corrupted ///"
        ]

        for s in static:

            await asyncio.sleep(1)

            await ctx.send(
                f"```{s}```"
            )

# =====================================================
# SETUP
# =====================================================

async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
    )
