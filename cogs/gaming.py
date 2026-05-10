import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
import os
import datetime

class Gaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db["counting_data"]
        self.settings_db = self.bot.db["settings"]
        self.cache = {} 
        self.weather_api_key = os.getenv("WEATHER_API_KEY")

    # --- Counting System ---
    async def get_webhook(self, channel):
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="Aircraft Counting")
        if not webhook:
            webhook = await channel.create_webhook(name="Aircraft Counting")
        return webhook

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_data = await self.settings_db.find_one({"guild_id": str(message.guild.id)})
        if not guild_data or str(message.channel.id) != guild_data.get("counting_channel"):
            return

        if message.content.isdigit():
            guild_id = str(message.guild.id)
            
            if guild_id not in self.cache:
                data = await self.db.find_one({"guild_id": guild_id})
                if data:
                    self.cache[guild_id] = {"count": data["count"], "last_user": data.get("last_user")}
                else:
                    self.cache[guild_id] = {"count": 0, "last_user": None}
            
            current_count = self.cache[guild_id]["count"]
            last_user_id = self.cache[guild_id]["last_user"]
            user_number = int(message.content)

            if user_number == current_count + 1 and str(message.author.id) != last_user_id:
                self.cache[guild_id] = {"count": user_number, "last_user": str(message.author.id)}
                await self.db.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"count": user_number, "last_user": str(message.author.id)}},
                    upsert=True
                )
                
                webhook = await self.get_webhook(message.channel)
                await message.delete()
                await webhook.send(
                    content=str(user_number),
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url
                )
            else:
                self.cache[guild_id] = {"count": 0, "last_user": None}
                await self.db.update_one({"guild_id": guild_id}, {"$set": {"count": 0, "last_user": None}}, upsert=True)
                await message.delete()

    # --- Commands ---

    @app_commands.command(name="setcounting", description="Set the channel for the counting game")
    @app_commands.checks.has_permissions(administrator=True)
    async def setcounting(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.settings_db.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {"counting_channel": str(channel.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Counting channel has been set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="weather", description="Check the weather in any city or country")
    @app_commands.describe(location="The city or country to check")
    async def weather(self, interaction: discord.Interaction, location: str):
        await interaction.response.defer()

        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.weather_api_key}&units=metric"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    city = data['name']
                    country = data['sys']['country']
                    temp = data['main']['temp']
                    desc = data['weather'][0]['description'].capitalize()
                    humidity = data['main']['humidity']
                    icon = data['weather'][0]['icon']
                    
                    # Convert sunrise/sunset timestamps to readable format
                    sunrise = datetime.datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
                    sunset = datetime.datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
                    
                    embed = discord.Embed(
                        title=f"🌡️ Weather in {city}, {country}",
                        description=f"**{desc}**",
                        color=0x3498db
                    )
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon}@4x.png")
                    embed.add_field(name="Temperature", value=f"{temp}°C", inline=True)
                    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                    embed.add_field(name="Sunrise", value=f"🌅 {sunrise}", inline=True)
                    embed.add_field(name="Sunset", value=f"🌇 {sunset}", inline=True)
                    embed.set_footer(text="Powered by Aircraft Games | OpenWeatherMap")

                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"❌ Location `{location}` not found.", ephemeral=True)

    @app_commands.command(name="mysteriousball", description="Ask the ball a question")
    async def mysteriousball(self, interaction: discord.Interaction, question: str):
        responses = ["Yes", "No", "Whatever", "Go touch grass", "Hahaha", "Maybe...", "Ask again never", "The stars say yes", "Most definitely not"]
        embed = discord.Embed(title="🔮 The Mysterious Ball", color=0x9b59b6)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{random.choice(responses)}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play Rock Paper Scissors")
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user)
        await interaction.response.send_message("🪨 📄 ✂️ Choose your weapon!", view=view)

# --- Button Logic for RPS (Remains the same) ---
class RPSView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.secondary, emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.secondary, emoji="📄")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.secondary, emoji="✂️")
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Scissors")

    async def play(self, interaction: discord.Interaction, user_choice):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your game!", ephemeral=True)
        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        if user_choice == bot_choice:
            result, color = "It's a tie!", 0x95a5a6
        elif (user_choice == "Rock" and bot_choice == "Scissors") or \
             (user_choice == "Paper" and bot_choice == "Rock") or \
             (user_choice == "Scissors" and bot_choice == "Paper"):
            result, color = "You win! 🎉", 0x2ecc71
        else:
            result, color = "You lost! 💀", 0xe74c3c
        embed = discord.Embed(title="RPS Results", description=f"**{result}**", color=color)
        embed.add_field(name="You", value=user_choice, inline=True)
        embed.add_field(name="Bot", value=bot_choice, inline=True)
        await interaction.response.edit_message(content=None, embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Gaming(bot))
