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

    async def get_webhook(self, channel):
        try:
            webhooks = await channel.webhooks()
            webhook = discord.utils.get(webhooks, name="Aircraft Counting")
            if not webhook:
                webhook = await channel.create_webhook(name="Aircraft Counting")
            return webhook
        except discord.Forbidden:
            return None

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
                if webhook:
                    await message.delete()
                    await webhook.send(
                        content=str(user_number),
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url
                    )
                else:
                    await message.add_reaction("✅")
            else:
                self.cache[guild_id] = {"count": 0, "last_user": None}
                await self.db.update_one(
                    {"guild_id": guild_id}, 
                    {"$set": {"count": 0, "last_user": None}}, 
                    upsert=True
                )
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass

    @app_commands.command(name="setcounting", description="Setup the counting game channel")
    @app_commands.describe(channel="Select the text channel for counting")
    @app_commands.checks.has_permissions(administrator=True)
    async def setcounting(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.settings_db.update_one(
            {"guild_id": str(interaction.guild_id)},
            {"$set": {"counting_channel": str(channel.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"🚀 **Counting System** active in {channel.mention}!", ephemeral=True)

    @app_commands.command(name="weather", description="Get professional weather info")
    @app_commands.describe(location="City name (e.g., Tokyo, New York)")
    async def weather(self, interaction: discord.Interaction, location: str):
        await interaction.response.defer()

        url = "http://api.weatherapi.com/v1/current.json"
        params = {"key": self.weather_api_key, "q": location, "aqi": "yes"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    curr = data['current']
                    loc = data['location']
                    
                    embed = discord.Embed(
                        title=f"🌡️ Weather Info: {loc['name']}, {loc['country']}",
                        description=f"**{curr['condition']['text']}**",
                        color=0x00A2FF
                    )
                    
                    aqi_val = curr['air_quality']['us-epa-index']
                    aqi_text = {1: "Good ✅", 2: "Moderate ⚠️", 3: "Unhealthy 🟠", 4: "Harmful 🔴"}.get(aqi_val, "Unknown")

                    embed.add_field(name="Temperature", value=f"{curr['temp_c']}°C", inline=True)
                    embed.add_field(name="Feels Like", value=f"{curr['feelslike_c']}°C", inline=True)
                    embed.add_field(name="Humidity", value=f"{curr['humidity']}%", inline=True)
                    embed.add_field(name="Wind", value=f"{curr['wind_kph']} km/h", inline=True)
                    embed.add_field(name="Air Quality", value=aqi_text, inline=True)
                    embed.add_field(name="Local Time", value=loc['localtime'].split(" ")[1], inline=True)
                    
                    embed.set_thumbnail(url=f"https:{curr['condition']['icon']}")
                    embed.set_footer(text="Aircraft Games Information Center")

                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"❌ Error: Location `{location}` not found or API key is inactive.")

    @app_commands.command(name="mysteriousball", description="Ask the cosmic ball a question")
    async def mysteriousball(self, interaction: discord.Interaction, question: str):
        responses = ["Yes", "No", "Maybe", "Ask again later", "Focus and ask again", "Signs point to yes", "My sources say no", "Outlook not so good"]
        embed = discord.Embed(title="🔮 Mysterious Ball", description=f"**Q:** {question}\n**A:** {random.choice(responses)}", color=0x9b59b6)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play Rock-Paper-Scissors")
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user)
        await interaction.response.send_message("🪨 📄 ✂️ Pick your move!", view=view)

class RPSView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user

    @discord.ui.button(label="Rock", emoji="🪨")
    async def rock(self, interaction, button): await self.play(interaction, "Rock")
    @discord.ui.button(label="Paper", emoji="📄")
    async def paper(self, interaction, button): await self.play(interaction, "Paper")
    @discord.ui.button(label="Scissors", emoji="✂️")
    async def scissors(self, interaction, button): await self.play(interaction, "Scissors")

    async def play(self, interaction, user_choice):
        if interaction.user != self.user: return
        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        if user_choice == bot_choice: res, col = "It's a Tie!", 0x999999
        elif (user_choice == "Rock" and bot_choice == "Scissors") or (user_choice == "Paper" and bot_choice == "Rock") or (user_choice == "Scissors" and bot_choice == "Paper"):
            res, col = "You Won! 🎉", 0x2ECC71
        else: res, col = "You Lost! 💀", 0xE74C3C
        
        embed = discord.Embed(title=res, color=col)
        embed.add_field(name="You", value=user_choice)
        embed.add_field(name="Bot", value=bot_choice)
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Gaming(bot))
