import os
import asyncio
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# We attach this to the 'bot' object so every Cog can use 'self.bot.db'
mongo_url = os.getenv("MONGO_URL")
bot.db_client = AsyncIOMotorClient(mongo_url)
bot.db = bot.db_client["aircraft_db"] 

async def load_cogs():
    """Automatically loads every .py file in the /cogs folder"""
    print("--- 📂 Loading Cogs ---")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
    print("-----------------------")

@bot.event
async def on_ready():
    # Sync server list for the Dashboard
    guild_ids = [str(g.id) for g in bot.guilds]
    await bot.db["bot_presence"].update_one(
        {"_id": "bot_stats"},
        {"$set": {"active_guilds": guild_ids}},
        upsert=True
    )
    
    # Sync Slash Commands to Discord (Required for new commands to show up)
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")

    print(f"🚀 {bot.user} is online | Connected to MongoDB")

async def main():
    async with bot:
        await load_cogs()
        # Ensure your DISCORD_TOKEN is in your Railway Variables!
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
