import discord
from discord import app_commands
from discord.ext import commands
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db["levels"]
        self.config_db = self.bot.db["level_configs"]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        user_data = await self.db.find_one({"user": user_id, "guild": guild_id})
        
        if not user_data:
            user_data = {"user": user_id, "guild": guild_id, "xp": 5, "lvl": 1}
            await self.db.insert_one(user_data)
        else:
            xp_to_add = random.randint(5, 15)
            new_xp = user_data["xp"] + xp_to_add
            new_lvl = (new_xp // 100) + 1
            
            if new_lvl > user_data["lvl"]:
                await message.channel.send(f"🎊 Congrats {message.author.mention}, you reached **Level {new_lvl}**!")
                await self.check_role_reward(message.author, message.guild, new_lvl)
            
            await self.db.update_one(
                {"_id": user_data["_id"]}, 
                {"$set": {"xp": new_xp, "lvl": new_lvl}}
            )

    async def check_role_reward(self, member, guild, level):
        config = await self.config_db.find_one({"guild_id": str(guild.id)})
        if config and "rewards" in config:
            role_id = config["rewards"].get(str(level))
            if role_id:
                role = guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                        await member.send(f"🎖️ You've been granted the **{role.name}** role for hitting Level {level} in {guild.name}!")
                    except:
                        pass

    @app_commands.command(name="levelconfig")
    @app_commands.describe(level="Level (1-200)", role="Role reward")
    @app_commands.checks.has_permissions(administrator=True)
    async def levelconfig(self, interaction: discord.Interaction, level: int, role: discord.Role):
        if level < 1 or level > 200:
            return await interaction.response.send_message("Level must be 1-200.", ephemeral=True)

        await self.config_db.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {f"rewards.{level}": str(role.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Level {level} reward set to {role.mention}", ephemeral=True)

    @app_commands.command(name="levelrewards")
    async def levelrewards(self, interaction: discord.Interaction):
        config = await self.config_db.find_one({"guild_id": str(interaction.guild_id)})
        if not config or "rewards" not in config:
            return await interaction.response.send_message("No rewards set.", ephemeral=True)

        rewards = config["rewards"]
        sorted_lvls = sorted(rewards.keys(), key=lambda x: int(x))
        text = "\n".join([f"**Lvl {l}**: <@&{rewards[l]}>" for l in sorted_lvls])
        
        embed = discord.Embed(title="🎖️ Level Rewards", description=text, color=0x00ffaa)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
