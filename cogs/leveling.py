import discord
from discord import app_commands
from discord.ext import commands
import random

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db["levels"]
        self.config_db = self.bot.db["level_configs"] # Colectie noua pentru setari

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
                await message.channel.send(f"🎊 Felicitări {message.author.mention}, ai ajuns la **Nivelul {new_lvl}**!")
                # Verificăm dacă există un rol premiu pentru noul nivel
                await self.check_role_reward(message.author, message.guild, new_lvl)
            
            await self.db.update_one(
                {"_id": user_data["_id"]}, 
                {"$set": {"xp": new_xp, "lvl": new_lvl}}
            )

    async def check_role_reward(self, member, guild, level):
        """Funcție internă care acordă rolul dacă nivelul are un premiu setat"""
        config = await self.config_db.find_one({"guild_id": str(guild.id)})
        if config and "rewards" in config:
            role_id = config["rewards"].get(str(level))
            if role_id:
                role = guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                        await member.send(f"🎖️ Ai primit rolul **{role.name}** pentru atingerea nivelului {level} în {guild.name}!")
                    except:
                        pass

    @app_commands.command(name="levelconfig", description="Setează roluri premiu pentru anumite nivele")
    @app_commands.describe(level="Nivelul la care se acordă rolul", role="Rolul care va fi acordat")
    @app_commands.checks.has_permissions(administrator=True) # Doar adminii pot folosi
    async def levelconfig(self, interaction: discord.Interaction, level: int, role: discord.Role):
        if level < 1 or level > 200:
            return await interaction.response.send_message("Nivelul trebuie să fie între 1 și 200.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        
        # Actualizăm sau creăm configurația pentru server
        await self.config_db.update_one(
            {"guild_id": guild_id},
            {"$set": {f"rewards.{level}": str(role.id)}},
            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Configurat: Jucătorii vor primi rolul {role.mention} la **Nivelul {level}**.",
            ephemeral=True
        )

    @app_commands.command(name="levelrewards", description="Vezi lista de roluri premiu pe acest server")
    async def levelrewards(self, interaction: discord.Interaction):
        config = await self.config_db.find_one({"guild_id": str(interaction.guild_id)})
        if not config or "rewards" not in config or not config["rewards"]:
            return await interaction.response.send_message("Nu sunt setate roluri premiu pe acest server.", ephemeral=True)

        rewards = config["rewards"]
        # Sortăm nivelele crescător
        sorted_levels = sorted(rewards.keys(), key=lambda x: int(x))
        
        description = ""
        for lvl in sorted_levels:
            role = interaction.guild.get_role(int(rewards[lvl]))
            role_mention = role.mention if role else "Rol Șters"
            description += f"**Nivel {lvl}**: {role_mention}\n"

        embed = discord.Embed(title="🎖️ Premii Nivel", description=description, color=0xffd700)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
