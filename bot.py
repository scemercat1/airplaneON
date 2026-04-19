import discord
from discord.ext import commands
import json, os, asyncio, random
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
        channel = guild.get_channel(log_id)
        if channel:
            await channel.send(embed=embed)

def dm_embed(title, description, color):
    return discord.Embed(title=title, description=description, color=color)

@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.loop.create_task(check_giveaways())
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="mods")
async def mods(interaction: discord.Interaction, roles: str):
    if not is_owner(interaction):
        return await interaction.response.send_message("Only owner.", ephemeral=True)

    role_ids = [int(r.strip("<@&>")) for r in roles.split()]
    data = load_json("config.json")
    data[str(interaction.guild.id)] = role_ids
    save_json("config.json", data)

    await interaction.response.send_message("Mods set.", ephemeral=True)

@bot.tree.command(name="logs")
async def logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_owner(interaction):
        return await interaction.response.send_message("Only owner.", ephemeral=True)

    data = load_json("logs.json")
    data[str(interaction.guild.id)] = channel.id
    save_json("logs.json", data)

    await interaction.response.send_message("Logs set.", ephemeral=True)

@bot.tree.command(name="role")
async def role_cmd(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not is_mod(interaction):
        return

    if role in member.roles:
        await member.remove_roles(role)
        action = "Removed"
    else:
        await member.add_roles(role)
        action = "Added"

    await interaction.response.send_message(f"{action} role.")

@bot.tree.command(name="warn")
async def warn(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return

    embed = dm_embed("Warned", reason, discord.Color.orange())

    try:
        await member.send(embed=embed)
    except:
        pass

    await send_log(interaction.guild, discord.Embed(
        title="Warn",
        description=f"{member} warned by {interaction.user}\nReason: {reason}",
        color=discord.Color.orange()
    ))

    await interaction.response.send_message("Warn sent.")

@bot.tree.command(name="kick")
async def kick(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return

    embed = dm_embed("Kicked", reason, discord.Color.red())

    try:
        await member.send(embed=embed)
    except:
        pass

    await member.kick(reason=reason)

    await send_log(interaction.guild, discord.Embed(
        title="Kick",
        description=f"{member} kicked by {interaction.user}\nReason: {reason}",
        color=discord.Color.red()
    ))

    await interaction.response.send_message("Kicked.")

@bot.tree.command(name="ban")
async def ban(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return

    embed = dm_embed("Banned", reason, discord.Color.dark_red())

    try:
        await member.send(embed=embed)
    except:
        pass

    await member.ban(reason=reason)

    await send_log(interaction.guild, discord.Embed(
        title="Ban",
        description=f"{member} banned by {interaction.user}\nReason: {reason}",
        color=discord.Color.dark_red()
    ))

    await interaction.response.send_message("Banned.")

@bot.tree.command(name="mute")
async def mute(interaction, member: discord.Member, minutes: int, reason: str):
    if not is_mod(interaction): return

    await member.timeout(timedelta(minutes=minutes))

    embed = dm_embed("Muted", reason, discord.Color.blurple())

    try:
        await member.send(embed=embed)
    except:
        pass

    await send_log(interaction.guild, discord.Embed(
        title="Mute",
        description=f"{member} muted by {interaction.user}\nReason: {reason}",
        color=discord.Color.blurple()
    ))

    await interaction.response.send_message("Muted.")

@bot.tree.command(name="giveawaycreate")
async def giveaway(interaction, name: str, prize: str, description: str, winners: int, time: str):
    if not is_mod(interaction): return

    unit = time[-1]
    value = int(time[:-1])

    seconds = value * {"s":1,"m":60,"h":3600,"d":86400}.get(unit,60)

    end_time = datetime.utcnow().timestamp() + seconds

    embed = discord.Embed(
        title=f"🎉 {name}",
        description=f"{description}\n\nPrize: **{prize}**",
        color=discord.Color.green()
    )

    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    data = load_json("giveaways.json")
    data[str(msg.id)] = {
        "channel": interaction.channel.id,
        "message": msg.id,
        "end": end_time,
        "winners": winners
    }
    save_json("giveaways.json", data)

    await interaction.response.send_message("Giveaway started.", ephemeral=True)

async def check_giveaways():
    await bot.wait_until_ready()
    while True:
        data = load_json("giveaways.json")

        for gid, g in list(data.items()):
            if datetime.utcnow().timestamp() >= g["end"]:
                channel = bot.get_channel(g["channel"])
                msg = await channel.fetch_message(g["message"])

                users = [u async for u in msg.reactions[0].users() if not u.bot]

                if users:
                    winners = random.sample(users, min(len(users), g["winners"]))
                    await channel.send(f"🎉 Winners: {', '.join([w.mention for w in winners])}")
                else:
                    await channel.send("No winners.")

                del data[gid]

        save_json("giveaways.json", data)
        await asyncio.sleep(10)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

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

        webhook = await message.channel.create_webhook(name="counter")

        await webhook.send(
            content=message.content,
            username=message.author.display_name,
            avatar_url=message.author.display_avatar.url
        )

        await message.delete()
        await webhook.delete()

    await bot.process_commands(message)

token = os.getenv("DISCORD_TOKEN")
bot.run(token)
