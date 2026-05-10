import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Gaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db["counting_data"]
        # In-memory cache to prevent database lag during rapid counting
        self.cache = {} 

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

        if "counting" in message.channel.name.lower() and message.content.isdigit():
            # Get current state from cache or DB
            guild_id = str(message.guild.id)
            if guild_id not in self.cache:
                data = await self.db.find_one({"guild_id": guild_id})
                self.cache[guild_id] = data["count"] if data else 0
            
            current_count = self.cache[guild_id]
            user_number = int(message.content)

            if user_number == current_count + 1:
                # Correct number!
                self.cache[guild_id] = user_number
                await self.db.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"count": user_number}},
                    upsert=True
                )
                
                # Webhook magic: copy user and send number
                webhook = await self.get_webhook(message.channel)
                await message.delete()
                await webhook.send(
                    content=str(user_number),
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url
                )
            else:
                # Wrong number: Delete and say NOTHING as requested
                self.cache[guild_id] = 0
                await self.db.update_one({"guild_id": guild_id}, {"$set": {"count": 0}}, upsert=True)
                await message.delete()

    @app_commands.command(name="mysteriousball", description="Ask the ball a question")
    async def mysteriousball(self, interaction: discord.Interaction, question: str):
        responses = ["Yes", "No", "Whatever", "Go touch grass", "Hahaha", "Maybe...", "Ask again never", "The stars say yes", "Most definitely not"]
        embed = discord.Embed(title="🔮 The Mysterious Ball", color=0x9b59b6)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{random.choice(responses)}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play Rock Paper Scissors with the bot")
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user)
        await interaction.response.send_message("🪨 📄 ✂️ Choose your weapon!", view=view)

# --- Button Logic for RPS ---
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
            result = "It's a tie!"
            color = 0x95a5a6
        elif (user_choice == "Rock" and bot_choice == "Scissors") or \
             (user_choice == "Paper" and bot_choice == "Rock") or \
             (user_choice == "Scissors" and bot_choice == "Paper"):
            result = "You win! 🎉"
            color = 0x2ecc71
        else:
            result = "You lost! 💀"
            color = 0xe74c3c

        embed = discord.Embed(title="RPS Results", description=f"**{result}**", color=color)
        embed.add_field(name="You", value=user_choice, inline=True)
        embed.add_field(name="Aircraft Bot", value=bot_choice, inline=True)
        
        await interaction.response.edit_message(content=None, embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Gaming(bot))
