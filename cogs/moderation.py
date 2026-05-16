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
    # HELPERS
    # =====================================================

    async def get_msg(self, guild_id, type):
        data = await self.db["settings"].find_one({
            "guild_id": str(guild_id)
        })
        return data.get(type) if data else None

    # =====================================================
    # BLACKLIST SYSTEM
    # =====================================================

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
                    f"{message.author.mention}, blacklisted word detected.",
                    delete_after=5
                )
            except:
                pass

    # =====================================================
    # MODERATION COMMANDS
    # =====================================================

    @app_commands.command(name="warn")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, itx: discord.Interaction, member: discord.Member, reason: str):
        # Fetch custom warn message from dashboard settings
        custom_msg = await self.get_msg(itx.guild.id, "warn_message")
        
        if custom_msg:
            # Replaces placeholders if your dashboard supports them
            dm_text = custom_msg.replace("{reason}", reason).replace("{guild}", itx.guild.name)
        else:
            dm_text = f"⚠️ Warned in {itx.guild.name}: {reason}"

        try:
            await member.send(dm_text)
        except:
            pass

        await itx.response.send_message(f"Warned {member.mention}")

    @app_commands.command(name="kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, itx: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        # Fetch custom kick message from dashboard settings
        custom_msg = await self.get_msg(itx.guild.id, "kick_message")
        
        if custom_msg:
            dm_text = custom_msg.replace("{reason}", reason).replace("{guild}", itx.guild.name)
        else:
            dm_text = f"👞 Kicked from {itx.guild.name}: {reason}"

        try:
            await member.send(dm_text)
            # Short buffer delay to allow the DM packet to send before breaking connection
            await asyncio.sleep(0.5)
        except:
            pass

        await member.kick(reason=reason)
        await itx.response.send_message(f"Kicked {member.name}")

    @app_commands.command(name="ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, itx: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        # Fetch custom ban message from dashboard settings
        custom_msg = await self.get_msg(itx.guild.id, "ban_message")
        
        if custom_msg:
            dm_text = custom_msg.replace("{reason}", reason).replace("{guild}", itx.guild.name)
        else:
            dm_text = f"🔨 Banned from {itx.guild.name}: {reason}"

        try:
            await member.send(dm_text)
            await asyncio.sleep(0.5)
        except:
            pass

        await member.ban(reason=reason)
        await itx.response.send_message(f"Banned {member.name}")

    @app_commands.command(name="timeout")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, itx: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
        # Fetch custom timeout message from dashboard settings
        custom_msg = await self.get_msg(itx.guild.id, "timeout_message")
        
        if custom_msg:
            dm_text = custom_msg.replace("{reason}", reason).replace("{minutes}", str(minutes)).replace("{guild}", itx.guild.name)
        else:
            dm_text = f"⏳ Timed out in {itx.guild.name} for {minutes}m: {reason}"

        try:
            await member.send(dm_text)
        except:
            pass

        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await itx.response.send_message(f"Timed out {member.name}")

    @app_commands.command(name="clear")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, itx: discord.Interaction, amount: int):
        await itx.response.defer(ephemeral=True)
        deleted = await itx.channel.purge(limit=amount)
        await itx.followup.send(f"Deleted {len(deleted)} messages")

    # =====================================================
    # 🔥 LIVE EVENT (CINEMATIC STORY VERSION)
    # =====================================================

    @commands.command(name="owner-2-live-event")
    async def owner_2_live_event(self, ctx):

        app = await self.bot.application_info()

        # AUTH
        if ctx.author.id != app.owner.id and not ctx.author.guild_permissions.administrator:
            if app.team:
                if ctx.author.id not in [m.id for m in app.team.members]:
                    return await ctx.send("❌ Unauthorized.")
            else:
                return await ctx.send("❌ Unauthorized.")

        # =====================================================
        # INTRO SYSTEM LOG
        # =====================================================

        await ctx.send(
            "```yaml\n"
            "AircraftGames CORE INITIALIZING...\n"
            "Loading Observability Layer...\n"
            "Loading Security Nodes...\n"
            "Loading AI Systems...\n"
            "```"
        )

        await asyncio.sleep(3)

        await ctx.send(
            "```bash\n"
            "SYSTEM ONLINE\n"
            "MongoDB CONNECTED\n"
            "Discord Gateway STABLE\n"
            "Status: Monitoring active systems\n"
            "```"
        )

        await asyncio.sleep(3)

        # =====================================================
        # WEBHOOK CHARACTERS (WITH IMAGES)
        # =====================================================

        try:
            technician = await ctx.channel.create_webhook(name="Technician 🧑‍💻")
            fox = await ctx.channel.create_webhook(name="FoxCore 🦊")
            owl = await ctx.channel.create_webhook(name="OwlSecurity 🦉")
            cat = await ctx.channel.create_webhook(name="CatMonitor 🐱")
            hacker = await ctx.channel.create_webhook(name="UNKNOWN.exe 💀")
        except:
            return await ctx.send("❌ Missing Manage Webhooks permission.")

        # Avatar images (animals only + hacker icon)
        FOX_IMG = "https://i.imgur.com/4M34hi2.png"
        OWL_IMG = "https://i.imgur.com/3XjJx7y.png"
        CAT_IMG = "https://i.imgur.com/vHejcai.jpeg"
        TECH_IMG = "https://i.imgur.com/1X7Q8bM.png"
        HACK_IMG = "https://i.imgur.com/Tizs4QC.jpeg"

        # =====================================================
        # PHASE 1 - NORMAL SYSTEM
        # =====================================================

        await fox.send(username="FoxCore 🦊", avatar_url=FOX_IMG,
                       content="All systems stable.")

        await asyncio.sleep(3)

        await cat.send(username="CatMonitor 🐱", avatar_url=CAT_IMG,
                       content="Memory usage normal.")

        await asyncio.sleep(3)

        await owl.send(username="OwlSecurity 🦉", avatar_url=OWL_IMG,
                       content="Security scan clean.")

        await asyncio.sleep(4)

        await technician.send(username="Technician 🧑‍💻", avatar_url=TECH_IMG,
                               content="AircraftGames running perfectly.")

        await asyncio.sleep(5)

        # =====================================================
        # PHASE 2 - FIRST ANOMALY
        # =====================================================

        await ctx.send("```diff\n- minor latency spike detected\n```")

        await asyncio.sleep(4)

        await owl.send(username="OwlSecurity 🦉", avatar_url=OWL_IMG,
                       content="Something is pinging external nodes...")

        await asyncio.sleep(4)

        await cat.send(username="CatMonitor 2.0 🐱", avatar_url=CAT_IMG,
                       content="I don’t like this pattern.")

        await asyncio.sleep(4)

        # =====================================================
        # PHASE 3 - SYSTEM BREACH STARTS
        # =====================================================

        await ctx.send("```diff\n- SYSTEM INSTABILITY INCREASING\n```")

        await asyncio.sleep(4)

        await fox.send(username="FoxCore 🦊", avatar_url=FOX_IMG,
                       content="Who opened external access?")

        await asyncio.sleep(4)

        await technician.send(username="Technician 🧑‍💻", avatar_url=TECH_IMG,
                               content="No one should have access to core files...")

        await asyncio.sleep(5)

        # =====================================================
        # HACKER APPEARS
        # =====================================================

        await hacker.send(username="UNKNOWN.exe 💀", avatar_url=HACK_IMG,
                          content="I’m already inside.")

        await asyncio.sleep(5)

        await owl.send(username="OwlSecurity 🦉", avatar_url=OWL_IMG,
                       content="TRACE FAILED.")

        await asyncio.sleep(4)

        # =====================================================
        # PHASE 4 - TECHNICIAN VS HACKER
        # =====================================================

        await technician.send(username="Technician 🧑‍💻", avatar_url=TECH_IMG,
                               content="Get out of my system.")

        await asyncio.sleep(5)

        await hacker.send(username="UNKNOWN.exe 💀", avatar_url=HACK_IMG,
                          content="You built it. I just opened the door.")

        await asyncio.sleep(6)

        await technician.send(username="Technician 🧑‍💻", avatar_url=TECH_IMG,
                               content="Firewall reinforcements ONLINE.")

        await asyncio.sleep(5)

        await hacker.send(username="UNKNOWN.exe 💀", avatar_url=HACK_IMG,
                          content="Too slow.")

        await asyncio.sleep(5)

        # =====================================================
        # FINAL CORRUPTION
        # =====================================================

        await ctx.send(
            "```yaml\n"
            "AircraftGames CORE STATUS:\n"
            "CORRUPTED\n"
            "LOGS: REWRITTEN\n"
            "ACCESS: LOST\n"
            "```"
        )

        await asyncio.sleep(5)

        # =====================================================
        # NEW ENDING: THE TURNAROUND & SUDO CONFRONTATION
        # =====================================================

        await technician.send(
            username="Technician 🧑‍💻", 
            avatar_url=TECH_IMG,
            content="Wait... looking at the backup cluster data streams... I found a back door entry point! Re-routing matrix access now."
        )

        await asyncio.sleep(4)

        await ctx.send(
            "```bash\n"
            "$ sudo systemctl stop aircraft-core-external\n"
            "[sudo] password for technician: ************\n"
            "Processing...\n"
            "```"
        )
        await asyncio.sleep(3)

        await hacker.send(
            username="UNKNOWN.exe 💀", 
            avatar_url=HACK_IMG,
            content="What are you doing?! Stop modifying the root security tables!"
        )

        await asyncio.sleep(3)

        await ctx.send(
            "```bash\n"
            "$ sudo iptables -A INPUT -s 185.220.101.0/24 -j DROP\n"
            "$ sudo killall -9 unknown.exe\n"
            "```"
        )
        await asyncio.sleep(3)

        await hacker.send(
            username="UNKNOWN.exe 💀", 
            avatar_url=HACK_IMG,
            content="NO! The connection is dropsdf--... connection lost... fatal error..."
        )

        await asyncio.sleep(4)

        await ctx.send(
            "```diff\n"
            "+ SUCCESS: MALICIOUS PROCESS ELIMINATED\n"
            "+ RESTORING AIRCRAFTGAMES CORES...\n"
            "+ REBOOTING HARDWARE INTERFACES...\n"
            "```"
        )
        await asyncio.sleep(4)

        # =====================================================
        # THE GRAND FINALE ANNOUNCEMENTS
        # =====================================================

        # 1. Official announcement from the bot itself with an @everyone ping
        await ctx.send(content="2.0 Update was now release. Thank you, @everyone!")
        await asyncio.sleep(3)

        # 2. CatMonitor approving the update
        await cat.send(
            username="CatMonitor 🐱", 
            avatar_url=CAT_IMG,
            content="Cool. Like it."
        )
        await asyncio.sleep(2)

        # =====================================================
        # CLEANUP
        # =====================================================

        try:
            await fox.delete()
            await owl.delete()
            await cat.delete()
            await technician.delete()
            await hacker.delete()
        except:
            pass


async def setup(bot):
    await bot.add_cog(Moderation(bot))
