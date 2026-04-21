import discord
from discord.ext import commands
from discord import app_commands
import asyncio, random, time

class Giveaway(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="giveawaystart")
    async def gstart(self, itx, name: str, prize: str, description: str, winners: int, seconds: int):
        end_time = int(time.time() + seconds)
        embed = discord.Embed(title=f"🎉 GIVEAWAY: {name}", description=description, color=0x5865F2)
        embed.add_field(name="Prize", value=prize)
        embed.add_field(name="Winners", value=str(winners))
        embed.add_field(name="Ends", value=f"<t:{end_time}:R>")
        
        await itx.response.send_message("Giveaway started!", ephemeral=True)
        msg = await itx.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        await asyncio.sleep(seconds)

        # Pick winners
        new_msg = await itx.channel.fetch_message(msg.id)
        users = [u async for u in new_msg.reactions[0].users() if not u.bot]
        
        if len(users) < winners:
            await itx.channel.send(f"Not enough entries for **{name}**.")
        else:
            w_list = random.sample(users, winners)
            mentions = ", ".join([w.mention for w in w_list])
            await itx.channel.send(f"🏆 Congratulations {mentions}! You won **{prize}**!")

async def setup(bot): await bot.add_cog(Giveaway(bot))
