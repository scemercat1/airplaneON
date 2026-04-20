import discord
from discord.ext import commands
from discord import app_commands
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

def get_db_data(collection, filter_id):
    res = collection.find_one({"_id": str(filter_id)})
    return res["data"] if res else {}

def save_db_data(collection, filter_id, data):
    collection.update_one({"_id": str(filter_id)}, {"$set": {"data": data}}, upsert=True)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Permissions
def is_mod(interaction):
    data = get_db_data(config_col, interaction.guild.id)
    roles = [int(r) for r in data] if isinstance(data, list) else []
    return any(r.id in roles for r in interaction.user.roles) or interaction.user.guild_permissions.administrator

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
    guild_ids = [str(g.id) for g in bot.guilds]
    guilds_col.update_one({"_id": "bot_stats"}, {"$set": {"active_guilds": guild_ids}}, upsert=True)
    await bot.tree.sync()
    bot.loop.create_task(check_giveaways())
    print(f"Logged in as {bot.user}")

# ---------------- MODERATION ----------------

@bot.tree.command(name="ban")
@app_commands.describe(member="Member to ban", reason="Reason for ban")
async def ban(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return await interaction.response.send_message("No perms.", ephemeral=True)
    await member.ban(reason=reason)
    await send_log(interaction.guild, discord.Embed(title="Ban", description=f"{member} banned by {interaction.user}\nReason: {reason}", color=discord.Color.red()))
    await interaction.response.send_message(f"Banned {member.display_name}.")

@bot.tree.command(name="mute")
async def mute(interaction, member: discord.Member, minutes: int, reason: str):
    if not is_mod(interaction): return
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"Muted {member.display_name} for {minutes}m.")

@bot.tree.command(name="clear")
async def clear(interaction, amount: int):
    if not is_mod(interaction): return
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Cleared {amount} messages.", ephemeral=True)

@bot.tree.command(name="slowdown")
async def slowdown(interaction, seconds: int):
    if not is_mod(interaction): return
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"Slowmode set to {seconds}s.")

@bot.tree.command(name="lock")
async def lock(interaction):
    if not is_mod(interaction): return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("Channel locked. 🔒")

@bot.tree.command(name="unlock")
async def unlock(interaction):
    if not is_mod(interaction): return
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("Channel unlocked. 🔓")

# ---------------- COUNTING ----------------

@bot.tree.command(name="countchannel")
async def countchannel(interaction, channel: discord.TextChannel, start: int):
    if not is_mod(interaction): return
    counting_col.update_one({"_id": str(channel.id)}, {"$set": {"count": start}}, upsert=True)
    await interaction.response.send_message(f"Counting started in {channel.mention} at {start}!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    count_data = counting_col.find_one({"_id": str(message.channel.id)})
    if count_data:
        expected = count_data["count"] + 1
        
        # Check for same user
        if last_user.get(str(message.channel.id)) == message.author.id:
            await message.delete()
            return

        # Wrong number or not a number
        if not message.content.isdigit() or int(message.content) != expected:
            await message.delete()
            try:
                await message.author.timeout(timedelta(minutes=10), reason="Failed counting")
                await message.channel.send(f"❌ {message.author.mention} failed! The count was {expected-1}. 10m Mute.", delete_after=5)
            except: pass
            counting_col.update_one({"_id": str(message.channel.id)}, {"$set": {"count": 0}})
            return

        # Correct Number - Webhook Logic
        await message.delete()
        last_user[str(message.channel.id)] = message.author.id
        counting_col.update_one({"_id": str(message.channel.id)}, {"$set": {"count": expected}})

        # Send as Webhook
        webhooks = await message.channel.webhooks()
        webhook = discord.utils.get(webhooks, name="Aircraft Counting")
        if not webhook:
            webhook = await message.channel.create_webhook(name="Aircraft Counting")
        
        await webhook.send(
            content=message.content, 
            username=message.author.display_name, 
            avatar_url=message.author.display_avatar.url
        )
        return # Avoid processing commands if it's counting

    await bot.process_commands(message)

# ---------------- GIVEAWAYS ----------------

@bot.tree.command(name="giveawaystart")
async def giveawaystart(interaction, name: str, prize: str, description: str, winners: int, time: str):
    unit = time[-1]
    val = int(time[:-1])
    sec = val * {"s":1,"m":60,"h":3600,"d":86400}.get(unit, 60)
    gid = str(uuid.uuid4())[:8]
    end = datetime.utcnow().timestamp() + sec

    embed = discord.Embed(title=f"🎉 {name}", description=f"{description}\n\nPrize: **{prize}**\nEnds: <t:{int(end)}:R>", color=discord.Color.green())
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    giveaways_col.insert_one({"_id": gid, "channel": interaction.channel.id, "message": msg.id, "end": end, "winners": winners, "ended": False})
    await interaction.response.send_message(f"Giveaway started! ID: {gid}", ephemeral=True)

async def check_giveaways():
    await bot.wait_until_ready()
    while True:
        now = datetime.utcnow().timestamp()
        for g in giveaways_col.find({"ended": False, "end": {"$lte": now}}):
            ch = bot.get_channel(g["channel"])
            if ch:
                try:
                    msg = await ch.fetch_message(g["message"])
                    users = [u async for u in msg.reactions[0].users() if not u.bot]
                    if users:
                        ws = random.sample(users, min(len(users), g["winners"]))
                        await ch.send(f"🎉 Giveaway Finished! Winners: {', '.join([w.mention for w in ws])}")
                    else:
                        await ch.send("Giveaway ended with no participants.")
                except: pass
            giveaways_col.update_one({"_id": g["_id"]}, {"$set": {"ended": True}})
        await asyncio.sleep(15)

# ---------------- CONFIG ----------------

@bot.tree.command(name="mods")
async def mods(interaction, roles: str):
    if not is_owner(interaction): return
    ids = [int(r.strip("<@&>")) for r in roles.split()]
    save_db_data(config_col, interaction.guild.id, ids)
    await interaction.response.send_message("Mod roles updated.")

bot.run(os.getenv("DISCORD_TOKEN"))
