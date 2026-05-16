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
# REPLACE ONLY THE !owner-2-live-event COMMAND
# INSIDE moderation.py
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
        "✅ Loaded: eventsystem\n"
        "-----------------------\n"
        "```"
    )

    await asyncio.sleep(3)

    await ctx.send(
        "```bash\n"
        "Starting Container...\n"
        "Successfully synced all commands.\n"
        "🚀 AircraftGames#1515 is online\n"
        "Connected to MongoDB\n"
        "Status: L£is3n1ng to /corru3pted\n"
        "```"
    )

    await asyncio.sleep(3)

    # =================================================
    # WEBHOOKS
    # =================================================

    try:

        fox_webhook = await ctx.channel.create_webhook(
            name="FoxTech"
        )

        cat_webhook = await ctx.channel.create_webhook(
            name="CatMonitor"
        )

        owl_webhook = await ctx.channel.create_webhook(
            name="OwlSecurity"
        )

        glitch_webhook = await ctx.channel.create_webhook(
            name="unknown_client.exe"
        )

    except:

        return await ctx.send(
            "❌ Missing Manage Webhooks permission."
        )

    # =================================================
    # NORMAL SYSTEM CHAT
    # =================================================

    await fox_webhook.send(
        username="FoxTech",
        avatar_url="https://i.imgur.com/4M34hi2.png",
        content="System startup completed."
    )

    await asyncio.sleep(4)

    await cat_webhook.send(
        username="CatMonitor",
        avatar_url="https://i.imgur.com/zQZSWrt.png",
        content="MongoDB latency normal."
    )

    await asyncio.sleep(5)

    await owl_webhook.send(
        username="OwlSecurity",
        avatar_url="https://i.imgur.com/3XjJx7y.png",
        content="Scanning active sessions..."
    )

    await asyncio.sleep(4)

    await fox_webhook.send(
        username="FoxTech",
        avatar_url="https://i.imgur.com/4M34hi2.png",
        content="Everything looks stable today."
    )

    await asyncio.sleep(5)

    await cat_webhook.send(
        username="CatMonitor",
        avatar_url="https://i.imgur.com/zQZSWrt.png",
        content="Small ping spike detected."
    )

    await asyncio.sleep(6)

    await owl_webhook.send(
        username="OwlSecurity",
        avatar_url="https://i.imgur.com/3XjJx7y.png",
        content="Probably Discord API instability."
    )

    await asyncio.sleep(4)

    # =================================================
    # WARNING SIGNS
    # =================================================

    warnings = [

        "```diff\n- websocket instability detected\n```",

        "```ini\n[AircraftCore]\nlatency=1244ms\n```",

        "```yaml\nmemory_fragmentation: true\n```",

        "```fix\n[WARN] unknown payload detected\n```",

        "```diff\n- unauthorized session opened\n```",

        "```yaml\nexternal connection: accepted\n```"
    ]

    for warn in warnings:

        await ctx.send(warn)

        await asyncio.sleep(3)

    # =================================================
    # MORE WEBHOOK CHAT
    # =================================================

    await fox_webhook.send(
        username="FoxTech",
        avatar_url="https://i.imgur.com/4M34hi2.png",
        content="Wait... why is there an external process?"
    )

    await asyncio.sleep(5)

    await owl_webhook.send(
        username="OwlSecurity",
        avatar_url="https://i.imgur.com/3XjJx7y.png",
        content="I found an unknown client connected to AircraftCore."
    )

    await asyncio.sleep(6)

    await cat_webhook.send(
        username="CatMonitor",
        avatar_url="https://i.imgur.com/zQZSWrt.png",
        content="Disconnecting it now..."
    )

    await asyncio.sleep(5)

    # =================================================
    # HACKER ENTERS
    # =================================================

    await glitch_webhook.send(
        username="unknown_client.exe",
        avatar_url="https://i.imgur.com/7x5Fh1A.png",
        content="you can't."
    )

    await asyncio.sleep(7)

    await fox_webhook.send(
        username="FoxTech",
        avatar_url="https://i.imgur.com/4M34hi2.png",
        content="Who are you?"
    )

    await asyncio.sleep(5)

    await glitch_webhook.send(
        username="unknown_client.exe",
        avatar_url="https://i.imgur.com/7x5Fh1A.png",
        content="you left the archive exposed."
    )

    await asyncio.sleep(7)

    await owl_webhook.send(
        username="OwlSecurity",
        avatar_url="https://i.imgur.com/3XjJx7y.png",
        content="Forcefully terminating connection..."
    )

    await asyncio.sleep(6)

    await glitch_webhook.send(
        username="unknown_client.exe",
        avatar_url="https://i.imgur.com/7x5Fh1A.png",
        content="too late"
    )

    await asyncio.sleep(5)

    # =================================================
    # MINI COUNTDOWN
    # =================================================

    for i in [10, 8, 6, 4, 2]:

        await ctx.send(
            f"```Connecting to AircraftNode... {i}s```"
        )

        await asyncio.sleep(4)

    # =================================================
    # CORRUPTION STARTS
    # =================================================

    corruption = [

        "01010100 01001000 01000101 01011001",

        "restoring hidden memory...",

        "injecting payload...",

        "memory corruption detected",

        "AircraftCore breached",

        "trace failed",

        "ERROR ERROR ERROR",

        "███ corrupted ███",

        "WHO ARE YOU",

        "reconnect? reconnect?",

        "/// system failure ///",

        "archive restored",

        "replaying deleted logs",

        "there is no escape",

        "██████████████████"
    ]

    for msg in corruption:

        await ctx.send(
            f"```{msg}```"
        )

        await asyncio.sleep(2)

    # =================================================
    # WEBHOOK ARGUMENT
    # =================================================

    await fox_webhook.send(
        username="FoxTech",
        avatar_url="https://i.imgur.com/4M34hi2.png",
        content="This isn't part of the system..."
    )

    await asyncio.sleep(5)

    await cat_webhook.send(
        username="CatMonitor",
        avatar_url="https://i.imgur.com/zQZSWrt.png",
        content="The deleted logs are restoring themselves."
    )

    await asyncio.sleep(6)

    await owl_webhook.send(
        username="OwlSecurity",
        avatar_url="https://i.imgur.com/3XjJx7y.png",
        content="Disconnect EVERYTHING NOW."
    )

    await asyncio.sleep(5)

    await glitch_webhook.send(
        username="unknown_client.exe",
        avatar_url="https://i.imgur.com/7x5Fh1A.png",
        content="you invited me in."
    )

    await asyncio.sleep(8)

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

        "Docker Stopped.",

        "Attempting emergency recovery...",

        "Recovery failed."
    ]

    for line in crash_lines:

        await ctx.send(
            f"```ansi\n{line}\n```"
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
            "`archive restored`\n\n"
            "Aircraft Core integrity failed.\n"
            "External entity still connected.\n\n"
            "`TRACE FAILED`"
        ),
        color=0xff0000
    )

    embed.set_image(
        url="https://i.imgur.com/3ZUrjUP.gif"
    )

    embed.set_footer(
        text="unknown_client.exe"
    )

    await ctx.send(embed=embed)

    # =================================================
    # FINAL GLITCH SPAM
    # =================================================

    ending = [

        "████████████",

        "do not restart the container",

        "it remembers",

        "01001001 00100000 01010011 01000101 01000101 00100000 01011001 01001111 01010101",

        "trace corrupted",

        "why did you wake it?",

        "/// END CONNECTION ///"
    ]

    for e in ending:

        await ctx.send(
            f"```{e}```"
        )

        await asyncio.sleep(2)

    # =================================================
    # CLEANUP
    # =================================================

    try:

        await fox_webhook.delete()

        await cat_webhook.delete()

        await owl_webhook.delete()

        await glitch_webhook.delete()

    except:

        pass
