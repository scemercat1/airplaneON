import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

class Update2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_db = bot.db["guild_data"]
        self.youtube_feed_checker.start()

    def cog_unload(self):
        self.youtube_feed_checker.cancel()

    @app_commands.command(
        name="welcomemsg", 
        description="Configure a custom message that will be DM'ed to new members upon joining"
    )
    @app_commands.describe(message="The message to send. Use {user} to mention them, and {server} for the server name.")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcomemsg(self, interaction: discord.Interaction, message: str):
        await self.guild_db.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"welcome_dm_text": message}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✨ Welcome DM Message Configured", 
            description=f"New members will now receive this DM:\n\n{message}", 
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_settings = await self.guild_db.find_one({"guild_id": member.guild.id})
        
        if guild_settings and guild_settings.get("welcome_dm_text"):
            raw_message = guild_settings["welcome_dm_text"]
            formatted_message = raw_message.replace("{user}", member.mention).replace("{server}", member.guild.name)
            
            try:
                await member.send(content=formatted_message)
            except discord.Forbidden:
                pass

    @app_commands.command(
        name="youtubealerts", 
        description="Configure automated YouTube upload alerts (Premium Only)"
    )
    @app_commands.describe(
        ytchannelusername="The YouTube handle or username (e.g., MrBeast or @MrBeast)",
        channeltoalert="The text channel where the notification will be posted",
        custom_message="Your alert text. MUST include {video_url} and can include {video_title}."
    )
    async def youtubealerts(self, interaction: discord.Interaction, ytchannelusername: str, channeltoalert: discord.TextChannel, custom_message: str):
        data = await self.guild_db.find_one({"guild_id": interaction.guild.id})
        if not data or not data.get("premium"):
            return await interaction.response.send_message(
                "❌ This feature requires an active server Premium license. Activate one using `/premium`!", 
                ephemeral=True
            )

        if "{video_url}" not in custom_message:
            return await interaction.response.send_message(
                "❌ Your custom message layout must include `{video_url}` so viewers can click the link!", 
                ephemeral=True
            )

        clean_username = ytchannelusername.strip().replace("@", "")
        await interaction.response.defer(ephemeral=True)

        test_url = f"https://www.youtube.com/feeds/videos.xml?user={clean_username}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(test_url, timeout=10) as resp:
                    if resp.status != 200:
                        test_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={clean_username}"
                        async with session.get(test_url, timeout=10) as resp2:
                            if resp2.status != 200:
                                return await interaction.followup.send(
                                    f"❌ Could not find a YouTube channel matching `{ytchannelusername}`. Please verify the handle.", 
                                    ephemeral=True
                                )
                            else:
                                final_lookup_url = test_url
                    else:
                        final_lookup_url = test_url
            except Exception as e:
                return await interaction.followup.send(f"❌ YouTube Feed Connection Error: {str(e)}", ephemeral=True)

        await self.guild_db.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {
                "yt_feed_url": final_lookup_url,
                "yt_ping_channel_id": channeltoalert.id,
                "yt_custom_alert_msg": custom_message,
                "yt_last_seen_video_id": None
            }},
            upsert=True
        )

        await interaction.followup.send(
            f"✅ **YouTube Alerts Configured!**\n"
            f"**Target:** `{ytchannelusername}`\n"
            f"**Channel:** {channeltoalert.mention}\n\n"
            f"The bot will scan this feed and apply your custom formatting on the next upload.", 
            ephemeral=True
        )

    @tasks.loop(minutes=3)
    async def youtube_feed_checker(self):
        await self.bot.wait_until_ready()
        
        async with aiohttp.ClientSession() as session:
            cursor = self.guild_db.find({"yt_feed_url": {"$exists": True}, "premium": True})
            
            async for server_data in cursor:
                feed_url = server_data["yt_feed_url"]
                
                try:
                    async with session.get(feed_url, timeout=10) as resp:
                        if resp.status != 200: 
                            continue
                        
                        xml_text = await resp.text()
                        
                        # Parse XML safely using namespaces to read exact node structures
                        root = ET.fromstring(xml_text)
                        namespaces = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
                        
                        entries = root.findall('atom:entry', namespaces)
                        if not entries:
                            continue
                        
                        # Always check the actual first entry
                        latest_entry = entries[0]
                        video_id = latest_entry.find('yt:videoId', namespaces).text
                        video_title = latest_entry.find('atom:title', namespaces).text
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        # Skip if this video is already tracked
                        if server_data.get("yt_last_seen_video_id") == video_id:
                            continue
                        
                        # Safety check: Ignore entries older than 2 days (Prevents old logs spamming chat on bot setup)
                        published_str = latest_entry.find('atom:published', namespaces).text
                        # Convert ISO format timestamp to standard datetime string
                        published_time = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        if (datetime.now(timezone.utc) - published_time).days > 2:
                            continue
                            
                        target_channel = self.bot.get_channel(server_data["yt_ping_channel_id"])
                        if target_channel:
                            message_template = server_data["yt_custom_alert_msg"]
                            compiled_message = message_template.replace("{video_url}", video_url).replace("{video_title}", video_title)
                            await target_channel.send(content=compiled_message)
                            
                        await self.guild_db.update_one(
                            {"guild_id": server_data["guild_id"]},
                            {"$set": {"yt_last_seen_video_id": video_id}}
                        )
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(Update2(bot))
