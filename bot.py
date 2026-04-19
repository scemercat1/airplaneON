import discord
from discord.ext import commands
from discord import app_commands
import json, os, asyncio, random
from datetime import datetime, timedelta

DATA_PATH = "/data"

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
    roles = data.get(str(interaction.guild.id), [])
    return any(r.id in roles for r in interaction.user.roles)

def is_owner(interaction):
    return interaction.user.id == interaction.guild.owner_id

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="mods")
async def mods(interaction: discord.Interaction, roles: str):
    if not is_owner(interaction):
        return await interaction.response.send_message("Only server owner.", ephemeral=True)

    role_ids = [int(r.strip("<@&>")) for r in roles.split()]
    data = load_json("config.json")
    data[str(interaction.guild.id)] = role_ids
    save_json("config.json", data)

    await interaction.response.send_message("Mods updated.")

@bot.tree.command(name="warn")
async def warn(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    await member.send(f"You were warned: {reason}")
    await interaction.response.send_message("Warned.")

@bot.tree.command(name="mute")
async def mute(interaction, member: discord.Member, minutes: int, reason: str):
    if not is_mod(interaction): return
    await member.timeout(timedelta(minutes=minutes))
    await interaction.response.send_message("Muted.")

@bot.tree.command(name="unmute")
async def unmute(interaction, member: discord.Member):
    if not is_mod(interaction): return
    await member.timeout(None)
    await interaction.response.send_message("Unmuted.")

@bot.tree.command(name="ban")
async def ban(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    await member.ban(reason=reason)
    await interaction.response.send_message("Banned.")

@bot.tree.command(name="kick")
async def kick(interaction, member: discord.Member, reason: str):
    if not is_mod(interaction): return
    await member.kick(reason=reason)
    await interaction.response.send_message("Kicked.")

@bot.tree.command(name="clear")
async def clear(interaction, amount: int):
    if not is_mod(interaction): return
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message("Cleared.", ephemeral=True)

@bot.tree.command(name="giveawaycreate")
async def giveaway(interaction: discord.Interaction, name: str, prize: str, description: str, winners: int, time: str):
    if not is_mod(interaction):
        return

    unit = time[-1]
    value = int(time[:-1])

    seconds = value * {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }.get(unit, 60)

    embed = discord.Embed(
        title=f"🎉 {name}",
        description=f"{description}\n\nPrize: **{prize}**",
        color=discord.Color.green()
    )

    embed.set_footer(text=f"{winners} winners | Ends in {time}")

    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    await interaction.response.send_message("Giveaway started.", ephemeral=True)

    await asyncio.sleep(seconds)

    msg = await interaction.channel.fetch_message(msg.id)
    users = [u async for u in msg.reactions[0].users() if not u.bot]

    if len(users) == 0:
        return await interaction.channel.send("No winners.")

    winners_list = random.sample(users, min(len(users), winners))

    await interaction.channel.send(
        f"🎉 Winners: {', '.join([w.mention for w in winners_list])}"
    )

@bot.tree.command(name="countchannel")
async def countchannel(interaction: discord.Interaction, channel: discord.TextChannel, start: int):
    if not is_mod(interaction):
        return

    data = load_json("counting.json")
    data[str(channel.id)] = start
    save_json("counting.json", data)

    await interaction.response.send_message("Counting channel set.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_json("counting.json")

    if str(message.channel.id) in data:
        expected = data[str(message.channel.id)] + 1

        if not message.content.isdigit() or int(message.content) != expected:
            await message.delete()
            return

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
