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

    # =========================
    # HELPER
    # =========================

    async def get_msg(self, guild_id, type):
        data = await self.db["settings"].find_one({
            "guild_id": str(guild_id)
        })
        return data.get(type) if data else None

    # =========================
    # BLACKLIST LISTENER
    # =========================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not message.guild:
            return

        data = await self.db["settings"].find_one({
            "guild_id": str(message.guild.id)
        })

        blacklist = data.get("blacklisted_words", []) if data else []

        if any(word.lower() in message.content.lower() for word in blacklist):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, you used a blacklisted word.",
                    delete_after=5
                )
            except discord.Forbidden:
                pass

    # =========================
    # COMMANDS
    # =========================

    @app_commands.command(name="blacklistword")
    @app_commands.checks.has_permissions(administrator=True)
    async def blacklistword(self, itx, word: str):

        await self.db["settings"].update_one(
            {"guild_id": str(itx.guild_id)},
            {"$addToSet": {"blacklisted_words": word.lower()}},
            upsert=True
        )

        await itx.response.send_message(f"✅ `{word}` blacklisted.", ephemeral=True)

    @app_commands.command(name="warn")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, itx, member: discord.Member, reason: str):

        await member.send(f"⚠️ Warned: {reason}")
        await itx.response.send_message(f"Warned {member.mention}")

    @app_commands.command(name="kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, itx, member: discord.Member, reason: str = "No reason"):

        try:
            await member.send(f"👞 Kicked: {reason}")
        except:
            pass

        await member.kick(reason=reason)
        await itx.response.send_message(f"Kicked {member.name}")

    @app_commands.command(name="ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, itx, member: discord.Member, reason: str = "No reason"):

        await member.ban(reason=reason)
        await itx.response.send_message(f"Banned {member.name}")

    @app_commands.command(name="timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, itx, member: discord.Member, minutes: int, reason: str = "No reason"):

        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await itx.response.send_message(f"Timed out {member.name} for {minutes}m")

    @app_commands.command(name="clear")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, itx, amount: int):

        await itx.response.defer(ephemeral=True)
        deleted = await itx.channel.purge(limit=amount)
        await itx.followup.send(f"Deleted {len(deleted)} messages")

    @app_commands.command(name="slowmode")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, itx, seconds: int):

        await itx.channel.edit(slowmode_delay=seconds)
        await itx.response.send_message(f"Slowmode: {seconds}s")

    @app_commands.command(name="lock")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, itx):

        await itx.channel.set_permissions(itx.guild.default_role, send_messages=False)
        await itx.response.send_message("Channel locked")

    @app_commands.command(name="unlock")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, itx):

        await itx.channel.set_permissions(itx.guild.default_role, send_messages=True)
        await itx.response.send_message("Channel unlocked")

    # =====================================================
    # 🔥 LIVE EVENT (SAFE CINEMATIC VERSION)
    # =====================================================

    @commands.command(name="owner-2-live-event")
    async def owner_2_live_event(self, ctx):

        app = await self.bot.application_info()

        # AUTH CHECK
        if ctx.author.id != app.owner.id and not ctx.author.guild_permissions.administrator:
            if app.team:
                if ctx.author.id not in [m.id for m in app.team.members]:
                    return await ctx.send("❌ Unauthorized.")
            else:
                return await ctx.send("❌ Unauthorized.")

        # START SCREEN
        msg = await ctx.send("```yaml\nSYSTEM INITIALIZING...\nLOADING MODULES...\n```")

        await asyncio.sleep(3)

        await msg.edit(content="```bash\nSYSTEM ONLINE\nMONGO CONNECTED\nDISCORD SYNC OK\nSTATUS: STABLE\n```")

        await asyncio.sleep(3)

        # WEBHOOKS (ANIMAL AI NODES ONLY)
        try:
            fox = await ctx.channel.create_webhook(name="FoxNode 🦊")
            cat = await ctx.channel.create_webhook(name="CatCore 🐱")
            owl = await ctx.channel.create_webhook(name="OwlWatch 🦉")
            rabbit = await ctx.channel.create_webhook(name="RabbitAI 🐰")
        except:
            return await ctx.send("❌ Missing webhook permission.")

        # PHASE 1
        await fox.send("System stable 🦊")
        await asyncio.sleep(3)

        await cat.send("Memory OK 🐱")
        await asyncio.sleep(3)

        await owl.send("Security clean 🦉")
        await asyncio.sleep(3)

        await rabbit.send("Latency normal 🐰")

        await asyncio.sleep(4)

        # PHASE 2
        warn = await ctx.send("```diff\n- minor anomaly detected\n```")

        await asyncio.sleep(4)

        await fox.send("Spike detected...")
        await asyncio.sleep(3)

        await owl.send("Tracing unknown traffic...")
        await asyncio.sleep(3)

        await cat.send("System still stable... for now.")

        await asyncio.sleep(4)

        # PHASE 3
        await warn.edit(content="```diff\n- ANOMALY INCREASING\n- CORE INSTABILITY\n```")

        await asyncio.sleep(4)

        await rabbit.send("Something is inside the system.")
        await asyncio.sleep(4)

        await fox.send("External access detected.")
        await asyncio.sleep(4)

        await owl.send("Tracing failed.")

        await asyncio.sleep(4)

        # PHASE 4
        glitch = await ctx.send("```fix\n[UNKNOWN ENTITY DETECTED]\n```")

        await asyncio.sleep(5)

        await glitch.edit(content="```yaml\nENTITY: unknown_client.exe\nSTATUS: ACTIVE\n```")

        await asyncio.sleep(5)

        await fox.send("It is rewriting logs.")
        await asyncio.sleep(4)

        await cat.send("We are losing control.")
        await asyncio.sleep(4)

        await owl.send("Disconnect NOW.")

        await asyncio.sleep(4)

        # FINAL
        embed = discord.Embed(
            title="SYSTEM BREACH",
            description="External entity integrated into core system.",
            color=0xff0000
        )

        await ctx.send(embed=embed)

        # CLEANUP
        try:
            await fox.delete()
            await cat.delete()
            await owl.delete()
            await rabbit.delete()
        except:
            pass


async def setup(bot):
    await bot.add_cog(Moderation(bot))
