import os
import discord
from discord.ext import commands
import docker

# Get the bot token from the environment variable
TOKEN = os.getenv('BOT_TOKEN')

# Define the intents your bot will use
intents = discord.Intents.default()
intents.message_content = True  # Allows the bot to read message content (necessary for commands)

# Initialize the bot with command prefix '!' and the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Docker client
client = docker.DockerClient(base_url='unix://var/run/docker.sock')

# Restrict bot usage to a specific channel (optional)
ALLOWED_CHANNELS = ['bot-commands']  # Replace with your actual channel names

# Name of your game server container
CONTAINER_NAME = 'Palworld'

# Command to start the game server
@bot.command()
async def startserver(ctx):
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.start()
        await ctx.send('Game server is starting!')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        await ctx.send(f'Error starting the server: {e}')

# Command to stop the game server
@bot.command()
async def stopserver(ctx):
    if ctx.channel.name not in ALLOWED_CHANNELS:
        return
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.stop()
        await ctx.send('Game server is stopping!')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        await ctx.send(f'Error stopping the server: {e}')

# Command to check server status
@bot.command()
async def serverstatus(ctx):
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.reload()  # Refresh container state
        status = container.status  # 'running', 'exited', etc.
        await ctx.send(f'Game server status: {status}')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        await ctx.send(f'Error retrieving server status: {e}')

bot.run(TOKEN)
