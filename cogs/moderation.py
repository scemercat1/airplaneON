# cogs/moderation.py

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import random

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

        try:

            await member.send(
                f"👞 Kicked for {reason}"
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
    # LIVE EVENT
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

        await ctx.send(
            "```yaml\n"
            "-----------------------\n"
            "--- 📂 Loading Updates ---\n"
            "✅ Loaded: reactroles\n"
            "✅ Loaded: update2.0\n"
            "✅ Loaded: moderation\n"
            "✅ Loaded: premiumcore\n"
            "✅ Loaded: observability\n"
            "-----------------------\n"
            "```"
        )

        await asyncio.sleep(2)

        await ctx.send(
            "```bash\n"
            "Starting Container...\n"
            "Successfully synced all commands.\n"
            "🚀 AircraftGames#1515 is online\n"
            "Connected to MongoDB\n"
            "Status: L£is3n1ng to /corru3pted\n"
            "```"
        )

        await asyncio.sleep(2)

        # =================================================
        # TECHNICIAN WEBHOOKS
        # =================================================

        try:

            webhook = await ctx.channel.create_webhook(
                name="Aircraft Tech"
            )

        except:

            return await ctx.send(
                "❌ Missing Manage Webhooks permission."
            )

        tech_messages = [

            (
                "TechSupport.exe",
                "https://i.imgur.com/6RKk4hG.png",
                "Everything looks stable."
            ),

            (
                "Database Monitor",
                "https://i.imgur.com/fYqMHYQ.png",
                "MongoDB ping rising..."
            ),

            (
                "Container Watcher",
                "https://i.imgur.com/8Km9tLL.png",
                "Wait... why is latency spiking?"
            ),

            (
                "TechSupport.exe",
                "https://i.imgur.com/6RKk4hG.png",
                "Probably just Discord API."
            ),

            (
                "Database Monitor",
                "https://i.imgur.com/fYqMHYQ.png",
                "No... something connected."
            ),

            (
                "Container Watcher",
                "https://i.imgur.com/8Km9tLL.png",
                "Unknown external session detected."
            )
        ]

        for username, avatar, content in tech_messages:

            await webhook.send(
                content=content,
                username=username,
                avatar_url=avatar
            )

            await asyncio.sleep(2)

        # =================================================
        # SYSTEM WARNINGS
        # =================================================

        warnings = [

            "```diff\n- websocket instability detected\n```",

            "```ini\n[AircraftCore]\nlatency=932ms\n```",

            "```yaml\nmemory_fragmentation: true\n```",

            "```fix\n[WARN] unknown payload detected\n```",

            "```diff\n- unauthorized session opened\n```"
        ]

        for warn in warnings:

            await ctx.send(warn)

            await asyncio.sleep(1.5)

        # =================================================
        # SHORT COUNTDOWN
        # =================================================

        for i in range(15, 0, -5):

            await ctx.send(
                f"```Connecting to AircraftNode... {i}s```"
            )

            await asyncio.sleep(2)

        # =================================================
        # HACKER ENTERS
        # =================================================

        hacker_messages = [

            (
                "unknown_client.exe",
                "https://i.imgur.com/t8dAqQp.png",
                "hello?"
            ),

            (
                "TechSupport.exe",
                "https://i.imgur.com/6RKk4hG.png",
                "Who connected?"
            ),

            (
                "unknown_client.exe",
                "https://i.imgur.com/t8dAqQp.png",
                "you left the ports open."
            ),

            (
                "Container Watcher",
                "https://i.imgur.com/8Km9tLL.png",
                "Disconnecting unknown user..."
            ),

            (
                "unknown_client.exe",
                "https://i.imgur.com/t8dAqQp.png",
                "too late"
            ),

            (
                "unknown_client.exe",
                "https://i.imgur.com/t8dAqQp.png",
                "I already restored the archive."
            )
        ]

        for username, avatar, content in hacker_messages:

            await webhook.send(
                content=content,
                username=username,
                avatar_url=avatar
            )

            await asyncio.sleep(2)

        # =================================================
        # CRASH
        # =================================================

        crash_lines = [

            "Interrupted operation as its client disconnected",

            "Connection ended - MongoDB",

            "Connection ended - AircraftDB",

            "Connection ended - Server",

            "Connection ended - Client",

            "Stopping Container...",

            "Docker Stopped."
        ]

        for line in crash_lines:

            await ctx.send(
                f"```ansi\n{line}\n```"
            )

            await asyncio.sleep(1)

        # =================================================
        # CORRUPTION
        # =================================================

        corruption = [

            "01010100 01001000 01000101 01011001",

            "injecting payload...",

            "restoring hidden memory...",

            "memory corruption detected",

            "AircraftCore breached",

            "trace failed",

            "ERROR ERROR ERROR",

            "███ corrupted ███",

            "WHO ARE YOU",

            "reconnect? reconnect?",

            "/// system failure ///"
        ]

        for msg in corruption:

            await ctx.send(
                f"```{msg}```"
            )

            await asyncio.sleep(1.5)

        # =================================================
        # FINAL EMBED
        # =================================================

        embed = discord.Embed(
            title="█▓▒░ SYSTEM BREACH DETECTED ░▒▓█",
            description=(
                "`origin unknown`\n"
                "`connection unstable`\n"
                "`archive restored`\n\n"
                "Aircraft Core integrity failed.\n"
                "External entity still connected."
            ),
            color=0xff0000
        )

        embed.set_image(
            url="https://i.imgur.com/3ZUrjUP.gif"
        )

        embed.set_footer(
            text="trace failed"
        )

        await ctx.send(embed=embed)

        # =================================================
        # DELETE WEBHOOK
        # =================================================

        try:

            await webhook.delete()

        except:

            pass

# =====================================================
# SETUP
# =====================================================

async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
    )
