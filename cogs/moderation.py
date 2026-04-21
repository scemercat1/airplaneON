import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # Helper to get dashboard settings
    async def get_msg(self, guild_id, type):
        data = await self.db["settings"].find_one({"guild_id": str(guild_id)})
        return data.get(type) if data else None

    @app_commands.command(name="warn")
    async def warn(self, itx, member: discord.Member, reason: str):
        custom = await self.get_msg(itx.guild_id, "warn")
        msg = custom.replace("{reason}", reason) if custom else f"Warned for {reason}"
        await member.send(f"⚠️ {msg}")
        await itx.response.send_message(f"Warned {member.mention}")

    @app_commands.command(name="kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, itx, member: discord.Member, reason: str = "No reason"):
        custom = await self.get_msg(itx.guild_id, "kick")
        msg = custom.replace("{reason}", reason) if custom else f"Kicked for {reason}"
        await member.send(f"👞 {msg}")
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
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await itx.response.send_message(f"Timed out {member.name} for {minutes}m")

    @app_commands.command(name="clear")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, itx, amount: int):
        await itx.response.defer(ephemeral=True)
        deleted = await itx.channel.purge(limit=amount)
        await itx.followup.send(f"Deleted {len(deleted)} messages.")

    # Rapid-fire additional commands (logic implied for brevity)
    @app_commands.command(name="slowmode")
    async def slowmode(self, itx, seconds: int): await itx.channel.edit(slowmode_delay=seconds); await itx.response.send_message(f"Slowmode: {seconds}s")
    
    @app_commands.command(name="lock")
    async def lock(self, itx): await itx.channel.set_permissions(itx.guild.default_role, send_messages=False); await itx.response.send_message("Channel locked.")

    @app_commands.command(name="unlock")
    async def unlock(self, itx): await itx.channel.set_permissions(itx.guild.default_role, send_messages=True); await itx.response.send_message("Channel unlocked.")

    # Other commands to include: unban, unmute, nick, role-add, role-remove, vmute, vdeafen, set-modlog, audit-search, softban, list-warns, clear-warns.

async def setup(bot): await bot.add_cog(Moderation(bot))
