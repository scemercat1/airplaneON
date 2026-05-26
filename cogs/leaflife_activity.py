import discord
from discord.ext import commands
from discord import app_commands

class LeafLifeActivity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaflife", description="Launch the 2D LeafLife mini-game right inside your voice channel! 🍂")
    async def launch_leaflife(self, interaction: discord.Interaction):
        # 1. Verify user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must join a voice channel first to start the LeafLife activity!", 
                ephemeral=True
            )

        voice_channel = interaction.user.voice.channel
        
        # 2. Defer response to eliminate any potential API gateway timeout crashes
        await interaction.response.defer(ephemeral=False)

        try:
            invite = await voice_channel.create_invite(
                target_type=discord.InviteTarget.embedded_application,
                target_application_id=interaction.guild.me.id,  # Uses your bot's client ID automatically
                max_age=600,  # Invite link lasts for 10 minutes
                max_uses=0    # Unlimited clicks for server friends
            )
            
            embed = discord.Embed(
                title="🍂 LeafLife 2D — AircraftGames",
                description=(
                    f"**Grow your mystical space plant live!**\n\n"
                    f"Click the button below or the invite link to open the 2D canvas web application "
                    f"directly inside **{voice_channel.name}**."
                ),
                color=0x2ecc71
            )
            # Clean aesthetic asset for the game profile card
            embed.set_thumbnail(url="https://i.imgur.com/83p1XbK.png")
            embed.add_field(name="Session Status", value="🟢 Active & Ready to Join", inline=True)
            embed.add_field(name="Hosted By", value=interaction.user.mention, inline=True)
            embed.set_footer(text="AircraftGames Activity Engine • Designed for global players")
            
            # Build interactive Link Button interface
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="🎮 Play LeafLife 2D", url=invite.url, style=discord.ButtonStyle.link))
            
            await interaction.followup.send(embed=embed, view=view)

        except discord.Forbidden:
            await interaction.followup.send("❌ Error: The bot lacks the `Create Invite` permission node inside this voice channel!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to initialize web session: `{str(e)}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LeafLifeActivity(bot))
