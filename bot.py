import discord
from discord.ext import commands
import json, os, asyncio, random, uuid
from datetime import datetime, timedelta

DATA_PATH = "/data"
last_user = {}

def load_json(name):
    path = f"{DATA_PATH}/{name}"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(name, data):
    with open(f"{DATA_PATH}/{name}", "w") as f:
        json.dump(data, f, indent=2)

def get_mod_message(guild_id, msg_type):
    data = load_json("mod_messages.json")
    guild_settings = data.get(str(guild_id), {})
    return guild_settings.get(msg_type)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_mod(interaction):
    data = load_json("config.json")
    roles = [int(r) for r in data.get(str(interaction.guild.id), [])]
    return any(r.id in roles for r in interaction.user.roles)

def is_owner(interaction):
    return interaction.user.id == interaction.guild.owner_id

def get_logs(guild_id):
    data = load_json("logs.json")
    return data.get(str(guild_id))

async def send_log(guild, embed):
    log_id = get_logs(guild.id)
    if log_id:
        ch = guild.get_channel(log_id)
        if ch:
            await ch.send(embed=embed)

def dm_embed(title, desc, color):
    return discord.Embed(title=title, description=desc, color=color)

@bot.event
async def on_ready():
    try:
        guild_ids = [str(g.id) for g in bot.guilds]
        with open(f"{DATA_PATH}/bot_guilds.json", "w") as f:
            json.dump(guild_ids, f)
    except Exception as e:
        print(f"Sync error: {e}")

    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}")

    bot.loop.create_task(check_giveaways())
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="mods")
async def mods(interaction, roles: str):
    if not is_owner(interaction):
        return await interaction.response.send_message("Only owner.", ephemeral=True)
    role_ids = [int(r.strip("<@&>")) for r in roles.split()]
    data = load_json("config.json")
    data[str(interaction.guild.id)] = role_ids
    save_json("config.json", data)
    await interaction.response.send_message("Mods set.", ephemeral=True)

@bot.tree.command(name="logs")
async def logs(interaction, channel: discord.TextChannel):
    if not is_owner(interaction):
        return await interaction.response.send_message("Only owner.", ephemeral=True)
    data = load_json("logs.json")
    data[str(interaction.guild.id)] = channel.id
    save_json("logs.json", data)
    await interaction.response.send_message("Logs enabled.", ephemeral=True)

@bot.tree.command(name="role")
async def role(interaction, member: discord.Member, role: discord.Role):
    if not is_mod(interaction): return
    if role in member.roles:
        await member.remove_roles(role)
        action = "removed"
    else:
        await member.add_roles(role)
        action = "added"
    await interaction.response.send_message(f"Role {action}.")

@bot.tree.command(name="warn")
async def warn(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    custom = get_mod_message(interaction.guild.id, "warn")
    display = custom.replace("{reason}", reason) if custom else reason
    try:
        await member.send(embed=dm_embed("Warn", display, discord.Color.orange()))
    except: pass
    await send_log(interaction.guild, discord.Embed(title="Warn", description=f"{member} warned by {interaction.user}\nReason: {display}", color=discord.Color.orange()))
    await interaction.response.send_message("Warn sent.")

@bot.tree.command(name="kick")
async def kick(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    custom = get_mod_message(interaction.guild.id, "kick")
    display = custom.replace("{reason}", reason) if custom else reason
    try:
        await member.send(embed=dm_embed("Kick", display, discord.Color.red()))
    except: pass
    await member.kick(reason=reason)
    await send_log(interaction.guild, discord.Embed(title="Kick", description=f"{member} kicked by {interaction.user}\nReason: {display}", color=discord.Color.red()))
    await interaction.response.send_message("Kicked.")

@bot.tree.command(name="ban")
async def ban(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    custom = get_mod_message(interaction.guild.id, "ban")
    display = custom.replace("{reason}", reason) if custom else reason
    try:
        await member.send(embed=dm_embed("Ban", display, discord.Color.dark_red()))
    except: pass
    await member.ban(reason=reason)
    await send_log(interaction.guild, discord.Embed(title="Ban", description=f"{member} banned by {interaction.user}\nReason: {display}", color=discord.Color.dark_red()))
    await interaction.response.send_message("Banned.")

@bot.tree.command(name="mute")
async def mute(interaction, member: discord.Member, minutes: int, reason: str):
    if not is_mod(interaction): return
    await member.timeout(timedelta(minutes=minutes))
    custom = get_mod_message(interaction.guild.id, "mute")
    display = custom.replace("{reason}", reason) if custom else reason
    try:
        await member.send(embed=dm_embed("Muted", display, discord.Color.blurple()))
    except: pass
    await send_log(interaction.guild, discord.Embed(title="Mute", description=f"{member} muted by {interaction.user}\nReason: {display}", color=discord.Color.blurple()))
    await interaction.response.send_message("Muted.")

async def check_giveaways():
    await bot.wait_until_ready()
    while True:
        data = load_json("giveaways.json")
        now = datetime.utcnow().timestamp()
        for gid, g in list(data.items()):
            if not g.get("ended") and now >= g["end"]:
                channel = bot.get_channel(g["channel"])
                msg = await channel.fetch_message(g["message"])
                users = [u async for u in msg.reactions[0].users() if not u.bot]
                if users:
                    winners = random.sample(users, min(len(users), g["winners"]))
                    await channel.send(f"🎉 Winners: {', '.join([w.mention for w in winners])}")
                else:
                    await channel.send("No winners.")
                g["ended"] = True
                g["delete_at"] = now + 3600
            if g.get("delete_at") and now >= g["delete_at"]:
                del data[gid]
        save_json("giveaways.json", data)
        await asyncio.sleep(10)

@bot.event
async def on_message(message):
    if message.author.bot: return
    data = load_json("counting.json")
    if str(message.channel.id) in data:
        expected = data[str(message.channel.id)] + 1
        if str(message.channel.id) in last_user and last_user[str(message.channel.id)] == message.author.id:
            await message.delete()
            return
        if not message.content.isdigit() or int(message.content) != expected:
            await message.delete()
            data[str(message.channel.id)] = 0
            save_json("counting.json", data)
            return
        last_user[str(message.channel.id)] = message.author.id
        data[str(message.channel.id)] = expected
        save_json("counting.json", data)
    await bot.process_commands(message)

token = os.getenv("DISCORD_TOKEN")
bot.run(token)
