import os
import discord
from discord.ext import commands, tasks
import docker
import re
import threading
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO or DEBUG for more verbosity
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

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

# Inactivity settings
INACTIVITY_LIMIT = 600  # In seconds (10 minutes)
CHECK_INTERVAL = 60     # In seconds (check every minute)
inactivity_time = 0     # Initialize inactivity timer

# Shared data structures
online_players = set()
online_players_lock = threading.Lock()
log_monitoring_thread = None

def monitor_container_logs():
    global online_players
    while True:
        try:
            container = client.containers.get(CONTAINER_NAME)
            container.reload()
            if container.status != 'running':
                logging.info(f'Container "{CONTAINER_NAME}" is not running. Retrying in 10 minutes...')
                time.sleep(600)
                continue

            logging.info(f'Starting log monitoring for container "{CONTAINER_NAME}"')
            # Stream logs in real-time
            log_stream = container.logs(stream=True, follow=True, since=int(time.time()))

            # Compile regex patterns
            player_join_pattern = re.compile(r'\[.*\] \[LOG\] (?P<player_name>.+?) joined the server\. \(User id: .*\)')
            player_leave_pattern = re.compile(r'\[.*\] \[LOG\] (?P<player_name>.+?) left the server\. \(User id: .*\)')

            for log in log_stream:
                line = log.decode('utf-8').strip()
                if line == '':
                    continue
                # Process the log line
                if player_join_pattern.match(line):
                    match = player_join_pattern.match(line)
                    player = match.group('player_name')
                    with online_players_lock:
                        online_players.add(player)
                    logging.info(f'Player joined: {player}')
                elif player_leave_pattern.match(line):
                    match = player_leave_pattern.match(line)
                    player = match.group('player_name')
                    with online_players_lock:
                        online_players.discard(player)
                    logging.info(f'Player left: {player}')
        except docker.errors.NotFound:
            logging.warning(f'Container "{CONTAINER_NAME}" not found. Retrying in 5 seconds...')
            time.sleep(5)
        except Exception as e:
            logging.error(f'Error in monitor_container_logs: {e}', exc_info=True)
            time.sleep(5)

def start_log_monitoring_thread():
    global log_monitoring_thread
    if log_monitoring_thread is None or not log_monitoring_thread.is_alive():
        log_monitoring_thread = threading.Thread(target=monitor_container_logs, daemon=True)
        log_monitoring_thread.start()
        logging.info('Started log monitoring thread')

def stop_log_monitoring_thread():
    global log_monitoring_thread
    # Daemon threads exit when main program exits; we don't need to do anything special here
    log_monitoring_thread = None
    logging.info('Stopped log monitoring thread')

def is_allowed(ctx):
    return ctx.channel.name in ALLOWED_CHANNELS

# Command to start the game server
@bot.command(
    help="Starts the game server.\n\nUse this command to start the Palworld game server. The server will begin monitoring player activity once started.",
    brief="Starts the game server."
)
async def startserver(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status != 'running':
            container.start()
            await ctx.send('Game server is starting!')
            # Start the log monitoring thread
            start_log_monitoring_thread()
        else:
            await ctx.send('Game server is already running.')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f'Error starting the server: {e}', exc_info=True)
        await ctx.send(f'Error starting the server: {e}')

# Command to stop the game server
@bot.command(
    help="Stops the game server.\n\nUse this command to stop the Palworld game server. This will also stop the player activity monitoring.",
    brief="Stops the game server."
)
async def stopserver(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status == 'running':
            container.stop()
            await ctx.send('Game server is stopping!')
            # Stop the log monitoring thread
            stop_log_monitoring_thread()
        else:
            await ctx.send('Game server is not running.')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f'Error stopping the server: {e}', exc_info=True)
        await ctx.send(f'Error stopping the server: {e}')

# Command to check server status
@bot.command(
    help="Displays the current status of the game server.\n\nShows whether the Palworld game server is running or stopped.",
    brief="Displays the game server status."
)
async def serverstatus(ctx):
    if not is_allowed(ctx):
        return
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.reload()  # Refresh container state
        status = container.status  # 'running', 'exited', etc.
        await ctx.send(f'Game server status: {status}')
    except docker.errors.NotFound:
        await ctx.send(f'Container "{CONTAINER_NAME}" not found.')
    except Exception as e:
        logging.error(f'Error retrieving server status: {e}', exc_info=True)
        await ctx.send(f'Error retrieving server status: {e}')

# Background task to monitor inactivity
@tasks.loop(seconds=CHECK_INTERVAL)
async def monitor_inactivity():
    global inactivity_time
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.reload()
        if container.status == 'running':
            with online_players_lock:
                players_online_count = len(online_players)
            logging.info(f"Players online: {players_online_count}")
            if players_online_count > 0:
                inactivity_time = 0
            else:
                inactivity_time += CHECK_INTERVAL
                if inactivity_time >= INACTIVITY_LIMIT:
                    container.stop()
                    logging.warning('No players online for 10 minutes. Stopping the server.')
                    inactivity_time = 0
                    # Optionally send a message to a Discord channel
                    channel = discord.utils.get(bot.get_all_channels(), name=ALLOWED_CHANNELS[0])
                    if channel:
                        await channel.send('No players online for 10 minutes. Stopping the server.')
                    # Stop the log monitoring thread
                    stop_log_monitoring_thread()
        else:
            inactivity_time = 0
    except docker.errors.NotFound:
        inactivity_time = 0  # Reset timer if container doesn't exist
    except Exception as e:
        logging.error(f'Error in monitor_inactivity: {e}', exc_info=True)

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    # Start the inactivity monitor
    monitor_inactivity.start()
    # Start the log monitoring thread
    start_log_monitoring_thread()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Unknown command: {ctx.message.content}. Use `!help` to see available commands.")
    else:
        logging.error(f'Unhandled exception: {error}', exc_info=True)
        await ctx.send(f"An error occurred: {error}")

bot.run(TOKEN)
