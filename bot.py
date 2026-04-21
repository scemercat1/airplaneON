import os
import asyncio
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

mongo_url = os.getenv("MONGO_URL")
bot.db_client = AsyncIOMotorClient(mongo_url)
bot.db = bot.db_client["aircraft_db"] 

async def load_cogs():
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
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, 
            name="/help"
        )
    )

    guild_ids = [str(g.id) for g in bot.guilds]
    await bot.db["bot_presence"].update_one(
        {"_id": "bot_stats"},
        {"$set": {"active_guilds": guild_ids}},
        upsert=True
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")

    print(f"🚀 {bot.user} is online | Connected to MongoDB | Status: Listening to /help")

@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"🔄 Global Slash Commands Synced! ({len(synced)} commands)")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
