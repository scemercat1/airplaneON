import discord
from discord.ext import commands
import os, asyncio, random, uuid
from datetime import datetime, timedelta
from pymongo import MongoClient

# MongoDB Setup
MONGO_URL = os.getenv("MONGO_URL")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client["aircraft_db"]

# Collections
settings_col = db["settings"]
guilds_col = db["bot_presence"]
counting_col = db["counting"]
giveaways_col = db["giveaways"]
config_col = db["config"]
logs_col = db["logs"]

last_user = {}

# Helper to mimic your old load/save logic but with MongoDB
def get_db_data(collection, filter_id):
    res = collection.find_one({"_id": str(filter_id)})
    return res["data"] if res else {}

def save_db_data(collection, filter_id, data):
    collection.update_one({"_id": str(filter_id)}, {"$set": {"data": data}}, upsert=True)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_mod(interaction):
    data = get_db_data(config_col, interaction.guild.id)
    roles = [int(r) for r in data] if isinstance(data, list) else []
    return any(r.id in roles for r in interaction.user.roles)

def is_owner(interaction):
    return interaction.user.id == interaction.guild.owner_id

async def send_log(guild, embed):
    log_data = get_db_data(logs_col, guild.id)
    if log_data:
        ch = guild.get_channel(int(log_data))
        if ch: await ch.send(embed=embed)

def dm_embed(title, desc, color):
    return discord.Embed(title=title, description=desc, color=color)

@bot.event
async def on_ready():
    # Sync presence for Dashboard
    guild_ids = [str(g.id) for g in bot.guilds]
    guilds_col.update_one({"_id": "bot_stats"}, {"$set": {"active_guilds": guild_ids}}, upsert=True)
    
    try:
        await bot.tree.sync()
        print("Slash commands synced")
    except Exception as e:
        print(f"Sync error: {e}")

    bot.loop.create_task(check_giveaways())
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="mods")
async def mods(interaction, roles: str):
    if not is_owner(interaction): return await interaction.response.send_message("Only owner.", ephemeral=True)
    role_ids = [int(r.strip("<@&>")) for r in roles.split()]
    save_db_data(config_col, interaction.guild.id, role_ids)
    await interaction.response.send_message("Mods set.", ephemeral=True)

@bot.tree.command(name="logs")
async def logs(interaction, channel: discord.TextChannel):
    if not is_owner(interaction): return await interaction.response.send_message("Only owner.", ephemeral=True)
    save_db_data(logs_col, interaction.guild.id, str(channel.id))
    await interaction.response.send_message("Logs enabled.", ephemeral=True)

@bot.tree.command(name="warn")
async def warn(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    # Check Dashboard Custom Message
    dash_data = settings_col.find_one({"guild_id": str(interaction.guild.id)})
    custom = dash_data.get("warn") if dash_data else None
    display = custom.replace("{reason}", reason) if custom and "{reason}" in custom else reason

    try: await member.send(embed=dm_embed("Warn", display, discord.Color.orange()))
    except: pass

    await send_log(interaction.guild, discord.Embed(title="Warn", description=f"{member} warned by {interaction.user}\nReason: {display}", color=discord.Color.orange()))
    await interaction.response.send_message("Warn sent.")

@bot.tree.command(name="kick")
async def kick(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    dash_data = settings_col.find_one({"guild_id": str(interaction.guild.id)})
    custom = dash_data.get("kick") if dash_data else None
    display = custom.replace("{reason}", reason) if custom and "{reason}" in custom else reason
    
    try: await member.send(embed=dm_embed("Kick", display, discord.Color.red()))
    except: pass
    await member.kick(reason=reason)
    await send_log(interaction.guild, discord.Embed(title="Kick", description=f"{member} kicked by {interaction.user}\nReason: {display}", color=discord.Color.red()))
    await interaction.response.send_message("Kicked.")

@bot.tree.command(name="giveawaystart")
async def giveawaystart(interaction, name: str, prize: str, description: str, winners: int, time: str):
    unit = time[-1]
    value = int(time[:-1])
    seconds = value * {"s":1,"m":60,"h":3600,"d":86400}.get(unit,60)
    gid = str(uuid.uuid4())[:8]
    end = datetime.utcnow().timestamp() + seconds

    embed = discord.Embed(title=f"🎉 {name}", description=f"{description}\nPrize: {prize}\nID: `{gid}`", color=discord.Color.green())
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    giveaways_col.insert_one({
        "_id": gid,
        "channel": interaction.channel.id,
        "message": msg.id,
        "end": end,
        "winners": winners,
        "ended": False
    })
    await interaction.response.send_message(f"Giveaway ID: {gid}", ephemeral=True)

async def check_giveaways():
    await bot.wait_until_ready()
    while True:
        now = datetime.utcnow().timestamp()
        active_gs = giveaways_col.find({"ended": False, "end": {"$lte": now}})
        for g in active_gs:
            channel = bot.get_channel(g["channel"])
            try:
                msg = await channel.fetch_message(g["message"])
                users = [u async for u in msg.reactions[0].users() if not u.bot]
                if users:
                    ws = random.sample(users, min(len(users), g["winners"]))
                    await channel.send(f"🎉 Winners: {', '.join([w.mention for w in ws])}")
                else:
                    await channel.send("No winners.")
            except: pass
            giveaways_col.update_one({"_id": g["_id"]}, {"$set": {"ended": True}})
        await asyncio.sleep(10)

@bot.event
async def on_message(message):
    if message.author.bot: return
    count_data = counting_col.find_one({"_id": str(message.channel.id)})
    if count_data:
        expected = count_data["count"] + 1
        if last_user.get(str(message.channel.id)) == message.author.id:
            await message.delete()
            return
        if not message.content.isdigit() or int(message.content) != expected:
            await message.delete()
            counting_col.update_one({"_id": str(message.channel.id)}, {"$set": {"count": 0}}, upsert=True)
            return
        last_user[str(message.channel.id)] = message.author.id
        counting_col.update_one({"_id": str(message.channel.id)}, {"$set": {"count": expected}}, upsert=True)
    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
