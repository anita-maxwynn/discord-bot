import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# URLs to stream
STREAM_URLS = {
    '1': 'https://stream.radioparadise.com/mp3-192',
    '2': 'http://listen.powerhitz.com/hot108',
    '3': 'https://listen.181fm.com/181-beat_128k.mp3',
}

voice_client = None
current_stream = None

def is_admin_or_mod(ctx):
    mod_role = discord.utils.get(ctx.guild.roles, name='mod')
    return ctx.author.guild_permissions.administrator or (mod_role in ctx.author.roles)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    logging.info(f'Bot started as {bot.user.name} - {bot.user.id}')

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel:
        await channel.send(f'Welcome to the server, {member.mention}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def join(ctx):
    global voice_client
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()
        await ctx.send(f"🎶 Joined {channel.name}")
    else:
        await ctx.send("❌ You need to be in a voice channel.")

@bot.command()
async def leave(ctx):
    global voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None
        await ctx.send("👋 Left the voice channel.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def url(ctx, number: str):
    global voice_client, current_stream
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to change the stream.")
        return

    if number not in STREAM_URLS:
        await ctx.send("❌ Invalid stream number. Choose 1, 2, or 3.")
        return

    url = STREAM_URLS[number]

    if not voice_client or not voice_client.is_connected():
        if ctx.author.voice:
            voice_client = await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You're not in a voice channel.")
            return

    if voice_client.is_playing():
        voice_client.stop()

    source = await discord.FFmpegOpusAudio.from_probe(url, method='fallback')
    voice_client.play(source)
    current_stream = number
    await ctx.send(f"✅ Now playing stream {number}.")



@bot.command()
async def assign(ctx, member: discord.Member):
    mod_role = discord.utils.get(ctx.guild.roles, name='mod')
    if not mod_role:
        await ctx.send("❌ 'mod' role not found.")
        return

    # Check if author is admin or already has 'mod' role
    is_admin = ctx.author.guild_permissions.administrator
    has_mod = mod_role in ctx.author.roles

    if not (is_admin or has_mod):
        await ctx.send("❌ You don’t have permission to assign the mod role.")
        return

    await member.add_roles(mod_role)
    await ctx.send(f"✅ {mod_role.name} role assigned to {member.mention}.")


@bot.command()
async def unassign(ctx):
    mod_role = discord.utils.get(ctx.guild.roles, name='mod')
    if mod_role in ctx.author.roles:
        await ctx.author.remove_roles(mod_role)
        await ctx.send(f'Role {mod_role.name} removed from {ctx.author.mention}.')
    else:
        await ctx.send('You do not have that role.')

@bot.command()
async def pause(ctx):
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to pause the stream.")
        return
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Stream paused.")

@bot.command()
async def resume(ctx):
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to resume the stream.")
        return
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Stream resumed.")

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
