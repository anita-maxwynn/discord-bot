import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from google import genai # Import the Gemini library

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
gemini_api_key = os.getenv('GEMINI_TOKEN') # Get Gemini API key from .env

# Configure Gemini API
if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)
else:
    print("Warning: GEMINI_API_KEY not found. Search command will not work.")
    model = None

# Logging setup
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.DEBUG, handlers=[handler])

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

voice_client = None
current_stream = None


STREAM_URLS = {
    '1': 'https://stream.radioparadise.com/mp3-192',
    '2': 'http://listen.powerhitz.com/hot108',
    '3': 'https://listen.181fm.com/181-beat_128k.mp3',
}
# Check if user is mod or admin
def is_admin_or_mod(ctx):
    mod_role = discord.utils.get(ctx.guild.roles, name='mod')
    return (
        ctx.author.guild_permissions.administrator or
        (mod_role and mod_role in ctx.author.roles)
    )

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    logging.info(f'Bot started as {bot.user.name} - {bot.user.id}')

@bot.event
async def on_member_join(member):
    logging.info(f'New member joined: {member.name} - {member.id}')
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel:
        await channel.send(f'Welcome to the server, {member.mention}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    logging.info(f'Message from {message.author.name}: {message.content}')
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def assign(ctx, member: discord.Member):
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to assign the mod role.")
        return

    mod_role = discord.utils.get(ctx.guild.roles, name='mod')
    if not mod_role:
        await ctx.send("❌ 'mod' role not found.")
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
async def join(ctx, *, channel_name: str):
    global voice_client
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to use this command.")
        return

    channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
    if not channel:
        await ctx.send("❌ Voice channel not found.")
        return

    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        voice_client = await channel.connect()

    await ctx.send(f"🎶 Joined {channel.name}")

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
async def pause(ctx):
    global voice_client
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to pause the stream.")
        return
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Stream paused.")
    else:
        await ctx.send("❌ Nothing is playing.")

@bot.command()
async def resume(ctx):
    global voice_client
    if not is_admin_or_mod(ctx):
        await ctx.send("❌ You don’t have permission to resume the stream.")
        return
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Stream resumed.")
    else:
        await ctx.send("❌ Stream is not paused.")

@bot.command()
async def search(ctx, *, query: str):
    await ctx.send(f"🔍 Searching for: `{query}`...")
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=(query+"in 2000 characters or less"))
        # Gemini sometimes returns a 'parts' object directly, sometimes as a list
        if hasattr(response, 'parts') and response.parts:
            # Join the text from all parts
            result_text = " ".join([part.text for part in response.parts if hasattr(part, 'text')])
        elif hasattr(response, 'text'):
            result_text = response.text
        else:
            result_text = "Could not retrieve a valid text response from Gemini."

        if result_text:
            # Discord message character limit is 2000
            if len(result_text) > 2000:
                await ctx.send("📝 Result too long, sending first 2000 characters:")
                await ctx.send(result_text[:2000] + "...")
            else:
                await ctx.send(f"✅ Search result:\n```\n{result_text}\n```")
        else:
            await ctx.send("🤷 No specific text response found from Gemini.")

    except Exception as e:
        logging.error(f"Error during Gemini search: {e}")
        await ctx.send(f"❌ An error occurred during the search: {e}")


bot.run(token)